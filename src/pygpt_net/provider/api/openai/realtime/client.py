#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.31 23:00:00                  #
# ================================================== #

import asyncio
import base64
import io
import json
import websockets

from typing import Optional, Callable, Awaitable
from urllib.parse import urlencode

from pygpt_net.core.events import RealtimeEvent
from pygpt_net.core.types import MODE_AUDIO
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.text.utils import has_unclosed_code_tag

# shared
from pygpt_net.core.realtime.shared.loop import BackgroundLoop
from pygpt_net.core.realtime.shared.audio import (
    coerce_to_pcm16_mono,
    resample_pcm16_mono,
    iter_pcm_chunks,
    DEFAULT_24K,
)
from pygpt_net.core.realtime.shared.tools import (
    sanitize_function_tools,
    sanitize_remote_tools,
    prepare_tools_for_session,
    prepare_tools_for_response,
    tools_signature,
    build_tool_outputs_payload,
)
from pygpt_net.core.realtime.shared.turn import TurnMode, apply_turn_mode_openai
from pygpt_net.core.realtime.shared.session import set_ctx_rt_handle, set_rt_session_expires_at


class OpenAIRealtimeClient:
    """
    OpenAI Realtime API client with persistent session and a dedicated background event loop.

    Key points:
    - A single background asyncio loop runs in its own thread for the lifetime of the client.
    - One websocket connection (session) at a time; multiple "turns" (send_turn) are serialized.
    - No server VAD: manual turn control via input_audio_buffer.* + response.create.
    - Safe to call run()/send_turn()/reset()/shutdown() from any thread or event loop.

    Session resumption:
    - The official Realtime API does not expose a documented server-side "resume" for closed WS sessions.
      We still persist the server-provided session.id and surface it via ctx.extra["rt_session_id"].
    - If opts.rt_session_id is provided and differs from the current in-memory handle, we reset the
      connection and attempt to reconnect with a "session_id" query parameter. If that fails, we fall
      back to the standard URL to avoid breaking existing functionality.
    """

    WS_URL = "wss://api.openai.com/v1/realtime"

    def __init__(self, window=None, debug: bool = False):
        """
        OpenAI Realtime API client

        :param window: Window instance
        :param debug: Enable debug logging
        """
        self.window = window
        self.debug = debug

        # WebSocket and session state (lives on the owner loop)
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._rx_task: Optional[asyncio.Task] = None
        self._running: bool = False

        # Background loop
        self._bg = BackgroundLoop(name="OpenAI-RT-Loop")

        # Flow control primitives (created on the owner loop)
        self._send_lock: Optional[asyncio.Lock] = None
        self._response_done: Optional[asyncio.Event] = None
        self._response_active: bool = False

        # Callbacks and context
        self._on_text: Optional[Callable[[str], Awaitable[None]]] = None
        self._on_audio: Optional[Callable[[bytes, str, Optional[int], Optional[int], bool], Awaitable[None]]] = None
        self._should_stop: Optional[Callable[[], bool]] = None
        self._ctx: Optional[CtxItem] = None
        self._last_opts = None  # kept to allow reset() without resupplying

        self._DEFAULT_RATE = DEFAULT_24K

        # Per-response extraction state (tools/images/citations/usage/assembled text)
        self._rt_state = None  # dict populated on response.created

        # Input transcription buffers keyed by item_id
        self._input_tr_buffers: dict[str, io.StringIO] = {}

        # Cached session.tools signature to avoid redundant session.update
        self._cached_session_tools_sig: Optional[str] = None

        # Last tool calls snapshot for mapping tool responses
        self._last_tool_calls: list[dict] = []

        # Live session handle (for best-effort resumption semantics)
        self._rt_session_id: Optional[str] = None
        self._rt_session_expires_at: Optional[int] = None  # epoch seconds if provided by server

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
        Run one turn: open session if needed, send prompt/audio, await response completion.

        :param ctx: CtxItem with model and conversation
        :param opts: Options object with prompt/audio/voice/etc.
        :param on_text: Async callback for text deltas
        :param on_audio: Async callback for audio chunks
        :param should_stop: Sync callback to signal barge-in (cancel active response)
        """
        self._ensure_background_loop()
        self._ctx = ctx

        # If a different resumable handle is provided, reset to attempt best-effort resume.
        try:
            provided = getattr(opts, "rt_session_id", None)
            if isinstance(provided, str):
                provided = provided.strip()
            if self.ws is not None and provided and provided != (self._rt_session_id or ""):
                await self._run_on_owner(self._reset_session_internal(ctx, opts, on_text, on_audio, should_stop))
        except Exception:
            pass

        # Open session on the owner loop (once)
        if not self.ws:
            await self._run_on_owner(self._open_session_internal(ctx, opts, on_text, on_audio, should_stop))

        # Send one turn on the owner loop
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
        Explicitly open a session (websocket); normally run() does this on demand.
        """
        self._ensure_background_loop()

        # If the session is already open but a different handle is requested, reset to attempt reattach.
        try:
            provided = getattr(opts, "rt_session_id", None)
            if isinstance(provided, str):
                provided = provided.strip()
            if self.ws is not None and provided and provided != (self._rt_session_id or ""):
                await self._run_on_owner(self._reset_session_internal(ctx, opts, on_text, on_audio, should_stop))
                return
        except Exception:
            pass

        await self._run_on_owner(self._open_session_internal(ctx, opts, on_text, on_audio, should_stop))

    async def close_session(self):
        """Close the websocket session but keep the background loop alive."""
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
        Close the current session and open a fresh one (new conversation on the server).
        If parameters are omitted, last-known ones are used.
        """
        self._ensure_background_loop()
        await self._run_on_owner(self._reset_session_internal(ctx, opts, on_text, on_audio, should_stop))

    async def shutdown(self):
        """
        Gracefully close the current session (if any).
        Does NOT stop the background loop; use stop_loop_sync() or shutdown_and_stop() to also stop the loop.
        """
        if not self._bg.loop:
            return
        await self._run_on_owner(self._close_session_internal())

    async def shutdown_and_stop(self):
        """Close session and stop the background loop thread."""
        await self.shutdown()
        self.stop_loop_sync()

    # -----------------------------
    # Synchronous convenience calls
    # -----------------------------

    def close_session_sync(self, timeout: float = 5.0):
        """Synchronous wrapper around close_session()."""
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
        """Synchronous wrapper around reset_session()."""
        self._ensure_background_loop()
        self._bg.run_sync(self._reset_session_internal(ctx, opts, on_text, on_audio, should_stop), timeout=timeout)

    def shutdown_sync(self, timeout: float = 5.0):
        """Synchronous wrapper around shutdown() — closes the WS but leaves the loop alive."""
        if not self._bg.loop or not self._bg.loop.is_running():
            return
        self._bg.run_sync(self._close_session_internal(), timeout=timeout)

    def stop_loop_sync(self, timeout: float = 2.0):
        """Stop the background event loop thread."""
        self._bg.stop(timeout=timeout)

    # -----------------------------
    # Tools helpers
    # -----------------------------

    def _update_last_opts_tools(self, tools: Optional[list], remote_tools: Optional[list]) -> None:
        """
        Update self._last_opts with tools/remote_tools if fields are present.
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

    # -----------------------------
    # Internal: background loop/dispatch
    # -----------------------------

    def _ensure_background_loop(self):
        """Start the background asyncio loop once and keep it running."""
        self._bg.ensure()

    async def _run_on_owner(self, coro):
        """Await a coroutine scheduled on the owner loop from any thread/loop."""
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
        Open WS and configure the Realtime session on the owner loop.
        """
        if self.ws is not None:
            if self.debug:
                print("[open_session] already open")
            return

        core = self.window.core
        model_data = core.models.get(ctx.model)
        args = self.window.core.models.prepare_client_args(MODE_AUDIO, model_data if ctx else None)
        api_key = args.get("api_key")
        if not api_key:
            raise RuntimeError("OpenAI API key not configured")

        model_id = getattr(opts, "model", None) or (ctx.model if ctx and ctx.model else "gpt-4o-realtime-preview")
        voice = getattr(opts, "voice", None) or self._preferred_voice()

        # Optional: requested resume handle from opts
        resume_sid = None
        try:
            provided = getattr(opts, "rt_session_id", None)
            if isinstance(provided, str):
                provided = provided.strip()
            if provided and provided != (self._rt_session_id or ""):
                resume_sid = provided
                self._rt_session_id = resume_sid
                set_ctx_rt_handle(self._ctx, resume_sid, self.window)
        except Exception:
            pass

        # Build WS URL with model and optional session_id for best-effort resume
        base_q = {"model": model_id}
        if resume_sid:
            base_q["session_id"] = resume_sid  # if unsupported by server, connect fallback will ignore
        url_with_sid = f"{self.WS_URL}?{urlencode(base_q)}"
        url_no_sid = f"{self.WS_URL}?{urlencode({'model': model_id})}"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        # Transcription toggle
        transcribe_enabled = bool(getattr(opts, "transcribe", False))

        # Save callbacks and context
        self._on_text = on_text
        self._on_audio = on_audio
        self._should_stop = should_stop or (lambda: False)
        self._ctx = ctx
        self._last_opts = opts

        # Control primitives
        self._response_done = asyncio.Event()
        self._send_lock = asyncio.Lock()

        if self.debug:
            print(f"[open_session] owner_loop={id(asyncio.get_running_loop())}")

        # Connect WS: first try with session_id if provided; on failure, fall back to plain URL.
        try:
            target_url = url_with_sid if resume_sid else url_no_sid
            self.ws = await websockets.connect(
                target_url,
                additional_headers=headers,
                max_size=16 * 1024 * 1024,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
            )
        except Exception as e:
            if resume_sid and self.debug:
                print(f"[open_session] connect with session_id failed ({e!r}); falling back to plain URL")
            if resume_sid:
                self.ws = await websockets.connect(
                    url_no_sid,
                    additional_headers=headers,
                    max_size=16 * 1024 * 1024,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                )
        if self.debug:
            print("[open_session] WS connected")

        # Session payload (manual by default; prepared for auto)
        session_payload = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "voice": voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                # turn_detection set below via apply_turn_mode_openai
                **({"instructions": str(getattr(opts, "system_prompt"))} if getattr(opts, "system_prompt", None) else {}),
            },
        }
        turn_mode = TurnMode.AUTO if bool(getattr(opts, "auto_turn", False)) else TurnMode.MANUAL
        apply_turn_mode_openai(session_payload, turn_mode)

        # Attach tools to session (remote + functions)
        try:
            session_tools = prepare_tools_for_session(opts)
            if session_tools:
                session_payload["session"]["tools"] = session_tools
                self._cached_session_tools_sig = tools_signature(session_tools)
                if self.debug:
                    print(f"[open_session] session.tools attached: {len(session_tools)}")
            else:
                self._cached_session_tools_sig = tools_signature([])
        except Exception as _e:
            if self.debug:
                print(f"[open_session] tools sanitize error: {_e}")
            self._cached_session_tools_sig = tools_signature([])

        # Attach native input transcription if requested
        try:
            if transcribe_enabled:
                iat = {"model": "whisper-1"}
                lang = getattr(opts, "transcribe_language", None) or getattr(opts, "language", None)
                if lang:
                    iat["language"] = str(lang)
                session_payload["session"]["input_audio_transcription"] = iat
        except Exception:
            pass

        if self.debug:
            print(f"[open_session] session_payload: {json.dumps(session_payload)}")

        await self.ws.send(json.dumps(session_payload))
        if self.debug:
            print("[open_session] session.update sent")

        # Start a single receiver task
        if self._rx_task is None or self._rx_task.done():
            self._running = True
            self._rx_task = asyncio.create_task(self._recv_loop(), name="realtime-recv")
            if self.debug:
                print("[open_session] _recv_loop started")

    async def _close_session_internal(self):
        """Close WS and stop the receiver; keep the background loop alive for reuse."""
        self._running = False
        # Cancel active response if any
        if self.ws and self._response_active:
            try:
                await self.ws.send(json.dumps({"type": "response.cancel"}))
            except Exception:
                pass

        # Close the socket
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

        # Await receiver
        if self._rx_task:
            try:
                await self._rx_task
            except Exception:
                pass
            self._rx_task = None

        # Reset control primitives
        self._response_active = False
        self._response_done = None
        self._send_lock = None
        self._cached_session_tools_sig = None

        # Clear in-memory handle; do not wipe persisted ctx.extra["rt_session_id"]
        self._rt_session_id = None
        self._rt_session_expires_at = None

        if self.debug:
            print("[close_session] closed")

    async def _reset_session_internal(
        self,
        ctx: Optional[CtxItem] = None,
        opts=None,
        on_text: Optional[Callable[[str], Awaitable[None]]] = None,
        on_audio: Optional[Callable[[bytes, str, Optional[int], Optional[int], bool], Awaitable[None]]] = None,
        should_stop: Optional[Callable[[], bool]] = None,
    ):
        """
        Close current session and open a new one with provided or last-known parameters.
        """
        # Determine params to reuse if not provided
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
        Send one manual turn (optional text + optional audio) and trigger response.create.
        """
        if not self.ws:
            # If session dropped remotely, try to reopen from last state
            if self._ctx and self._last_opts:
                await self._open_session_internal(self._ctx, self._last_opts, self._on_text, self._on_audio, self._should_stop)
            else:
                raise RuntimeError("Session not open. Call open_session(...) first.")

        # Serialize all sends to a single WS writer
        if self._send_lock is None:
            self._send_lock = asyncio.Lock()

        async with self._send_lock:
            # Ensure previous response is finished
            if self._response_active and self._response_done:
                if self.debug:
                    print("[send_turn] waiting for previous response")
                await self._response_done.wait()

            # Optional text
            if prompt and str(prompt).strip() and prompt != "...":
                if self.debug:
                    print(f"[send_turn] prompt len={len(prompt)}")
                await self.ws.send(json.dumps({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": str(prompt)}],
                    },
                }))

            # Optional audio
            if audio_data:
                sr, _ch, pcm = coerce_to_pcm16_mono(audio_data, audio_format, audio_rate, fallback_rate=self._DEFAULT_RATE)

                if sr != self._DEFAULT_RATE:
                    try:
                        pcm = resample_pcm16_mono(pcm, sr, self._DEFAULT_RATE)
                        if self.debug:
                            print(f"[audio] resampled {sr} -> {self._DEFAULT_RATE}")
                        sr = self._DEFAULT_RATE
                    except Exception as e:
                        if self.debug:
                            print(f"[audio] resample failed {sr}->{self._DEFAULT_RATE}: {e}")

                await self.ws.send(json.dumps({"type": "input_audio_buffer.clear"}))
                for chunk in iter_pcm_chunks(pcm, sr, ms=50):
                    if not chunk:
                        continue
                    await self.ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(chunk).decode("utf-8"),
                    }))
                await self.ws.send(json.dumps({"type": "input_audio_buffer.commit"}))

            # Trigger exactly one assistant response
            if self._response_done is None:
                self._response_done = asyncio.Event()
            else:
                try:
                    self._response_done.clear()
                except Exception:
                    self._response_done = asyncio.Event()

            # Build optional response payload (tools/tool_choice)
            resp_obj = {"modalities": ["text", "audio"]}
            try:
                resp_tools, tool_choice = prepare_tools_for_response(self._last_opts)
                if resp_tools:
                    resp_obj["tools"] = resp_tools
                    if tool_choice is None:
                        tool_choice = "auto"
                if tool_choice:
                    resp_obj["tool_choice"] = tool_choice
            except Exception as _e:
                if self.debug:
                    print(f"[send_turn] response tools compose error: {_e}")

            payload = {"type": "response.create"}
            if len(resp_obj) > 0:
                payload["response"] = resp_obj

            await self.ws.send(json.dumps(payload))
            if self.debug:
                print("[send_turn] response.create sent")

        # Optionally wait for response.done (otherwise return immediately)
        if wait_for_done and self._response_done:
            if self.debug:
                print("[send_turn] waiting for response.done")
            await self._response_done.wait()
            if self.debug:
                print("[send_turn] response.done received")

    async def _cancel_active_response_internal(self):
        """Cancel current response (barge-in)."""
        if self.ws and self._response_active:
            try:
                await self.ws.send(json.dumps({"type": "response.cancel"}))
            except Exception:
                pass

    # -----------------------------
    # Internal: audio input (auto-turn mode)
    # -----------------------------

    def rt_handle_audio_input_sync(self, event: RealtimeEvent, timeout: float = 0.5):
        """
        Synchronous entrypoint for continuous microphone input when auto-turn is enabled.
        This is safe to call from any thread; it schedules on the owner's background loop.
        """
        # Fast return if nothing to send
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
        Owner-loop implementation: push live audio to input buffer in auto-turn mode.
        """
        # Session must be open and auto-turn must be enabled
        if not self.ws or not self._running:
            if self.debug:
                print("[_rt_handle_audio_input] Socket not open!")
            return
        try:
            if not bool(getattr(self._last_opts, "auto_turn", False)):
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
        rate = int(payload.get("rate") or 0) or self._DEFAULT_RATE
        channels = int(payload.get("channels") or 1)
        is_final = bool(payload.get("final", False))

        # Convert to PCM16 mono @ 24kHz as required by our session config
        fmt_hint = "pcm16" if mime.startswith("audio/pcm") else None
        try:
            sr, _ch, pcm = coerce_to_pcm16_mono(data, fmt_hint, rate, fallback_rate=self._DEFAULT_RATE)
            if sr != self._DEFAULT_RATE:
                try:
                    pcm = resample_pcm16_mono(pcm, sr, self._DEFAULT_RATE)
                    sr = self._DEFAULT_RATE
                except Exception:
                    # On resample failure, still try to send raw chunk as-is (defensive)
                    sr = self._DEFAULT_RATE
        except Exception:
            return

        # Serialize writes to the websocket
        if self._send_lock is None:
            self._send_lock = asyncio.Lock()

        async with self._send_lock:
            # Append in ~50 ms chunks to keep frames small
            for chunk in iter_pcm_chunks(pcm, sr, ms=50):
                if not chunk:
                    continue
                try:
                    await self.ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(chunk).decode("utf-8"),
                    }))
                except Exception:
                    return

            # If plugin reported stream end, flush the buffer once.
            if is_final:
                try:
                    if self.debug:
                        print("[_rt_handle_audio_input] final chunk; committing")
                    await self.ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                except Exception:
                    pass

    def commit_audio_input_sync(self, timeout: float = 0.5):
        """
        Synchronous entrypoint to commit the input audio buffer in auto-turn mode.
        This is safe to call from any thread; it schedules on the owner's background loop.
        """
        self._ensure_background_loop()
        try:
            self._bg.run_sync(self._commit_audio_input_internal(), timeout=timeout)
        except Exception:
            # Never raise to caller from audio callback
            pass

    async def _commit_audio_input_internal(self):
        """
        Owner-loop implementation: commit input audio buffer in auto-turn mode.
        """
        if not self.ws or not self._running:
            return
        try:
            if not bool(getattr(self._last_opts, "auto_turn", False)):
                return
        except Exception:
            return
        if self._send_lock is None:
            self._send_lock = asyncio.Lock()
        async with self._send_lock:
            try:
                await self.ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
            except Exception:
                pass

    def force_response_now_sync(self, timeout: float = 5.0):
        """Synchronously force the model to create a response from current input buffer."""
        self._ensure_background_loop()
        try:
            self._bg.run_sync(self._force_response_now_internal(), timeout=timeout)
        except Exception:
            pass

    async def _force_response_now_internal(self):
        """Owner-loop: commit current input buffer and trigger response.create."""
        if not self.ws or not self._running:
            return
        try:
            if not bool(getattr(self._last_opts, "auto_turn", False)):
                # This helper is intended for auto-turn; manual flow already does commit+response.create.
                return
        except Exception:
            return

        if self._send_lock is None:
            self._send_lock = asyncio.Lock()

        async with self._send_lock:
            # 1) Finalize current input buffer
            try:
                await self.ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
            except Exception:
                return

            # 2) Prepare wait handle for this response
            if self._response_done is None:
                self._response_done = asyncio.Event()
            else:
                try:
                    self._response_done.clear()
                except Exception:
                    self._response_done = asyncio.Event()

            # 3) Build response payload (modalities + tools/tool_choice like in _send_turn_internal)
            resp_obj = {"modalities": ["text", "audio"]}
            try:
                resp_tools, tool_choice = prepare_tools_for_response(self._last_opts)
                if resp_tools:
                    resp_obj["tools"] = resp_tools
                    if tool_choice is None:
                        tool_choice = "auto"
                if tool_choice:
                    resp_obj["tool_choice"] = tool_choice
            except Exception:
                pass

            # 4) Trigger the assistant response now
            try:
                await self.ws.send(json.dumps({"type": "response.create", "response": resp_obj}))
            except Exception:
                return

    # -----------------------------
    # Public: live tools update
    # -----------------------------

    async def update_session_tools(
        self,
        tools: Optional[list] = None,
        remote_tools: Optional[list] = None,
        force: bool = False
    ):
        """
        Update session tools live via session.update.
        If WS is not open, this updates self._last_opts and returns.
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
        timeout: float = 5.0
    ):
        """Synchronous wrapper over update_session_tools()."""
        self._ensure_background_loop()
        self._bg.run_sync(self._update_session_tools_internal(tools, remote_tools, force), timeout=timeout)

    async def _update_session_tools_internal(
        self,
        tools: Optional[list],
        remote_tools: Optional[list],
        force: bool
    ):
        """
        Owner-loop implementation for session tools update.
        """
        # If socket is not open, just cache into last opts
        if not self.ws:
            self._update_last_opts_tools(tools, remote_tools)
            self._cached_session_tools_sig = None
            if self.debug:
                print("[update_session_tools] WS not open; cached for next session")
            return

        # Sanitize/compose session tools
        try:
            fn = sanitize_function_tools(tools if tools is not None else getattr(self._last_opts, "tools", None))
            rt = sanitize_remote_tools(remote_tools if remote_tools is not None else getattr(self._last_opts, "remote_tools", None))
            session_tools = (rt or []) + (fn or [])
        except Exception as e:
            if self.debug:
                print(f"[update_session_tools] sanitize error: {e}")
            session_tools = []

        new_sig = tools_signature(session_tools)

        # Compare with cached signature
        if not force and self._cached_session_tools_sig == new_sig:
            if self.debug:
                print("[update_session_tools] no changes; skipping session.update")
            self._update_last_opts_tools(tools, remote_tools)
            return

        # Send session.update under the single writer lock
        if self._send_lock is None:
            self._send_lock = asyncio.Lock()
        async with self._send_lock:
            try:
                payload = {
                    "type": "session.update",
                    "session": {"tools": session_tools}
                }
                await self.ws.send(json.dumps(payload))
                self._cached_session_tools_sig = new_sig
                self._update_last_opts_tools(tools, remote_tools)
                if self.debug:
                    print(f"[update_session_tools] session.update sent; tools={len(session_tools)}")
            except Exception as e:
                if self.debug:
                    print(f"[update_session_tools] send error: {e}")

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
        Send tool results back to the Realtime session.
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
        """Synchronous wrapper for send_tool_results()."""
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
        Owner-loop implementation. Serializes sends under the WS writer lock.
        """
        if not self.ws:
            raise RuntimeError("Live session is not open")

        outputs = build_tool_outputs_payload(results, self._last_tool_calls)
        if not outputs:
            return

        if self._send_lock is None:
            self._send_lock = asyncio.Lock()

        async with self._send_lock:
            # Emit one conversation.item.create per tool output
            for it in outputs:
                payload = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": it["call_id"],
                        "output": it["output"],  # must be a string (JSON-encoded when dict/list)
                    },
                }
                if it.get("previous_item_id"):
                    payload["previous_item_id"] = it["previous_item_id"]
                await self.ws.send(json.dumps(payload))

            # Optionally ask the model to continue
            if continue_turn:
                if self._response_done is None:
                    self._response_done = asyncio.Event()
                else:
                    try:
                        self._response_done.clear()
                    except Exception:
                        self._response_done = asyncio.Event()

                await self.ws.send(json.dumps({"type": "response.create"}))

        # Wait for the follow-up response to complete
        if continue_turn and wait_for_done and self._response_done:
            try:
                await self._response_done.wait()
            except Exception:
                pass

    # -----------------------------
    # Internal: receive loop
    # -----------------------------

    async def _recv_loop(self):
        """
        Single receiver loop for the entire session.
        Processes incoming events and dispatches to callbacks.
        """
        if self.debug:
            print("[_recv_loop] started")

        DEFAULT_RATE = self._DEFAULT_RATE
        audio_done = True

        try:
            while self._running and self.ws:
                # Do not hard-stop the session on should_stop; only cancel active response if requested.
                if self._should_stop and self._should_stop():
                    await self._cancel_active_response_internal()

                try:
                    raw = await asyncio.wait_for(self.ws.recv(), timeout=60)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    if self.debug:
                        print(f"[_recv_loop] recv error: {e!r}")
                    break

                if isinstance(raw, bytes):
                    # Realtime sends JSON text frames; ignore unexpected binary
                    continue

                try:
                    ev = json.loads(raw)
                except Exception:
                    continue

                etype = ev.get("type")

                # ---- session lifecycle (capture server handle) ----
                if etype in ("session.created", "session.updated"):
                    sess = ev.get("session") or {}
                    sid = sess.get("id")
                    if isinstance(sid, str) and sid.strip():
                        self._rt_session_id = sid.strip()
                        set_ctx_rt_handle(self._ctx, self._rt_session_id, self.window)
                        if self.debug:
                            print(f"[_recv_loop] session id: {self._rt_session_id}")
                    # Optional: expires_at if present (not always provided)
                    exp = sess.get("expires_at") or sess.get("expiresAt")
                    try:
                        if isinstance(exp, (int, float)) and exp > 0:
                            self._rt_session_expires_at = int(exp)
                            set_rt_session_expires_at(self._ctx, self._rt_session_expires_at, self.window)
                    except Exception:
                        pass
                    continue

                if etype == "response.created":
                    if self.debug:
                        print("[_recv_loop] response created")
                    self._response_active = True
                    audio_done = False
                    self._rt_reset_state()

                elif etype == "input_audio_buffer.speech_started":
                    if self.debug:
                        print("[_recv_loop] speech_started")

                elif etype == "input_audio_buffer.speech_stopped":
                    if self.debug:
                        print("[_recv_loop] speech_stopped")

                elif etype == "input_audio_buffer.committed":
                    if self.debug:
                        print("[_recv_loop] audio_buffer.committed")

                    # disable mic input if auto-commit
                    if self._last_opts:
                        self._last_opts.rt_signals.response.emit(RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_COMMIT, {
                            "ctx": self._ctx,
                        }))

                # ---- input transcription (user speech) ----
                elif etype == "conversation.item.input_audio_transcription.delta":
                    if self._transcribe_enabled():
                        buf = self._input_tr_buffers.get(ev.get("item_id"))
                        if buf is None:
                            buf = io.StringIO()
                            self._input_tr_buffers[ev.get("item_id")] = buf
                        delta = ev.get("delta") or ev.get("text") or ev.get("transcript") or ""
                        if delta:
                            buf.write(str(delta))

                elif etype in ("conversation.item.input_audio_transcription.completed",
                               "conversation.item.input_audio_transcription.done"):
                    if self._transcribe_enabled():
                        item_id = ev.get("item_id")
                        tr = ev.get("transcript") or ""
                        buf = self._input_tr_buffers.pop(item_id, None)
                        if buf is not None:
                            try:
                                v = buf.getvalue()
                                if v and not tr:
                                    tr = v
                            finally:
                                try:
                                    buf.close()
                                except Exception:
                                    pass
                        if tr:
                            self._save_input_transcript(tr)

                elif etype == "conversation.item.input_audio_transcription.failed":
                    if self.debug:
                        err = (ev.get("error") or {}).get("message") or "input transcription failed"
                        print(f"[_recv_loop] {err}")

                elif etype == "conversation.item.created":
                    if self.debug:
                        print("[_recv_loop] conversation.item.created")
                    # Fallback: some servers may include transcript inside the created user item
                    if self._transcribe_enabled():
                        item = ev.get("item") or {}
                        if item.get("role") == "user":
                            for c in (item.get("content") or []):
                                if isinstance(c, dict) and c.get("type") in ("input_audio", "audio"):
                                    tr = c.get("transcript")
                                    if tr:
                                        self._save_input_transcript(str(tr))

                # ---- assistant text vs assistant audio transcript deltas ----
                elif etype in ("response.text.delta", "response.output_text.delta"):
                    delta = ev.get("delta") or ev.get("text")
                    if isinstance(delta, dict) and "text" in delta:
                        delta = delta["text"]
                    if delta:
                        self._rt_append_text(delta)
                        if self._on_text:
                            try:
                                await self._on_text(str(delta))
                            except Exception:
                                pass
                elif etype == "response.audio_transcript.delta":
                    if self._transcribe_enabled():
                        delta = ev.get("delta") or ev.get("text")
                        if isinstance(delta, dict) and "text" in delta:
                            delta = delta["text"]
                        if delta:
                            self._rt_append_text(delta)
                            if self._on_text:
                                try:
                                    await self._on_text(str(delta))
                                except Exception:
                                    pass

                elif etype in ("response.text.done", "response.output_text.done", "response.audio_transcript.done"):
                    if self.debug:
                        print("[_recv_loop] text done")

                elif etype == "response.content_part.added":
                    part = ev.get("part") or {}
                    ptype = part.get("type")
                    if ptype == "text":
                        txt = part.get("text") or ""
                        if txt:
                            self._rt_append_text(txt)
                            if self._on_text:
                                try:
                                    await self._on_text(str(txt))
                                except Exception:
                                    pass
                    elif ptype == "audio":
                        b64 = part.get("audio")
                        if b64 and self._on_audio:
                            try:
                                data = base64.b64decode(b64)
                                await self._on_audio(data, "audio/pcm", DEFAULT_RATE, 1, False)
                            except Exception:
                                pass
                        tr = part.get("transcript")
                        if tr and self._transcribe_enabled():
                            self._rt_append_text(tr)
                            if self._on_text:
                                try:
                                    await self._on_text(str(tr))
                                except Exception:
                                    pass

                elif etype == "response.audio.delta":
                    b64 = ev.get("delta")
                    if b64 and self._on_audio:
                        try:
                            data = base64.b64decode(b64)
                            await self._on_audio(data, "audio/pcm", DEFAULT_RATE, 1, False)
                        except Exception:
                            pass

                elif etype == "response.audio.done":
                    if self.debug:
                        print("[_recv_loop] audio done")
                    if not audio_done and self._on_audio:
                        try:
                            await self._on_audio(b"", "audio/pcm", DEFAULT_RATE, 1, True)
                        except Exception:
                            pass
                        audio_done = True

                # ---- function calling (tools) ----
                elif etype == "response.output_item.added":
                    if self.debug:
                        print("[_recv_loop] output_item added")
                    item = ev.get("item") or {}
                    if item.get("type") == "function_call":
                        fid = item.get("id") or item.get("item_id") or ""
                        call_id = item.get("call_id") or ""
                        name = item.get("name") or ""
                        self._rt_state["tool_calls"].append({
                            "id": fid,
                            "call_id": call_id,
                            "type": "function",
                            "function": {"name": name, "arguments": ""}
                        })
                        if fid and fid not in self._rt_state["fn_args_buffers"]:
                            self._rt_state["fn_args_buffers"][fid] = io.StringIO()

                elif etype == "response.function_call_arguments.delta":
                    buf = self._rt_state["fn_args_buffers"].get(ev.get("item_id"))
                    if buf is not None:
                        delta = ev.get("delta") or ""
                        if delta:
                            buf.write(delta)

                elif etype == "response.function_call_arguments.done":
                    item_id = ev.get("item_id")
                    args_val = ev.get("arguments") or ""
                    buf = self._rt_state["fn_args_buffers"].pop(item_id, None)
                    if buf is not None:
                        try:
                            concat = buf.getvalue()
                            if concat:
                                args_val = concat
                        finally:
                            try:
                                buf.close()
                            except Exception:
                                pass
                    for tc in self._rt_state["tool_calls"]:
                        if tc.get("id") == item_id:
                            tc["function"]["arguments"] = args_val
                            break
                    self._rt_state["force_func_call"] = True

                elif etype == "response.output_item.done":
                    if self.debug:
                        print("[_recv_loop] output_item done")
                    item = ev.get("item") or {}
                    if item.get("type") == "function_call":
                        fid = item.get("id") or item.get("item_id") or ""
                        name = item.get("name") or ""
                        args_val = item.get("arguments") or ""
                        for tc in self._rt_state["tool_calls"]:
                            if fid and tc.get("id") == fid:
                                if name:
                                    tc["function"]["name"] = name
                                if args_val:
                                    tc["function"]["arguments"] = args_val
                                break
                        self._rt_state["force_func_call"] = True

                # ---- code interpreter (delta/done) ----
                elif etype in ("response.code_interpreter_call_code.delta", "response.code_interpreter_call.code.delta"):
                    code_delta = ev.get("delta") or ""
                    if code_delta:
                        if not self._rt_state["is_code"]:
                            hdr = "\n\n**Code interpreter**\n```python\n"
                            self._rt_append_text(hdr + code_delta)
                            if self._on_text:
                                try:
                                    await self._on_text(hdr + code_delta)
                                except Exception:
                                    pass
                            self._rt_state["is_code"] = True
                        else:
                            self._rt_append_text(code_delta)
                            if self._on_text:
                                try:
                                    await self._on_text(code_delta)
                                except Exception:
                                    pass

                elif etype in ("response.code_interpreter_call_code.done", "response.code_interpreter_call.code.done"):
                    if self.debug:
                        print("[_recv_loop] code done")
                    if self._rt_state["is_code"]:
                        tail = "\n\n```\n-----------\n"
                        self._rt_append_text(tail)
                        if self._on_text:
                            try:
                                await self._on_text(tail)
                            except Exception:
                                pass
                        self._rt_state["is_code"] = False

                # ---- annotations (citations/files) ----
                elif etype == "response.output_text.annotation.added":
                    if self.debug:
                        print("[_recv_loop] annotation added")
                    ann = ev.get("annotation") or {}
                    atype = ann.get("type")
                    if atype == "url_citation":
                        url = ann.get("url")
                        self._rt_add_citation(url)
                    elif atype == "container_file_citation":
                        self._rt_state["files"].append({
                            "container_id": ann.get("container_id"),
                            "file_id": ann.get("file_id"),
                        })

                # ---- partial images (defensive) ----
                elif etype == "response.image_generation_call.partial_image":
                    image_b64 = ev.get("partial_image_b64")
                    if image_b64:
                        try:
                            img_bytes = base64.b64decode(image_b64)
                            save_path = self.window.core.image.gen_unique_path(self._ctx)
                            with open(save_path, "wb") as f:
                                f.write(img_bytes)
                            self._rt_state["image_paths"].append(save_path)
                            self._rt_state["is_image"] = True
                            if not isinstance(self._ctx.images, list):
                                self._ctx.images = []
                            if save_path not in self._ctx.images:
                                self._ctx.images.append(save_path)
                        except Exception:
                            pass

                elif etype == "response.done":
                    if self.debug:
                        print("[_recv_loop] response done")
                    # Ensure audio finalized
                    if not audio_done and self._on_audio:
                        try:
                            await self._on_audio(b"", "audio/pcm", DEFAULT_RATE, 1, True)
                        except Exception:
                            pass
                        audio_done = True

                    self._response_active = False

                    # Capture usage if present on response
                    try:
                        resp_obj = ev.get("response") or {}
                        self._rt_capture_usage(resp_obj)
                    except Exception:
                        pass

                    # Build final output text
                    output = "".join(self._rt_state["output_parts"]) if self._rt_state else ""
                    if has_unclosed_code_tag(output):
                        output += "\n```"
                    if not output:
                        try:
                            transcript = self._extract_text_from_response_done(ev)
                            if transcript:
                                output = transcript
                        except Exception:
                            pass

                    # Persist into ctx
                    try:
                        if self._ctx:
                            self._ctx.output = output or (self._ctx.output or "")
                            up = self._rt_state.get("usage_payload") if self._rt_state else None
                            if up:
                                in_tok = up.get("in")
                                out_tok = up.get("out")
                                if in_tok is None:
                                    in_tok = self._ctx.input_tokens if self._ctx.input_tokens is not None else 0
                                if out_tok is None:
                                    out_tok = 0
                                self._ctx.set_tokens(in_tok, out_tok)
                                try:
                                    if not isinstance(self._ctx.extra, dict):
                                        self._ctx.extra = {}
                                    self._ctx.extra["usage"] = {
                                        "vendor": "openai",
                                        "input_tokens": in_tok,
                                        "output_tokens": out_tok,
                                        "reasoning_tokens": up.get("reasoning", 0),
                                        "total_reported": up.get("total"),
                                    }
                                except Exception:
                                    pass

                            # Citations
                            if self._rt_state and self._rt_state["citations"]:
                                if self._ctx.urls is None:
                                    self._ctx.urls = []
                                for u in self._rt_state["citations"]:
                                    if u not in self._ctx.urls:
                                        self._ctx.urls.append(u)

                            # Images
                            if self._rt_state and self._rt_state["image_paths"]:
                                if not isinstance(self._ctx.images, list):
                                    self._ctx.images = []
                                for p in self._rt_state["image_paths"]:
                                    if p not in self._ctx.images:
                                        self._ctx.images.append(p)

                            self.window.core.ctx.update_item(self._ctx)
                    except Exception:
                        pass

                    # Download container files if any
                    try:
                        files = (self._rt_state or {}).get("files") or []
                        if files:
                            self.window.core.api.openai.container.download_files(self._ctx, files)
                    except Exception:
                        pass

                    # Unpack tool calls if any
                    try:
                        tcs = (self._rt_state or {}).get("tool_calls") or []
                        if tcs:
                            for tc in tcs:
                                fn = tc.get("function") or {}
                                if isinstance(fn.get("arguments"), dict):
                                    fn["arguments"] = json.dumps(fn["arguments"], ensure_ascii=False)
                            self._ctx.force_call = bool((self._rt_state or {}).get("force_func_call"))
                            self.window.core.debug.info("[realtime] Tool calls found, unpacking...")
                            self.window.core.command.unpack_tool_calls_chunks(self._ctx, tcs)
                            self.window.core.ctx.update_item(self._ctx)
                    except Exception:
                        pass

                    # Persist last tool calls snapshot for mapping tool outputs
                    try:
                        tcs = (self._rt_state or {}).get("tool_calls") or []
                        if tcs:
                            self._last_tool_calls = list(tcs)
                    except Exception:
                        pass

                    # Unblock waiters
                    if self._response_done:
                        self._response_done.set()

                    # send RT_OUTPUT_TURN_END signal
                    if self._last_opts:
                        self._last_opts.rt_signals.response.emit(RealtimeEvent(RealtimeEvent.RT_OUTPUT_TURN_END, {
                            "ctx": self._ctx,
                        }))

                    # Reset per-response extraction state
                    self._rt_state = None

                elif etype == "error":
                    if self.debug:
                        print(f"[_recv_loop] error event: {ev}")
                    # Session expiration and other errors
                    err = ev.get("error") or {}
                    msg = (err.get("message") or "")
                    code = (err.get("code") or "")
                    if isinstance(code, str) and code.strip().lower() == "session_expired":
                        self._rt_session_id = None
                        if self.debug:
                            print("[_recv_loop] session expired")
                    if "already has an active response" in (msg or "").lower():
                        if self._response_done:
                            self._response_done.set()
                        continue
                    if self._response_done:
                        self._response_done.set()
                    if self.debug:
                        print(f"[_recv_loop] error: {msg}")

                # Other events are ignored

        except Exception as e:
            if self.debug:
                print(f"[_recv_loop] exception: {e!r}")
        finally:
            if self.debug:
                print("[_recv_loop] stopped")
            try:
                if self.ws:
                    await self.ws.close()
            except Exception:
                pass
            self.ws = None
            self._running = False

    # -----------------------------
    # Helpers
    # -----------------------------

    def _preferred_voice(self) -> str:
        """
        Resolve preferred OpenAI voice from settings.
        """
        try:
            v = self.window.core.plugins.get_option("audio_output", "openai_voice")
            if v:
                return str(v)
        except Exception:
            pass
        return "alloy"

    def _extract_text_from_response_done(self, ev: dict) -> str:
        """
        Extract assistant text from response.done payload.
        """
        res = ev.get("response") or {}
        out = res.get("output") or []
        parts: list[str] = []

        for item in out:
            if not isinstance(item, dict):
                continue
            if item.get("type") not in ("message", "tool_result", "function_call_result", "response"):
                pass
            content_list = item.get("content") or []
            for c in content_list:
                if not isinstance(c, dict):
                    continue
                ctype = c.get("type")
                if ctype == "audio" and self._transcribe_enabled():
                    tr = c.get("transcript")
                    if tr:
                        parts.append(str(tr))
                elif ctype in ("text", "output_text", "input_text"):
                    txt = c.get("text")
                    if isinstance(txt, dict):
                        txt = txt.get("text") or txt.get("value")
                    if txt:
                        parts.append(str(txt))

        text = "\n".join(t.strip() for t in parts if t and str(t).strip())
        return text

    # ---- per-response state helpers ----

    def _rt_reset_state(self):
        """Reset per-response extraction state."""
        self._rt_state = {
            "output_parts": [],
            "begin": True,
            "fn_args_buffers": {},
            "tool_calls": [],
            "citations": [],
            "files": [],
            "image_paths": [],
            "is_image": False,
            "is_code": False,
            "force_func_call": False,
            "usage_payload": {},
        }

    def _rt_append_text(self, s: str):
        """Append text to assembled output, skipping initial empty deltas."""
        if self._rt_state is None:
            self._rt_reset_state()
        if self._rt_state["begin"] and (s is None or s == ""):
            return
        self._rt_state["output_parts"].append(str(s))
        self._rt_state["begin"] = False

    def _rt_add_citation(self, url: Optional[str]):
        """Add a URL citation to state and ctx (de-duplicated)."""
        if not url or not isinstance(url, str):
            return
        url = url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            return
        if url not in self._rt_state["citations"]:
            self._rt_state["citations"].append(url)
        try:
            if self._ctx:
                if self._ctx.urls is None:
                    self._ctx.urls = []
                if url not in self._ctx.urls:
                    self._ctx.urls.append(url)
        except Exception:
            pass

    def _rt_capture_usage(self, response_obj: dict):
        """
        Capture token usage from response.done if present.
        """
        try:
            usage = (response_obj or {}).get("usage") or {}
            if not usage:
                return
            in_tok = usage.get("input_tokens") or usage.get("prompt_tokens")
            out_tok = usage.get("output_tokens") or usage.get("completion_tokens")
            total = usage.get("total_tokens")
            self._rt_state["usage_payload"] = {
                "in": int(in_tok) if in_tok is not None else None,
                "out": int(out_tok) if out_tok is not None else None,
                "total": int(total) if total is not None else None,
                "reasoning": 0,
            }
        except Exception:
            pass

    # ---- transcription helpers ----

    def _transcribe_enabled(self) -> bool:
        """Returns True if transcription (input/output) is enabled via opts.transcribe."""
        try:
            return bool(getattr(self._last_opts, "transcribe", False))
        except Exception:
            return False

    def _save_input_transcript(self, transcript: str):
        """
        Persist input transcript into ctx. If the user didn't provide a text prompt in this turn,
        ctx.input is also populated so downstream code treats it as the user's textual message.
        """
        if not transcript:
            return
        try:
            if self._ctx:
                if not isinstance(self._ctx.extra, dict):
                    self._ctx.extra = {}
                self._ctx.input.extra["input_transcript"] = str(transcript)
                if not getattr(self._last_opts, "prompt", None):
                    self._ctx.input = str(transcript)
                self.window.core.ctx.update_item(self._ctx)
        except Exception:
            pass

    def set_debug(self, enabled: bool):
        """
        Enable or disable debug logging.

        :param enabled: True to enable debug logging, False to disable.
        """
        self.debug = bool(enabled)

    def is_session_active(self) -> bool:
        """Check if the WS session is currently open."""
        return self.ws is not None and self._running

    def update_ctx(self, ctx: CtxItem):
        """Update the current CtxItem (for session handle persistence)."""
        self._ctx = ctx