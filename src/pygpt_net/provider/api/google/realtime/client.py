#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.07 23:00:00                  #
# ================================================== #

import asyncio
import base64
import json
from typing import Optional, Callable, Awaitable, Tuple, List, Any

from google.genai import types as gtypes  # for Schema/FunctionDeclaration/FunctionResponse compatibility

from pygpt_net.core.events import RealtimeEvent
from pygpt_net.core.types import MODE_AUDIO
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.text.utils import has_unclosed_code_tag

# shared
from pygpt_net.core.realtime.shared.loop import BackgroundLoop
from pygpt_net.core.realtime.shared.audio import to_pcm16_mono
from pygpt_net.core.realtime.shared.tools import build_function_responses_payload
from pygpt_net.core.realtime.shared.text import coalesce_text
from pygpt_net.core.realtime.shared.turn import TurnMode, apply_turn_mode_google
from pygpt_net.core.realtime.shared.session import set_ctx_rt_handle


class GoogleLiveClient:
    """
    Google Live client with server-side memory and smooth audio:

    - One persistent Live session; server keeps conversation context across turns.
    - User turns are sent via:
        * text: send_client_content(Content(...), turn_complete=True/False)
        * audio: ActivityStart -> send_realtime_input(audio=Blob...) -> ActivityEnd
          (manual turns; no auto VAD; no inline dicts — SDK serializes wire format)
    - Auto-turn mode (automatic VAD) is fully supported for continuous mic input:
        * push audio chunks via send_realtime_input(audio=...)
        * flush on demand via send_realtime_input(audio_stream_end=True)
        * receiver for one model turn is started automatically on first audio chunk.
    - Each turn has its own receive loop, ending on serverContent.turnComplete or toolCall.
    - Audio is jitter-buffered (~60ms) and de-duplicated (prefer response.data over inline_data).
    - Final transcript is coalesced; preserves hard line breaks only.
    - Tool calls, citations, images and usage are extracted and persisted to ctx to mirror OpenAI provider behavior.
    - Emits RealtimeEvent.RT_OUTPUT_AUDIO_COMMIT when the model starts responding after auto VAD or after an explicit flush,
      and RealtimeEvent.RT_OUTPUT_TURN_END after each turn.
    - Supports sending tool results back to the model (send_tool_results/send_tool_results_sync).
    """
    def __init__(
            self,
            window=None,
            debug: bool = False
    ):
        self.window = window
        self.debug = debug

        # Live session resources (owned by background loop)
        self._session = None
        self._session_cm = None

        # Background loop
        self._bg: BackgroundLoop = BackgroundLoop(name="Google-RT-Loop")

        # Flow control (per-session)
        self._send_lock: Optional[asyncio.Lock] = None
        self._response_done: Optional[asyncio.Event] = None
        self._response_active: bool = False
        self._turn_task: Optional[asyncio.Task] = None

        # Callbacks and context
        self._on_text: Optional[Callable[[str], Awaitable[None]]] = None
        self._on_audio: Optional[Callable[[bytes, str, Optional[int], Optional[int], bool], Awaitable[None]]] = None
        self._should_stop: Optional[Callable[[], bool]] = None
        self._ctx: Optional[CtxItem] = None
        self._last_opts = None

        # Per-turn text aggregation
        self._turn_text_parts: List[str] = []
        self._last_out_tr: str = ""  # last full output transcription (to compute deltas)

        # Audio I/O (rates)
        self._IN_RATE = 16000     # input (LINEAR16 mono)
        self._OUT_RATE = 24000    # output (model audio PCM16@24kHz)

        # Output audio jitter buffer
        self._audio_buf = bytearray()
        self._OUT_CHUNK_MS = 60
        self._OUT_BYTES_PER_MS = int(self._OUT_RATE * 2 / 1000)  # PCM16 mono (2 bytes/sample)
        self._saw_data_stream = False  # prefer response.data over inline_data to avoid duplicates

        # Per-turn extraction state
        self._rt_state: Optional[dict] = None

        # Last tool calls snapshot
        self._last_tool_calls: list[dict] = []

        # Live session resumption (current session handle)
        self._rt_session_id: Optional[str] = None  # string handle that can be used to resume a session

        # Cached tools signature to avoid redundant restarts
        self._cached_session_tools_sig: Optional[str] = None

        # Auto-turn state
        self._auto_audio_in_flight: bool = False  # True if auto-turn audio has been sent in current turn

    # -----------------------------
    # Public high-level entrypoints
    # -----------------------------

    async def run(
        self,
        ctx: CtxItem,
        opts,
        on_text: Callable[[str], Awaitable[None]],
        on_audio: Callable[[bytes, str, Optional[int], Optional[int], bool], Awaitable[None]],
        should_stop: Callable[[], bool] = lambda: False,
    ):
        """
        Run one turn: open session if needed, send prompt/audio, receive until turn complete.
        """
        self._ensure_background_loop()
        self._ctx = ctx

        # If a different resumable handle is provided, reset the session to resume there
        try:
            provided = getattr(opts, "rt_session_id", None)
            if isinstance(provided, str):
                provided = provided.strip()
            if self._session is not None and provided and provided != (self._rt_session_id or ""):
                await self._run_on_owner(self._reset_session_internal(ctx, opts, on_text, on_audio, should_stop))
        except Exception:
            pass

        if not self._session:
            await self._run_on_owner(self._open_session_internal(ctx, opts, on_text, on_audio, should_stop))

        await self._run_on_owner(self._send_turn_internal(
            getattr(opts, "prompt", None),
            getattr(opts, "audio_data", None),
            getattr(opts, "audio_format", None),
            getattr(opts, "audio_rate", None),
            wait_for_done=not bool(getattr(opts, "streaming", False)),
        ))

    async def open_session(
        self,
        ctx: CtxItem,
        opts,
        on_text: Callable[[str], Awaitable[None]],
        on_audio: Callable[[bytes, str, Optional[int], Optional[int], bool], Awaitable[None]],
        should_stop: Callable[[], bool] = lambda: False,
    ):
        """
        Open persistent Live session (if not already open).
        """
        self._ensure_background_loop()

        # If the session is already open but a different handle is requested, reset to resume.
        try:
            provided = getattr(opts, "rt_session_id", None)
            if isinstance(provided, str):
                provided = provided.strip()
            if self._session is not None and provided and provided != (self._rt_session_id or ""):
                await self._run_on_owner(self._reset_session_internal(ctx, opts, on_text, on_audio, should_stop))
                return
        except Exception:
            pass

        await self._run_on_owner(self._open_session_internal(ctx, opts, on_text, on_audio, should_stop))

    async def close_session(self):
        """Close persistent Live session (if open)."""
        if not self._bg.loop:
            return
        await self._run_on_owner(self._close_session_internal())

    async def reset_session(
        self,
        ctx: Optional[CtxItem] = None,
        opts=None,
        on_text: Optional[Callable[[str], Awaitable[None]]] = None,
        on_audio: Optional[Callable[[bytes, str, Optional[int], Optional[int], bool], Awaitable[None]]] = None,
        should_stop: Optional[Callable[[], bool]] = None,
    ):
        """
        Reset (close and reopen) persistent Live session with same or new params.
        """
        self._ensure_background_loop()
        await self._run_on_owner(self._reset_session_internal(ctx, opts, on_text, on_audio, should_stop))

    async def shutdown(self):
        """Shutdown background loop and close session."""
        if not self._bg.loop:
            return
        await self._run_on_owner(self._close_session_internal())

    async def shutdown_and_stop(self):
        """Shutdown background loop, close session and stop the loop thread."""
        await self.shutdown()
        self.stop_loop_sync()

    # -----------------------------
    # Synchronous convenience calls
    # -----------------------------

    def close_session_sync(self, timeout: float = 5.0):
        """Close persistent Live session (if open)."""
        if not self._bg.loop or not self._bg.loop.is_running():
            return
        self._bg.run_sync(self._close_session_internal(), timeout=timeout)

    def reset_session_sync(
        self,
        ctx: Optional[CtxItem] = None,
        opts=None,
        on_text: Optional[Callable[[str], Awaitable[None]]] = None,
        on_audio: Optional[Callable[[bytes, str, Optional[int], Optional[int], bool], Awaitable[None]]] = None,
        should_stop: Optional[Callable[[], bool]] = None,
        timeout: float = 10.0,
    ):
        """
        Reset (close and reopen) persistent Live session with same or new params.
        """
        self._ensure_background_loop()
        self._bg.run_sync(self._reset_session_internal(ctx, opts, on_text, on_audio, should_stop), timeout=timeout)

    def shutdown_sync(self, timeout: float = 5.0):
        """
        Shutdown background loop and close session (sync).
        """
        if not self._bg.loop or not self._bg.loop.is_running():
            return
        self._bg.run_sync(self._close_session_internal(), timeout=timeout)

    def stop_loop_sync(self, timeout: float = 2.0):
        """
        Stop background loop and join the thread.
        """
        self._bg.stop(timeout=timeout)

    # -----------------------------
    # Tools helpers
    # -----------------------------

    def _update_last_opts_tools(self, tools: Optional[list], remote_tools: Optional[list]) -> None:
        """
        Update self._last_opts with tools/remote_tools if those attributes exist.
        """
        lo = self._last_opts
        if not lo:
            return
        try:
            if tools is not None and hasattr(lo, "tools"):
                setattr(lo, "tools", tools)
        except Exception:
            pass
        try:
            if remote_tools is not None and hasattr(lo, "remote_tools"):
                setattr(lo, "remote_tools", remote_tools)
        except Exception:
            pass

    def _tools_signature(self, tools_list: list) -> str:
        """
        Build a stable signature string for the given tools list.
        """
        try:
            return json.dumps(tools_list or [], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        except Exception:
            return str(tools_list or [])

    # -----------------------------
    # Internal: background loop/dispatch
    # -----------------------------

    def _ensure_background_loop(self):
        """Ensure background event loop and thread are running."""
        self._bg.ensure()

    async def _run_on_owner(self, coro):
        """
        Run coroutine on the owner loop and await result.
        """
        return await self._bg.run(coro)

    # -----------------------------
    # Internal: session lifecycle
    # -----------------------------

    async def _open_session_internal(
        self,
        ctx: CtxItem,
        opts,
        on_text: Callable[[str], Awaitable[None]],
        on_audio: Callable[[bytes, str, Optional[int], Optional[int], bool], Awaitable[None]],
        should_stop: Callable[[], bool] = lambda: False,
    ):
        """
        Open persistent Live session (if not already open).
        """
        if self._session is not None:
            if self.debug:
                print("[google.open_session] already open")
            return

        core = self.window.core
        model_data = core.models.get(ctx.model) if ctx and getattr(ctx, "model", None) else None
        client = self.window.core.api.google.get_client(MODE_AUDIO, model_data if ctx else None)
        if not client:
            raise RuntimeError("Google GenAI client not configured")

        # Select Live-capable model
        model_id = getattr(opts, "model", None) or (ctx.model if ctx and getattr(ctx, "model", None) else "gemini-live-2.5-flash-preview")
        voice = getattr(opts, "voice", None) or self._preferred_voice()

        # Compose tools for session
        session_tools = self._sanitize_tools(getattr(opts, "tools", None), getattr(opts, "remote_tools", None))

        # Live config — manual activity boundaries (no auto VAD by default)
        live_cfg = {
            "response_modalities": ["AUDIO"],
            "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": voice}}},
            "output_audio_transcription": {},
            "realtime_input_config": {"automatic_activity_detection": {"disabled": True}},
        }
        if session_tools:
            live_cfg["tools"] = session_tools

        # Cache current tools signature
        self._cached_session_tools_sig = self._tools_signature(session_tools or [])

        sys_prompt = getattr(opts, "system_prompt", None)
        if sys_prompt:
            live_cfg["system_instruction"] = str(sys_prompt)

        # Save callbacks and ctx early so handle persistence can target the current context
        self._on_text = on_text
        self._on_audio = on_audio
        self._should_stop = should_stop or (lambda: False)
        self._ctx = ctx
        self._last_opts = opts

        # Session resumption: configure per docs; include handle when provided, otherwise None.
        try:
            ph = None
            provided_handle = getattr(opts, "rt_session_id", None)
            if isinstance(provided_handle, str):
                ph = provided_handle.strip() or None

            sr_cfg = gtypes.SessionResumptionConfig(handle=ph)
            live_cfg["session_resumption"] = sr_cfg

            if ph:
                self._persist_rt_handle(ph)
        except Exception:
            pass

        # Apply turn mode (auto/manual VAD)
        turn_mode = TurnMode.AUTO if bool(getattr(opts, "auto_turn", False)) else TurnMode.MANUAL
        apply_turn_mode_google(live_cfg, turn_mode)
        self._tune_google_vad(live_cfg, opts)

        # Control primitives
        self._response_done = asyncio.Event()
        self._send_lock = asyncio.Lock()
        self._turn_text_parts = []
        self._last_out_tr = ""
        self._last_tool_calls = []

        # Connect session
        self._session_cm = client.aio.live.connect(model=model_id, config=live_cfg)
        self._session = await self._session_cm.__aenter__()
        if self.debug:
            print("[google.open_session] live session connected")

    async def _close_session_internal(self):
        """Close persistent Live session (if open)."""
        if self._turn_task and not self._turn_task.done():
            try:
                await asyncio.wait_for(self._turn_task, timeout=2.0)
            except Exception:
                pass
        self._turn_task = None

        if self._session_cm:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except Exception:
                pass
        self._session_cm = None
        self._session = None

        self._response_active = False
        self._response_done = None
        self._send_lock = None
        self._turn_text_parts = []
        self._last_out_tr = ""
        self._audio_buf.clear()
        self._saw_data_stream = False
        self._rt_state = None
        self._last_tool_calls = []

        # Clear in-memory handle as well to prevent unintended resumption
        self._rt_session_id = None

        # Clear cached tools signature
        self._cached_session_tools_sig = None

        # Auto-turn flags
        self._auto_audio_in_flight = False

        if self.debug:
            print("[google.close_session] closed")

    async def _reset_session_internal(
        self,
        ctx: Optional[CtxItem] = None,
        opts=None,
        on_text: Optional[Callable[[str], Awaitable[None]]] = None,
        on_audio: Optional[Callable[[bytes, str, Optional[int], Optional[int], bool], Awaitable[None]]] = None,
        should_stop: Optional[Callable[[], bool]] = None,
    ):
        """
        Reset (close and reopen) persistent Live session with same or new params.
        """
        ctx = ctx or self._ctx
        opts = opts or self._last_opts
        on_text = on_text or self._on_text
        on_audio = on_audio or self._on_audio
        should_stop = should_stop or self._should_stop or (lambda: False)

        if not (ctx and opts and on_text and on_audio):
            raise RuntimeError("reset_session requires previous or explicit ctx/opts/callbacks")

        await self._close_session_internal()
        await self._open_session_internal(ctx, opts, on_text, on_audio, should_stop)

    # -----------------------------
    # Internal: one "turn"
    # -----------------------------

    async def _send_turn_internal(
        self,
        prompt: Optional[str] = None,
        audio_data: Optional[bytes] = None,
        audio_format: Optional[str] = None,
        audio_rate: Optional[int] = None,
        wait_for_done: bool = True,
    ):
        """
        Send one turn: prompt and/or audio, receive until turn complete or tool call.
        """
        if not self._session:
            if self._ctx and self._last_opts:
                await self._open_session_internal(self._ctx, self._last_opts, self._on_text, self._on_audio, self._should_stop)
            else:
                raise RuntimeError("Session not open. Call open_session(...) first.")

        if self._send_lock is None:
            self._send_lock = asyncio.Lock()

        async with self._send_lock:
            if self._response_active and self._response_done:
                if self.debug:
                    print("[google.send_turn] waiting for previous response")
                await self._response_done.wait()

            # Reset per-turn collectors
            self._turn_text_parts = []
            self._last_out_tr = ""
            self._audio_buf.clear()
            self._saw_data_stream = False
            self._rt_reset_state()
            self._last_tool_calls = []
            self._auto_audio_in_flight = False

            # Normalize prompt/audio first to choose a stable path
            txt = str(prompt).strip() if prompt is not None else ""
            if txt == "...":
                txt = ""
            parts_t = [gtypes.Part(text=txt)] if txt else []

            pcm = b""
            rate = self._IN_RATE
            if audio_data:
                pcm, rate = to_pcm16_mono(audio_data, audio_format, audio_rate, target_rate=self._IN_RATE)

            has_text = bool(parts_t)
            has_audio = bool(pcm)

            # Branches
            if has_text and not has_audio:
                # TEXT-ONLY -> single Content, turn_complete=True
                await self._session.send_client_content(
                    turns=gtypes.Content(role="user", parts=parts_t),
                    turn_complete=True,
                )
                self._response_active = True
                if self._response_done is None:
                    self._response_done = asyncio.Event()
                else:
                    try:
                        self._response_done.clear()
                    except Exception:
                        self._response_done = asyncio.Event()
                self._turn_task = asyncio.create_task(self._recv_one_turn(), name="google-live-turn")

            elif has_audio and not has_text:
                # AUDIO-ONLY
                # If auto-turn is enabled, use auto-VAD path and flush with audio_stream_end.
                # Otherwise, use manual ActivityStart/End boundaries.
                use_auto = False
                try:
                    use_auto = bool(getattr(self._last_opts, "auto_turn", False))
                except Exception:
                    use_auto = False

                self._response_active = True
                if self._response_done is None:
                    self._response_done = asyncio.Event()
                else:
                    try:
                        self._response_done.clear()
                    except Exception:
                        self._response_done = asyncio.Event()

                # Start receiving before sending any audio
                self._turn_task = asyncio.create_task(self._recv_one_turn(), name="google-live-turn")

                if use_auto:
                    self._auto_audio_in_flight = True
                    # Auto-VAD: send a single audio blob and flush explicitly
                    try:
                        await self._session.send_realtime_input(
                            audio=gtypes.Blob(data=pcm, mime_type=f"audio/pcm;rate={int(rate)}")
                        )
                        await self._session.send_realtime_input(audio_stream_end=True)
                        self._emit_audio_commit_signal()  # fire once for explicit flush
                    except Exception as e:
                        if self.debug:
                            print(f"[google.audio:auto] send failed: {e!r}")
                        raise
                else:
                    # Manual activity: start -> audio -> end
                    await self._send_audio_realtime_manual(pcm, rate)

            elif has_text and has_audio:
                # TEXT + AUDIO in one user turn:
                # Respect the configured mode: in manual mode keep ActivityStart/End,
                # in auto-turn mode send text first and then treat audio as auto-VAD stream with explicit flush.
                use_auto = False
                try:
                    use_auto = bool(getattr(self._last_opts, "auto_turn", False))
                except Exception:
                    use_auto = False

                # 1) text opens the turn (turn_complete=False)
                await self._session.send_client_content(
                    turns=gtypes.Content(role="user", parts=parts_t),
                    turn_complete=False,
                )

                self._response_active = True
                if self._response_done is None:
                    self._response_done = asyncio.Event()
                else:
                    try:
                        self._response_done.clear()
                    except Exception:
                        self._response_done = asyncio.Event()

                # Start receiver, then send audio
                self._turn_task = asyncio.create_task(self._recv_one_turn(), name="google-live-turn")

                if use_auto:
                    self._auto_audio_in_flight = True
                    try:
                        await self._session.send_realtime_input(
                            audio=gtypes.Blob(data=pcm, mime_type=f"audio/pcm;rate={int(rate)}")
                        )
                        await self._session.send_realtime_input(audio_stream_end=True)
                        self._emit_audio_commit_signal()  # fire once for explicit flush
                    except Exception as e:
                        if self.debug:
                            print(f"[google.audio:auto+text] send failed: {e!r}")
                        raise
                else:
                    await self._send_audio_realtime_manual(pcm, rate)

            else:
                # nothing to send
                return

        if wait_for_done and self._turn_task:
            try:
                await self._turn_task
            except Exception:
                pass

    async def _send_audio_realtime_manual(self, pcm: bytes, rate: int):
        """
        Manual turn boundaries: ActivityStart -> audio chunks -> ActivityEnd.
        MIME must be audio/pcm;rate=RATE (no space).
        """
        if not pcm:
            return
        mime = f"audio/pcm;rate={int(rate)}"

        # Activity start
        try:
            await self._session.send_realtime_input(activity_start=gtypes.ActivityStart())
            if self.debug:
                print("[google.audio] activityStart")
        except Exception as e:
            if self.debug:
                print(f"[google.audio] activityStart failed: {e!r}")
            raise

        # ~100 ms chunks (for 16kHz -> 3200 bytes)
        bytes_per_ms = int(rate * 2 / 1000)  # 2 bytes per sample, mono
        chunk = max(bytes_per_ms * 100, 3200)
        for i in range(0, len(pcm), chunk):
            part = pcm[i:i + chunk]
            try:
                await self._session.send_realtime_input(
                    audio=gtypes.Blob(data=part, mime_type=mime)
                )
            except Exception as e:
                if self.debug:
                    print(f"[google.audio] payload send failed: {e!r}")
                raise

        # Activity end
        try:
            await self._session.send_realtime_input(activity_end=gtypes.ActivityEnd())
            if self.debug:
                print("[google.audio] activityEnd")
        except Exception as e:
            if self.debug:
                print(f"[google.audio] activityEnd failed: {e!r}")
            raise

    # -----------------------------
    # Internal: realtime audio input (auto-turn mode)
    # -----------------------------

    def rt_handle_audio_input_sync(self, event: RealtimeEvent, timeout: float = 0.5):
        """
        Synchronous entrypoint for continuous microphone input when auto-turn is enabled.
        Safe to call from any thread; schedules work on the background loop.
        """
        # Quick no-op if empty
        try:
            payload = getattr(event, "data", {}) or {}
            if isinstance(payload, dict) and "payload" in payload and isinstance(payload["payload"], dict):
                payload = payload["payload"]
            if not payload or not payload.get("data"):
                return
        except Exception:
            return

        self._ensure_background_loop()
        try:
            self._bg.run_sync(self._rt_handle_audio_input_internal(event), timeout=timeout)
        except Exception:
            # Never raise to caller from audio callback
            pass

    async def _rt_handle_audio_input_internal(self, event: RealtimeEvent):
        """
        Owner-loop implementation: push live audio to Gemini Live in auto-turn mode.
        """
        if not self._session:
            return
        try:
            if not bool(getattr(self._last_opts, "auto_turn", False)):
                # Only handle here when auto-turn is on; manual mode uses ActivityStart/End path.
                return
        except Exception:
            return

        # Extract normalized payload
        payload = getattr(event, "data", {}) or {}
        if isinstance(payload, dict) and "payload" in payload and isinstance(payload["payload"], dict):
            payload = payload["payload"]

        data: bytes = payload.get("data") or b""
        if not data:
            return
        mime = str(payload.get("mime") or "audio/pcm")
        rate = int(payload.get("rate") or 0) or self._IN_RATE
        channels = int(payload.get("channels") or 1)
        is_final = bool(payload.get("final", False))

        # Normalize to LINEAR16 mono @16kHz (Live API input native rate)
        fmt_hint = "pcm16" if mime.startswith("audio/pcm") else None
        try:
            pcm, norm_rate = to_pcm16_mono(data, fmt_hint, rate, target_rate=self._IN_RATE)
        except Exception:
            return

        # Ensure a receiver for this auto-turn is running before sending audio
        self._ensure_auto_receiver_started()

        # Mark that auto-turn audio has been sent in this turn
        self._auto_audio_in_flight = True

        # Send audio blob; Gemini Live handles VAD automatically in auto mode
        if self._send_lock is None:
            self._send_lock = asyncio.Lock()

        async with self._send_lock:
            try:
                await self._session.send_realtime_input(
                    audio=gtypes.Blob(data=pcm, mime_type=f"audio/pcm;rate={int(norm_rate)}")
                )
            except Exception:
                return

            # If stream end is flagged, flush server-side VAD buffer
            if is_final:
                try:
                    await self._session.send_realtime_input(audio_stream_end=True)
                    self._emit_audio_commit_signal()  # fire once for explicit flush
                except Exception:
                    pass

    def commit_audio_input_sync(self, timeout: float = 0.5):
        """
        Synchronous entrypoint to flush the input audio stream in auto-turn mode.
        This sends audio_stream_end to force the model to process current buffered audio.
        Safe to call from any thread.
        """
        self._ensure_background_loop()
        try:
            self._bg.run_sync(self._commit_audio_input_internal(), timeout=timeout)
        except Exception:
            # Never raise to caller
            pass

    async def _commit_audio_input_internal(self):
        """
        Owner-loop implementation: in auto-turn mode flush server-side VAD buffer.
        """
        if not self._session:
            return
        try:
            if not bool(getattr(self._last_opts, "auto_turn", False)):
                return
        except Exception:
            return

        # Ensure a receiver is running for this turn
        self._ensure_auto_receiver_started()

        if self._send_lock is None:
            self._send_lock = asyncio.Lock()
        async with self._send_lock:
            try:
                await self._session.send_realtime_input(audio_stream_end=True)
                self._emit_audio_commit_signal()  # fire once for explicit flush
            except Exception:
                pass

    def force_response_now_sync(self, timeout: float = 5.0):
        """
        Synchronously force the model to create a response from current input buffer (auto-turn).
        Internally sends audio_stream_end and ensures a receiver is running for the pending turn.
        """
        self._ensure_background_loop()
        try:
            self._bg.run_sync(self._force_response_now_internal(), timeout=timeout)
        except Exception:
            # Defensive: do not propagate errors to caller
            pass

    async def _force_response_now_internal(self):
        """
        Owner-loop: in auto-turn mode, flush current audio buffer and guarantee that a receive task
        for the current model turn is running. No-op in manual mode.
        """
        if not self._session:
            return
        try:
            if not bool(getattr(self._last_opts, "auto_turn", False)):
                return
        except Exception:
            return

        # Ensure a receiver is running for this turn
        self._ensure_auto_receiver_started()

        # Flush server-side buffer to force the model to respond
        if self._send_lock is None:
            self._send_lock = asyncio.Lock()
        async with self._send_lock:
            try:
                await self._session.send_realtime_input(audio_stream_end=True)
                self._emit_audio_commit_signal()  # fire once for explicit flush
            except Exception:
                pass

    async def _recv_one_turn(self):
        """Receive one turn until serverContent.turnComplete or toolCall."""
        if self.debug:
            print("[google._recv_one_turn] start")

        turn_finished = False

        try:
            async for response in self._session.receive():
                # 0) Session resumption updates (store last resumable handle)
                try:
                    sru = getattr(response, "session_resumption_update", None) or getattr(response, "sessionResumptionUpdate", None)
                    if sru:
                        # Prefer robustness: persist handle if present, regardless of 'resumable' flag inconsistencies
                        new_handle = self._extract_sru_handle(sru)
                        if isinstance(new_handle, str) and new_handle.strip():
                            self._persist_rt_handle(new_handle.strip())
                            if self.debug:
                                print(f"[google.live] session handle updated: {self._rt_session_id}")
                except Exception:
                    pass

                # 1) Usage (top-level)
                try:
                    um = getattr(response, "usage_metadata", None) or getattr(response, "usageMetadata", None)
                    if um:
                        self._rt_capture_google_usage(um)
                except Exception:
                    pass

                # 2) Preferred audio source: response.data (PCM16@24kHz)
                data = getattr(response, "data", None)
                if isinstance(data, (bytes, bytearray)):
                    # First output from model -> emit commit once (auto-turn only)
                    self._maybe_emit_auto_commit()
                    self._saw_data_stream = True
                    await self._audio_push(bytes(data), final=False)

                # 3) Server content
                sc = getattr(response, "server_content", None) or getattr(response, "serverContent", None)
                if sc:
                    # Any serverContent reaching here implies the model started processing;
                    # emit commit once if not yet emitted (auto-turn only).
                    self._maybe_emit_auto_commit()

                    # Output transcription (often cumulative)
                    out_tr = getattr(sc, "output_transcription", None) or getattr(sc, "outputTranscription", None)
                    if out_tr and getattr(out_tr, "text", None) and self._on_text:
                        full = str(out_tr.text)
                        delta = full[len(self._last_out_tr):] if full.startswith(self._last_out_tr) else full
                        self._last_out_tr = full
                        if delta.strip():
                            self._turn_text_parts.append(delta)
                            try:
                                await self._on_text(delta)
                            except Exception:
                                pass

                    # Optional: input transcription (handy in manual mode)
                    in_tr = getattr(sc, "input_transcription", None) or getattr(sc, "inputTranscription", None)
                    if in_tr and getattr(in_tr, "text", None) and self.debug:
                        print("[google.input_tr]", in_tr.text)

                    # Model turn parts
                    model_turn = getattr(sc, "model_turn", None) or getattr(sc, "modelTurn", None)
                    if model_turn:
                        parts = getattr(model_turn, "parts", None) or []
                        for p in parts:
                            # Function call parts
                            fc = getattr(p, "function_call", None) or (p.get("function_call") if isinstance(p, dict) else None)
                            if fc:
                                name = getattr(fc, "name", None) or (fc.get("name") if isinstance(fc, dict) else "")
                                args_obj = getattr(fc, "args", None) or (fc.get("args") if isinstance(fc, dict) else {})
                                args_dict = self._to_plain_dict(args_obj) or {}
                                self._rt_state["tool_calls"].append({
                                    "id": getattr(fc, "id", None) or "",
                                    "type": "function",
                                    "function": {
                                        "name": name or "",
                                        "arguments": json.dumps(args_dict, ensure_ascii=False),
                                    }
                                })
                                # self._rt_state["force_func_call"] = True
                                self._last_tool_calls = list(self._rt_state["tool_calls"])
                                turn_finished = True  # let the app run tools now

                            # Text part
                            txt = getattr(p, "text", None) or (p.get("text") if isinstance(p, dict) else None)
                            if txt and self._on_text:
                                s = str(txt)
                                self._turn_text_parts.append(s)
                                try:
                                    await self._on_text(s)
                                except Exception:
                                    pass

                            # Code execution parts
                            ex = getattr(p, "executable_code", None) or (p.get("executable_code") if isinstance(p, dict) else None)
                            if ex:
                                lang = (getattr(ex, "language", None) or "python").strip() or "python"
                                code_txt = (
                                    getattr(ex, "code", None) or
                                    getattr(ex, "program", None) or
                                    getattr(ex, "source", None) or
                                    ""
                                )
                                if not self._rt_state["is_code"]:
                                    hdr = f"\n\n**Code interpreter**\n```{lang.lower()}\n"
                                    self._turn_text_parts.append(hdr + str(code_txt))
                                    try:
                                        if self._on_text:
                                            await self._on_text(hdr + str(code_txt))
                                    except Exception:
                                        pass
                                    self._rt_state["is_code"] = True
                                else:
                                    self._turn_text_parts.append(str(code_txt))
                                    try:
                                        if self._on_text:
                                            await self._on_text(str(code_txt))
                                    except Exception:
                                        pass

                            cer = getattr(p, "code_execution_result", None) or (p.get("code_execution_result") if isinstance(p, dict) else None)
                            if cer and self._rt_state["is_code"]:
                                tail = "\n\n```\n-----------\n"
                                self._turn_text_parts.append(tail)
                                try:
                                    if self._on_text:
                                        await self._on_text(tail)
                                except Exception:
                                    pass
                                self._rt_state["is_code"] = False

                            # Inline images
                            inline = getattr(p, "inline_data", None) or (p.get("inline_data") if isinstance(p, dict) else None)
                            if inline:
                                mime = (getattr(inline, "mime_type", "") or (inline.get("mime_type") if isinstance(inline, dict) else "") or "").lower()
                                if mime.startswith("image/"):
                                    pdata = getattr(inline, "data", None) if not isinstance(inline, dict) else inline.get("data")
                                    try:
                                        img_bytes = None
                                        if isinstance(pdata, (bytes, bytearray)):
                                            img_bytes = bytes(pdata)
                                        elif isinstance(pdata, str):
                                            img_bytes = base64.b64decode(pdata)
                                        if img_bytes:
                                            save_path = self.window.core.image.gen_unique_path(self._ctx)
                                            with open(save_path, "wb") as f:
                                                f.write(img_bytes)
                                            self._rt_state["image_paths"].append(save_path)
                                            if not isinstance(self._ctx.images, list):
                                                self._ctx.images = []
                                            if save_path not in self._ctx.images:
                                                self._ctx.images.append(save_path)
                                    except Exception:
                                        pass

                        # Citations (grounding)
                        try:
                            self._collect_google_citations_from_server_content(sc)
                        except Exception:
                            pass

                    # Turn complete signal
                    try:
                        if bool(getattr(sc, "turn_complete", None) or getattr(sc, "turnComplete", None)):
                            turn_finished = True
                    except Exception:
                        pass

                # 4) Dedicated toolCall message
                tc = getattr(response, "tool_call", None) or getattr(response, "toolCall", None)
                if tc:
                    self._maybe_emit_auto_commit()  # ensure commit signaled before handing off to tools
                    fcs = getattr(tc, "function_calls", None) or getattr(tc, "functionCalls", None) or []
                    new_calls = []
                    for fc in fcs:
                        name = getattr(fc, "name", "") or ""
                        args_obj = getattr(fc, "args", {}) or {}
                        args_dict = self._to_plain_dict(args_obj) or {}
                        new_calls.append({
                            "id": getattr(fc, "id", "") or "",
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(args_dict, ensure_ascii=False),
                            }
                        })
                    if new_calls:
                        seen = {(tc["function"]["name"], tc["function"]["arguments"]) for tc in self._rt_state["tool_calls"]}
                        for c in new_calls:
                            key = (c["function"]["name"], c["function"]["arguments"])
                            if key not in seen:
                                self._rt_state["tool_calls"].append(c)
                                seen.add(key)
                        # self._rt_state["force_func_call"] = True
                        self._last_tool_calls = list(self._rt_state["tool_calls"])
                    turn_finished = True

                if turn_finished:
                    break

            # Flush jitter buffer
            await self._audio_push(b"", final=True)

        except asyncio.CancelledError:
            try:
                await self._audio_push(b"", final=True)
            except Exception:
                pass
        except Exception as e:
            if self.debug:
                print(f"[google._recv_one_turn] exception: {e!r}")
            try:
                await self._audio_push(b"", final=True)
            except Exception:
                pass
        finally:
            # Persist textual output
            try:
                if self.window and self.window.core and self._ctx:
                    txt = coalesce_text(self._turn_text_parts)
                    if has_unclosed_code_tag(txt):
                        txt += "\n```"
                    if txt:
                        self._ctx.output = txt
                    # Tokens usage
                    up = (self._rt_state or {}).get("usage_payload") or {}
                    if up:
                        in_tok = up.get("in")
                        out_tok = up.get("out")
                        self._ctx.set_tokens(in_tok if in_tok is not None else (self._ctx.input_tokens or 0),
                                             out_tok if out_tok is not None else 0)
                        try:
                            if not isinstance(self._ctx.extra, dict):
                                self._ctx.extra = {}
                            self._ctx.extra["usage"] = {
                                "vendor": "google",
                                "input_tokens": in_tok,
                                "output_tokens": out_tok,
                                "reasoning_tokens": up.get("reasoning", 0),
                                "total_reported": up.get("total"),
                            }
                        except Exception:
                            pass

                    # Citations to ctx.urls
                    cites = (self._rt_state or {}).get("citations") or []
                    if cites:
                        if self._ctx.urls is None:
                            self._ctx.urls = []
                        for u in cites:
                            if u not in self._ctx.urls:
                                self._ctx.urls.append(u)

                    # Images to ctx.images
                    imgs = (self._rt_state or {}).get("image_paths") or []
                    if imgs:
                        if not isinstance(self._ctx.images, list):
                            self._ctx.images = []
                        for p in imgs:
                            if p not in self._ctx.images:
                                self._ctx.images.append(p)

                    # Unpack tool calls
                    tcs = (self._rt_state or {}).get("tool_calls") or []
                    if tcs:
                        for tc in tcs:
                            fn = tc.get("function") or {}
                            if isinstance(fn.get("arguments"), dict):
                                fn["arguments"] = json.dumps(fn["arguments"], ensure_ascii=False)
                        self._ctx.force_call = bool((self._rt_state or {}).get("force_func_call"))
                        self.window.core.debug.info("[google.live] Tool calls found, unpacking...")
                        self.window.core.command.unpack_tool_calls_chunks(self._ctx, tcs)

                    self.window.core.ctx.update_item(self._ctx)
            except Exception:
                pass

            # Mark done for waiters
            self._response_active = False
            if self._response_done:
                try:
                    self._response_done.set()
                except Exception:
                    pass

            # Emit end-of-turn event for audio pipeline symmetry with OpenAI
            try:
                if self._last_opts and hasattr(self._last_opts, "rt_signals"):
                    self._last_opts.rt_signals.response.emit(RealtimeEvent(RealtimeEvent.RT_OUTPUT_TURN_END, {
                        "ctx": self._ctx,
                    }))
            except Exception:
                pass

            # Reset per-turn state
            self._rt_state = None
            self._auto_audio_in_flight = False

            if self.debug:
                print("[google._recv_one_turn] done")

    # -----------------------------
    # Public: live tools update
    # -----------------------------

    async def update_session_tools(
        self,
        tools: Optional[list] = None,
        remote_tools: Optional[list] = None,
        force: bool = False,
    ):
        """
        Update session tools for Google Live.
        Since the Live API does not support mid-session tool config updates via SDK,
        this performs a safe session restart with best-effort resumption if the tools changed.
        If the session is not open, it only updates cached opts for the next open.
        """
        self._ensure_background_loop()
        return await self._run_on_owner(
            self._update_session_tools_internal(tools, remote_tools, force)
        )

    def update_session_tools_sync(
        self,
        tools: Optional[list] = None,
        remote_tools: Optional[list] = None,
        force: bool = False,
        timeout: float = 10.0,
    ):
        """Synchronous wrapper over update_session_tools()."""
        self._ensure_background_loop()
        return self._bg.run_sync(
            self._update_session_tools_internal(tools, remote_tools, force),
            timeout=timeout
        )

    async def _update_session_tools_internal(
        self,
        tools: Optional[list],
        remote_tools: Optional[list],
        force: bool,
    ):
        """
        Owner-loop implementation for tools update on Google Live.

        Strategy:
        - Sanitize and compute signature of the requested tools set.
        - If session is closed: update last opts and clear local cache.
        - If session is open and tools changed (or force=True):
            * Wait for any active response to finish.
            * Restart the Live session and request resumption using the last known handle.
        """
        # Prepare target tools (prefer explicit args, fallback to last opts)
        try:
            target_tools_raw = tools if tools is not None else getattr(self._last_opts, "tools", None)
        except Exception:
            target_tools_raw = None
        try:
            target_remote_raw = remote_tools if remote_tools is not None else getattr(self._last_opts, "remote_tools", None)
        except Exception:
            target_remote_raw = None

        session_tools = self._sanitize_tools(target_tools_raw, target_remote_raw)
        new_sig = self._tools_signature(session_tools or [])

        # If session is not open, just cache for next open
        if not self._session:
            self._update_last_opts_tools(tools, remote_tools)
            self._cached_session_tools_sig = None
            if self.debug:
                print("[google.update_session_tools] session not open; cached for next open")
            return

        # Skip if unchanged
        if not force and self._cached_session_tools_sig == new_sig:
            self._update_last_opts_tools(tools, remote_tools)
            if self.debug:
                print("[google.update_session_tools] no changes; skipping restart")
            return

        # Ensure previous response is finished
        if self._send_lock is None:
            self._send_lock = asyncio.Lock()
        async with self._send_lock:
            if self._response_active and self._response_done:
                if self.debug:
                    print("[google.update_session_tools] waiting for active response to finish")
                try:
                    await self._response_done.wait()
                except Exception:
                    pass

        # Persist new tools into last opts
        self._update_last_opts_tools(tools, remote_tools)

        # Try to resume the session state after restart if possible
        prev_handle = self._rt_session_id

        # Inject resumption handle into opts for the next open
        try:
            if self._last_opts is not None and prev_handle:
                setattr(self._last_opts, "rt_session_id", prev_handle)
        except Exception:
            pass

        if self.debug:
            print("[google.update_session_tools] restarting session to apply new tools")

        # Restart session with updated opts and best-effort resume
        await self._reset_session_internal(
            ctx=self._ctx,
            opts=self._last_opts,
            on_text=self._on_text,
            on_audio=self._on_audio,
            should_stop=self._should_stop,
        )

        # Cache new signature to suppress redundant restarts
        self._cached_session_tools_sig = new_sig

        if self.debug:
            print(f"[google.update_session_tools] session restarted; tools={len(session_tools)}")

    # -----------------------------
    # Public: send tool results back to the model
    # -----------------------------

    async def send_tool_results(
        self,
        results,
        continue_turn: bool = True,
        wait_for_done: bool = True,
    ):
        """
        Send tool results back to the Live session (FunctionResponse list).
        """
        self._ensure_background_loop()
        return await self._run_on_owner(
            self._send_tool_results_internal(results, continue_turn, wait_for_done)
        )

    def send_tool_results_sync(
        self,
        results,
        continue_turn: bool = True,
        wait_for_done: bool = True,
        timeout: float = 20.0,
    ):
        """
        Synchronous wrapper for send_tool_results().
        """
        self._ensure_background_loop()
        return self._bg.run_sync(
            self._send_tool_results_internal(results, continue_turn, wait_for_done),
            timeout=timeout
        )

    async def _send_tool_results_internal(
        self,
        results,
        continue_turn: bool,
        wait_for_done: bool,
    ):
        """
        Internal implementation of send_tool_results.
        """
        if not self._session:
            raise RuntimeError("Live session is not open")

        # Build neutral list and convert to gtypes.FunctionResponse[]
        try:
            neutral = build_function_responses_payload(results, self._last_tool_calls)
        except Exception as e:
            raise RuntimeError(f"Invalid tool results payload: {e}") from e

        if not neutral:
            return

        fn_responses = [
            gtypes.FunctionResponse(id=e.get("id") or "", name=e.get("name") or "", response=e.get("response") or {})
            for e in neutral
        ]

        if self._send_lock is None:
            self._send_lock = asyncio.Lock()
        async with self._send_lock:
            try:
                await self._session.send_tool_response(function_responses=fn_responses)
            except Exception as e:
                raise RuntimeError(f"send_tool_response failed: {e}") from e

        if continue_turn:
            self._turn_text_parts = []
            self._last_out_tr = ""
            self._audio_buf.clear()
            self._saw_data_stream = False
            self._rt_reset_state()

            self._response_active = True
            if self._response_done is None:
                self._response_done = asyncio.Event()
            else:
                try:
                    self._response_done.clear()
                except Exception:
                    self._response_done = asyncio.Event()

            self._turn_task = asyncio.create_task(self._recv_one_turn(), name="google-live-turn-followup")

            if wait_for_done:
                try:
                    await self._turn_task
                except Exception:
                    pass

    # -----------------------------
    # Helpers
    # -----------------------------

    def _preferred_voice(self) -> str:
        """
        Get preferred TTS voice from options or default.
        """
        try:
            v = self.window.core.plugins.get_option("audio_output", "google_genai_tts_voice")
            if v:
                mapping = {"kore": "Kore", "puck": "Puck", "charon": "Charon", "verse": "Verse", "legend": "Legend"}
                return mapping.get(str(v).strip().lower(), str(v))
        except Exception:
            pass
        return "Kore"

    async def _audio_push(self, data: bytes, final: bool = False):
        """
        Push audio data to the output callback in ~100 ms chunks.
        """
        if not self._on_audio:
            return
        if data:
            self._audio_buf.extend(data)
        threshold = self._OUT_BYTES_PER_MS * self._OUT_CHUNK_MS
        while len(self._audio_buf) >= threshold:
            chunk = self._audio_buf[:threshold]
            del self._audio_buf[:threshold]
            try:
                await self._on_audio(bytes(chunk), "audio/pcm", self._OUT_RATE, 1, False)
            except Exception:
                pass
        if final:
            if self._audio_buf:
                try:
                    await self._on_audio(bytes(self._audio_buf), "audio/pcm", self._OUT_RATE, 1, False)
                except Exception:
                    pass
                self._audio_buf.clear()
            try:
                await self._on_audio(b"", "audio/pcm", self._OUT_RATE, 1, True)
            except Exception:
                pass

    def _to_plain_dict(self, obj: Any) -> Any:
        """
        Convert various objects (pydantic, dataclass, etc) to plain dict recursively.
        """
        try:
            if hasattr(obj, "to_json_dict"):
                return obj.to_json_dict()
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
        except Exception:
            pass
        if isinstance(obj, dict):
            return {k: self._to_plain_dict(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._to_plain_dict(x) for x in obj]
        return obj

    def _rt_reset_state(self):
        """Reset per-turn realtime state."""
        self._rt_state = {
            "tool_calls": [],
            "citations": [],
            "files": [],
            "image_paths": [],
            "is_image": False,
            "is_code": False,
            "force_func_call": False,
            "usage_payload": {},
            "auto_commit_signaled": False,
        }

    def _rt_capture_google_usage(self, um_obj: Any):
        """
        Capture Google GenAI token usage from usage_metadata object.
        """
        if not um_obj or self._rt_state is None:
            return

        def as_int(v):
            try:
                if v is None:
                    return None
                return int(v)
            except Exception:
                try:
                    return int(float(v))
                except Exception:
                    return None

        prompt = (getattr(um_obj, "prompt_token_count", None)
                  or getattr(um_obj, "promptTokenCount", None)
                  or getattr(um_obj, "prompt_tokens", None)
                  or None)
        total = (getattr(um_obj, "total_token_count", None)
                 or getattr(um_obj, "totalTokenCount", None)
                 or getattr(um_obj, "total_tokens", None)
                 or None)
        candidates = (getattr(um_obj, "candidates_token_count", None)
                      or getattr(um_obj, "candidatesTokenCount", None)
                      or getattr(um_obj, "output_tokens", None)
                      or None)
        reasoning = (getattr(um_obj, "candidates_reasoning_token_count", None)
                     or getattr(um_obj, "candidatesReasoningTokenCount", None)
                     or getattr(um_obj, "reasoning_tokens", None)
                     or 0)
        p = as_int(prompt)
        t = as_int(total)
        c = as_int(candidates)
        r = as_int(reasoning) or 0
        out_total = max(0, (t or 0) - (p or 0)) if (t is not None and p is not None) else c
        self._rt_state["usage_payload"] = {"in": p, "out": out_total, "reasoning": r, "total": t}

    def _collect_google_citations_from_server_content(self, sc: Any):
        """
        Collect citations (URLs) from server_content grounding metadata and add to rt_state and ctx.urls.
        """
        if self._rt_state is None:
            return

        def add_url(url: Optional[str]):
            if not url or not isinstance(url, str):
                return
            u = url.strip()
            if not (u.startswith("http://") or u.startswith("https://")):
                return
            if u not in self._rt_state["citations"]:
                self._rt_state["citations"].append(u)
            try:
                if self._ctx:
                    if self._ctx.urls is None:
                        self._ctx.urls = []
                    if u not in self._ctx.urls:
                        self._ctx.urls.append(u)
            except Exception:
                pass

        gm = getattr(sc, "grounding_metadata", None) or getattr(sc, "groundingMetadata", None)
        if gm:
            atts = getattr(gm, "grounding_attributions", None) or getattr(gm, "groundingAttributions", None) or []
            try:
                for att in atts or []:
                    for path in (
                        "web.uri", "web.url", "source.web.uri", "source.web.url",
                        "source.uri", "source.url", "uri", "url",
                    ):
                        add_url(self._safe_get(att, path))
            except Exception:
                pass
            for path in (
                "search_entry_point.uri", "search_entry_point.url",
                "searchEntryPoint.uri", "searchEntryPoint.url",
                "search_entry_point.rendered_content_uri", "searchEntryPoint.rendered_content_uri",
            ):
                add_url(self._safe_get(gm, path))

        try:
            mt = getattr(sc, "model_turn", None) or getattr(sc, "modelTurn", None)
            parts = getattr(mt, "parts", None) or []
            for p in parts:
                pcm = self._safe_get(p, "citation_metadata") or self._safe_get(p, "citationMetadata")
                if pcm:
                    arr = (self._safe_get(pcm, "citation_sources")
                           or self._safe_get(pcm, "citationSources")
                           or self._safe_get(pcm, "citations") or []
                           )
                    for cit in arr or []:
                        for path in ("uri", "url", "source.uri", "source.url", "web.uri", "web.url"):
                            add_url(self._safe_get(cit, path))
                gpa = self._safe_get(p, "grounding_attributions") or self._safe_get(p, "groundingAttributions") or []
                for att in gpa or []:
                    for path in ("web.uri", "web.url", "source.web.uri", "source.web.url", "uri", "url"):
                        add_url(self._safe_get(att, path))
        except Exception:
            pass

    def _safe_get(self, obj, path: str) -> Any:
        """
        Safely get a nested attribute or dict key by dot-separated path.
        """
        cur = obj
        for seg in path.split("."):
            if cur is None:
                return None
            if isinstance(cur, dict):
                cur = cur.get(seg)
            else:
                if seg.isdigit() and isinstance(cur, (list, tuple)):
                    idx = int(seg)
                    if 0 <= idx < len(cur):
                        cur = cur[idx]
                    else:
                        return None
                else:
                    cur = getattr(cur, seg, None)
        return cur

    # -------- tools sanitizer for Live config (dict-only, robust) --------

    def _sanitize_tools(self, tools: Any, remote_tools: Optional[list] = None) -> list:
        """
        Normalize opts.tools into Live API config.tools (list of dicts).
        Supports gtypes.Tool, dict, or mixed list.
        """
        out: list = []
        sigset: set[str] = set()

        def add(entry: dict):
            try:
                sig = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            except Exception:
                sig = str(entry)
            if sig not in sigset:
                out.append(entry)
                sigset.add(sig)

        def handle_tool_obj(t):
            # Convert gtypes.Tool -> dict
            fd_list = []
            fds = getattr(t, "function_declarations", None) or getattr(t, "functionDeclarations", None) or []
            for fd in fds or []:
                fd_dict = self._fd_to_dict(fd)
                if fd_dict:
                    fd_list.append(fd_dict)
            if fd_list:
                add({"function_declarations": fd_list})

            # built-ins
            if getattr(t, "code_execution", None) or getattr(t, "codeExecution", None):
                add({"code_execution": {}})
            if getattr(t, "google_search", None) or getattr(t, "googleSearch", None):
                add({"google_search": {}})
            if getattr(t, "url_context", None) or getattr(t, "urlContext", None):
                add({"url_context": {}})

        def handle_tool_dict(d: dict):
            fds = d.get("function_declarations") or d.get("functionDeclarations")
            if isinstance(fds, list) and fds:
                fd_list = []
                for fd in fds:
                    fd_dict = self._fd_to_dict(fd)
                    if fd_dict:
                        fd_list.append(fd_dict)
                if fd_list:
                    add({"function_declarations": fd_list})

            if (d.get("type") or "").lower() == "function":
                fn = d.get("function") if isinstance(d.get("function"), dict) else d
                name = fn.get("name")
                if name:
                    fd = {"name": str(name)}
                    if fn.get("description"):
                        fd["description"] = fn["description"]
                    params = fn.get("parameters")
                    fd["parameters"] = self._schema_to_plain(params if params is not None else {"type": "OBJECT"})
                    add({"function_declarations": [fd]})

            for k in ("google_search", "code_execution", "url_context"):
                if k in d and isinstance(d[k], dict):
                    add({k: dict(d[k])})
                elif k in d and d[k] is True:
                    add({k: {}})

        if isinstance(tools, (list, tuple)):
            for t in tools:
                if t is None:
                    continue
                if t.__class__.__name__ == "Tool" or isinstance(t, getattr(gtypes, "Tool", ())):
                    handle_tool_obj(t)
                elif isinstance(t, dict):
                    handle_tool_dict(t)

        if isinstance(remote_tools, (list, tuple)):
            for t in remote_tools:
                if isinstance(t, dict):
                    handle_tool_dict(t)
                elif t.__class__.__name__ == "Tool" or isinstance(t, getattr(gtypes, "Tool", ())):
                    handle_tool_obj(t)

        return out

    def _fd_to_dict(self, fd: Any) -> Optional[dict]:
        """
        Convert FunctionDeclaration (gtypes or dict) to plain dict with normalized schema.
        """
        if fd.__class__.__name__ == "FunctionDeclaration" or isinstance(fd, getattr(gtypes, "FunctionDeclaration", ())):
            name = getattr(fd, "name", None)
            if not name:
                return None
            out = {"name": str(name)}
            desc = getattr(fd, "description", None)
            if desc:
                out["description"] = desc
            params = getattr(fd, "parameters", None)
            out["parameters"] = self._schema_to_plain(params if params is not None else {"type": "OBJECT"})
            return out

        if isinstance(fd, dict):
            name = fd.get("name")
            if not name:
                return None
            out = {"name": str(name)}
            if fd.get("description"):
                out["description"] = fd["description"]
            params = fd.get("parameters")
            out["parameters"] = self._schema_to_plain(params if params is not None else {"type": "OBJECT"})
            return out

        return None

    def _schema_to_plain(self, sc: Any) -> dict:
        """
        Convert gtypes.Schema or dict to a plain dict acceptable by Live API.
        """
        allowed = {"OBJECT", "ARRAY", "STRING", "NUMBER", "INTEGER", "BOOLEAN"}
        alias = {"INT": "INTEGER", "BOOL": "BOOLEAN", "FLOAT": "NUMBER", "DOUBLE": "NUMBER"}

        def norm_type(val) -> str:
            n = getattr(val, "name", None)
            if isinstance(n, str) and n:
                s = n
            else:
                s = str(val or "")
                if "." in s:
                    s = s.split(".")[-1]
            s = alias.get(s.upper(), s.upper())
            return s if s in allowed else "OBJECT"

        if sc is not None and (sc.__class__.__name__ == "Schema" or isinstance(sc, getattr(gtypes, "Schema", ()))):
            d: dict = {}
            t = getattr(sc, "type", None)
            d["type"] = norm_type(t) if t is not None else "OBJECT"

            desc = getattr(sc, "description", None)
            if desc:
                d["description"] = desc
            fmt = getattr(sc, "format", None)
            if fmt:
                d["format"] = fmt
            enum = getattr(sc, "enum", None)
            if isinstance(enum, list) and enum and d["type"] == "STRING":
                d["enum"] = enum
            req = getattr(sc, "required", None)
            if isinstance(req, list) and req:
                d["required"] = [x for x in req if isinstance(x, str)]

            props = getattr(sc, "properties", None)
            if isinstance(props, dict) and props:
                d["properties"] = {k: self._schema_to_plain(v) for k, v in props.items()}

            items = getattr(sc, "items", None)
            if items:
                d["items"] = self._schema_to_plain(items)

            return d

        if isinstance(sc, dict):
            d = dict(sc)
            d["type"] = norm_type(d.get("type"))
            if isinstance(d.get("properties"), dict):
                d["properties"] = {k: self._schema_to_plain(v) for k, v in d["properties"].items()}
            if isinstance(d.get("items"), dict):
                d["items"] = self._schema_to_plain(d["items"])
            if "enum" in d and d.get("type") != "STRING":
                d.pop("enum", None)
            return d

        return {"type": "OBJECT"}

    def _tune_google_vad(self, live_cfg: dict, opts) -> None:
        """
        Increase end-of-speech hold for automatic VAD in Gemini Live.
        """
        try:
            ric = live_cfg.setdefault("realtime_input_config", {})
            aad = ric.setdefault("automatic_activity_detection", {})
            if aad.get("disabled") is True:
                return  # manual mode, VAD disabled

            # Resolve target silence (default 2000 ms)
            target_ms = getattr(opts, "vad_end_silence_ms", None)
            if not isinstance(target_ms, (int, float)) or target_ms <= 0:
                base = int(aad.get("silence_duration_ms") or 100)
                target_ms = max(base, 2000)

            aad["silence_duration_ms"] = int(target_ms)

            # Optional: make end-of-speech less aggressive
            try:
                aad["end_of_speech_sensitivity"] = gtypes.EndSensitivity.END_SENSITIVITY_LOW
            except Exception:
                aad["end_of_speech_sensitivity"] = "END_SENSITIVITY_LOW"

            # Optional: leading padding before detected speech
            prefix_ms = getattr(opts, "vad_prefix_padding_ms", None)
            if isinstance(prefix_ms, (int, float)) and prefix_ms >= 0:
                aad["prefix_padding_ms"] = int(prefix_ms)
        except Exception:
            pass

    def set_debug(self, enabled: bool):
        """
        Enable or disable debug logging.

        :param enabled: True to enable debug logging, False to disable.
        """
        self.debug = bool(enabled)

    def is_session(self) -> bool:
        """Check if the WS session is currently open."""
        return self._session is not None

    def is_session_active(self) -> bool:
        """Check if the WS session is currently open."""
        return self._session is not None

    def update_ctx(self, ctx: CtxItem):
        """Update the current CtxItem (for session handle persistence)."""
        self._ctx = ctx

    def get_current_rt_session_id(self) -> Optional[str]:
        """
        Return the current resumable session handle if known.
        """
        return self._rt_session_id

    # -----------------------------
    # Internal: auto-turn receiver bootstrap
    # -----------------------------

    def _ensure_auto_receiver_started(self):
        """
        Start a receiver task for one model turn in auto-turn mode if not already active.
        This guarantees we do not miss server responses when sending live audio chunks.
        """
        # Only in auto-turn mode and with an open session
        if not self._session:
            return
        try:
            if not bool(getattr(self._last_opts, "auto_turn", False)):
                return
        except Exception:
            return

        # If a previous task exists but is done, clear the ref
        if self._turn_task and self._turn_task.done():
            self._turn_task = None

        if not self._response_active:
            # Reset per-turn collectors
            self._turn_text_parts = []
            self._last_out_tr = ""
            self._audio_buf.clear()
            self._saw_data_stream = False
            self._rt_reset_state()

            self._response_active = True
            if self._response_done is None:
                self._response_done = asyncio.Event()
            else:
                try:
                    self._response_done.clear()
                except Exception:
                    self._response_done = asyncio.Event()

            self._turn_task = asyncio.create_task(self._recv_one_turn(), name="google-live-auto-turn")

    def update_session_autoturn_sync(
            self,
            enabled: bool,
            silence_ms: Optional[int] = None,
            prefix_ms: Optional[int] = None,
            timeout: float = 10.0,
    ):
        """
        Synchronous helper: enable/disable auto-turn (VAD) for Google Live
        and optionally override silence/prefix (milliseconds).
        Note: Live API doesn't support mid-session VAD reconfigure; we restart
        the session safely if it is open.
        """
        self._ensure_background_loop()
        return self._bg.run_sync(
            self._update_session_autoturn_internal(enabled, silence_ms, prefix_ms),
            timeout=timeout
        )

    async def _update_session_autoturn_internal(
            self,
            enabled: bool,
            silence_ms: Optional[int] = None,
            prefix_ms: Optional[int] = None,
    ):
        """
        Owner-loop: toggle auto-turn (automatic_activity_detection) and optionally
        set silence_duration_ms / prefix_padding_ms. If the session is open,
        perform a safe restart to apply new config. If closed, cache in opts.
        """

        # Helper to update cached opts
        def _apply_to_opts():
            if not self._last_opts:
                return
            try:
                setattr(self._last_opts, "auto_turn", bool(enabled))
            except Exception:
                pass
            try:
                if silence_ms is not None:
                    setattr(self._last_opts, "vad_end_silence_ms", int(silence_ms))
            except Exception:
                pass
            try:
                if prefix_ms is not None:
                    setattr(self._last_opts, "vad_prefix_padding_ms", int(prefix_ms))
            except Exception:
                pass

        # If session not open -> just cache and exit
        if not self._session:
            _apply_to_opts()
            if self.debug:
                print("[google.update_session_autoturn] session not open; cached for next open")
            return

        # Compute whether anything changes to avoid unnecessary restart
        cur_enabled = False
        try:
            cur_enabled = bool(getattr(self._last_opts, "auto_turn", False))
        except Exception:
            pass
        cur_sil = getattr(self._last_opts, "vad_end_silence_ms", None)
        cur_pre = getattr(self._last_opts, "vad_prefix_padding_ms", None)

        change = (cur_enabled != bool(enabled))
        if silence_ms is not None and int(silence_ms) != (int(cur_sil) if isinstance(cur_sil, (int, float)) else None):
            change = True
        if prefix_ms is not None and int(prefix_ms) != (int(cur_pre) if isinstance(cur_pre, (int, float)) else None):
            change = True

        if not change:
            # Nothing to do; still persist values to opts for consistency
            _apply_to_opts()
            if self.debug:
                print("[google.update_session_autoturn] no changes; skipping restart")
            return

        # Wait for any active response to finish before restart
        if self._send_lock is None:
            self._send_lock = asyncio.Lock()
        async with self._send_lock:
            if self._response_active and self._response_done:
                if self.debug:
                    print("[google.update_session_autoturn] waiting for active response to finish")
                try:
                    await self._response_done.wait()
                except Exception:
                    pass

        # Update cached opts with requested values
        _apply_to_opts()

        # Try to resume after restart using the last known handle (best-effort)
        prev_handle = self._rt_session_id
        try:
            if self._last_opts is not None and prev_handle:
                setattr(self._last_opts, "rt_session_id", prev_handle)
        except Exception:
            pass

        if self.debug:
            eff_sil = silence_ms if silence_ms is not None else cur_sil
            eff_pre = prefix_ms if prefix_ms is not None else cur_pre
            print(f"[google.update_session_autoturn] restarting session; auto_turn={enabled}, "
                  f"silence_ms={eff_sil}, prefix_ms={eff_pre}")

        # Restart session with updated config
        await self._reset_session_internal(
            ctx=self._ctx,
            opts=self._last_opts,
            on_text=self._on_text,
            on_audio=self._on_audio,
            should_stop=self._should_stop,
        )

        if self.debug:
            print("[google.update_session_autoturn] session restarted with new VAD settings")

    # -----------------------------
    # Internal: commit event helpers
    # -----------------------------

    def _emit_audio_commit_signal(self):
        """
        Emit RT_OUTPUT_AUDIO_COMMIT once per turn in auto-turn mode.
        """
        if self._rt_state is None:
            self._rt_reset_state()
        if self._rt_state.get("auto_commit_signaled"):
            return
        try:
            if not bool(getattr(self._last_opts, "auto_turn", False)):
                return
        except Exception:
            return
        # Limit to audio turns: only when we actually sent auto-turn audio this turn
        if not self._auto_audio_in_flight:
            return
        try:
            if self._last_opts and hasattr(self._last_opts, "rt_signals"):
                self._last_opts.rt_signals.response.emit(
                    RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_COMMIT, {"ctx": self._ctx})
                )
            self._rt_state["auto_commit_signaled"] = True
        except Exception:
            pass

    def _maybe_emit_auto_commit(self):
        """
        Emit RT_OUTPUT_AUDIO_COMMIT on first sign of model output in auto-turn mode.
        """
        self._emit_audio_commit_signal()

    # -----------------------------
    # Internal: session handle helpers
    # -----------------------------

    def _persist_rt_handle(self, handle: str) -> None:
        """
        Persist current session handle in-memory, to ctx.extra and into last opts for future restarts.
        """
        try:
            self._rt_session_id = handle
            set_ctx_rt_handle(self._ctx, handle, self.window)
        except Exception:
            pass
        try:
            if self._last_opts is not None:
                setattr(self._last_opts, "rt_session_id", handle)
        except Exception:
            pass

    def _extract_sru_handle(self, sru: Any) -> Optional[str]:
        """
        Extract handle from SessionResumptionUpdate (supports snake_case and camelCase, and token alias).
        """
        # Objects (attrs)
        for attr in ("new_handle", "newHandle", "token"):
            try:
                v = getattr(sru, attr, None)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            except Exception:
                pass
        # Dicts
        if isinstance(sru, dict):
            for k in ("new_handle", "newHandle", "token"):
                v = sru.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
        return None