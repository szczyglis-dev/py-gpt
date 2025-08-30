#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.30 06:00:00                  #
# ================================================== #

import asyncio
import io
import re
import threading
import wave
import audioop
from typing import Optional, Callable, Awaitable, Tuple, List

from google.genai import types as gtypes  # only for Blob/Part/Content compatibility

from pygpt_net.core.types import MODE_AUDIO
from pygpt_net.item.ctx import CtxItem


class GoogleLiveClient:
    """
    Google Live client with server-side memory and smooth audio:

    - One persistent WebSocket session; server keeps conversation context across turns.
    - User turns are sent exclusively via send_client_content (text and/or audio inline_data).
    - Each turn has its own receive loop (session.receive()), ending exactly at turn completion.
    - Output audio is jitter-buffered (~60ms) and de-duplicated (prefer response.data over inline_data).
    - Final transcript is coalesced without artificial newlines, preserving only "hard" breaks emitted by the model.
    - Public API mirrors OpenAIRealtimeClient (run/open_session/reset/close/shutdown; on_text/on_audio callbacks).
    """
    def __init__(
            self,
            window=None,
            debug: bool = False
    ):
        """
        Google GenAI Live client

        :param window: Window instance
        :param debug: Enable debug mode
        """
        self.window = window
        self.debug = debug

        # Live session resources (owned by background loop)
        self._session = None
        self._session_cm = None

        # Background event loop in a dedicated thread
        self._owner_loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None

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

        # Per-turn text aggregation (for ctx persistence and final transcript)
        self._turn_text_parts: List[str] = []
        self._last_out_tr: str = ""  # last full output transcription (to compute deltas)

        # Audio I/O (rates)
        self._IN_RATE = 16000    # input (inline_data)
        self._OUT_RATE = 24000   # output (model audio)

        # Output audio jitter buffer (smooth playback)
        self._audio_buf = bytearray()
        self._OUT_CHUNK_MS = 60  # emit ~60ms chunks; tune 40..100 to trade latency/smoothness
        self._OUT_BYTES_PER_MS = int(self._OUT_RATE * 2 / 1000)  # PCM16 mono (2 bytes per sample)
        self._saw_data_stream = False  # prefer response.data over inline_data to avoid duplicates

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
        Open the session if needed and send exactly one user turn.
        Server-side memory persists across turns while the session is open.

        :param ctx: CtxItem
        :param opts: RealtimeOptions with prompt/audio_data/audio_format/audio_rate attributes
        :param on_text: async callback for text deltas
        :param on_audio: async callback for audio chunks
        :param should_stop: sync callable to signal early termination
        """
        self._ensure_background_loop()
        self._ctx = ctx

        if not self._session:
            await self._run_on_owner(self._open_session_internal(ctx, opts, on_text, on_audio, should_stop))

        await self._run_on_owner(self._send_turn_internal(
            getattr(opts, "prompt", None),
            getattr(opts, "audio_data", None),
            getattr(opts, "audio_format", None),
            getattr(opts, "audio_rate", None),
            wait_for_done=not bool(getattr(opts, "streaming", False)),  # streaming ignored here; we use client_content only
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
        Explicitly open a Live session; normally run() does this on demand.

        :param ctx: CtxItem
        :param opts: RealtimeOptions with model/voice/system_prompt attributes
        :param on_text: async callback for text deltas
        :param on_audio: async callback for audio chunks
        :param should_stop: sync callable to signal early termination
        """
        self._ensure_background_loop()
        await self._run_on_owner(self._open_session_internal(ctx, opts, on_text, on_audio, should_stop))

    async def close_session(self):
        """Close the Live session but keep the background loop alive."""
        if not self._owner_loop:
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
        Close current session and open a new one with provided or last-known parameters.
        New session -> new server-side context.

        :param ctx: Optional CtxItem (if None, use last known)
        :param opts: Optional RealtimeOptions (if None, use last known)
        :param on_text: Optional async callback for text deltas (if None, use last known)
        :param on_audio: Optional async callback for audio chunks (if None, use last known)
        :param should_stop: Optional sync callable to signal early termination (if None, use last known)
        """
        self._ensure_background_loop()
        await self._run_on_owner(self._reset_session_internal(ctx, opts, on_text, on_audio, should_stop))

    async def shutdown(self):
        """Gracefully close the current session (if any). Background loop stays alive."""
        if not self._owner_loop:
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
        """
        Close the Live session but keep the background loop alive.

        :param timeout: float - seconds to wait for close
        """
        if not self._owner_loop or not self._owner_loop.is_running():
            return
        fut = asyncio.run_coroutine_threadsafe(self._close_session_internal(), self._owner_loop)
        try:
            fut.result(timeout=timeout)
        except Exception:
            pass

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
        Close current session and open a new one with provided or last-known parameters.

        :param ctx: CtxItem
        :param opts: RealtimeOptions with model/voice/system_prompt attributes
        :param on_text: callback for text deltas
        :param on_audio: callback for audio chunks
        :param should_stop: sync callable to signal early termination
        :param timeout: float - seconds to wait for reset
        """
        self._ensure_background_loop()
        fut = asyncio.run_coroutine_threadsafe(
            self._reset_session_internal(ctx, opts, on_text, on_audio, should_stop),
            self._owner_loop,
        )
        try:
            fut.result(timeout=timeout)
        except Exception:
            pass

    def shutdown_sync(self, timeout: float = 5.0):
        """
        Gracefully close the current session (if any). Background loop stays alive.

        :param timeout: float - seconds to wait for shutdown
        """
        if not self._owner_loop or not self._owner_loop.is_running():
            return
        fut = asyncio.run_coroutine_threadsafe(self._close_session_internal(), self._owner_loop)
        try:
            fut.result(timeout=timeout)
        except Exception:
            pass

    def stop_loop_sync(self, timeout: float = 2.0):
        """
        Stop the background loop thread (after closing any active session).

        :param timeout: float - seconds to wait for thread join
        """
        loop, thread = self._owner_loop, self._loop_thread
        if loop and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
        self._owner_loop = None
        self._loop_thread = None

    # -----------------------------
    # Internal: background loop/dispatch
    # -----------------------------

    def _ensure_background_loop(self):
        """Start the background asyncio loop once and keep it running."""
        if self._owner_loop and self._owner_loop.is_running():
            return
        self._owner_loop = asyncio.new_event_loop()

        def _runner(loop: asyncio.AbstractEventLoop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        self._loop_thread = threading.Thread(
            target=_runner, args=(self._owner_loop,),
            name="Google-RT-Loop", daemon=True
        )
        self._loop_thread.start()

    async def _run_on_owner(self, coro):
        """
        Await a coroutine scheduled on the owner loop from any thread/loop.

        :param coro: coroutine to run
        :return: result of the coroutine
        """
        if not self._owner_loop:
            raise RuntimeError("Owner loop is not running")
        cfut = asyncio.run_coroutine_threadsafe(coro, self._owner_loop)
        return await asyncio.wrap_future(cfut)

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
        Open Live session on the owner loop

        :param ctx: CtxItem
        :param opts: RealtimeOptions with model/voice/system_prompt attributes
        :param on_text: async callback for text deltas
        :param on_audio: async callback for audio chunks
        :param should_stop: sync callable to signal early termination
        :raises RuntimeError: if client not configured or session already open
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

        # Choose a Live-capable model; allow override via opts or ctx
        model_id = getattr(opts, "model", None) or (ctx.model if ctx and getattr(ctx, "model", None) else "gemini-live-2.5-flash")
        voice = getattr(opts, "voice", None) or self._preferred_voice()

        # Build config as a plain dict (stable across SDK versions)
        live_cfg = {
            "response_modalities": ["AUDIO"],
            "speech_config": {
                "voice_config": {"prebuilt_voice_config": {"voice_name": voice}}
            },
            # Provide transcript for audio responses (so UI can display text and we can persist in ctx)
            "output_audio_transcription": {},
        }
        sys_prompt = getattr(opts, "system_prompt", None)
        if sys_prompt:
            live_cfg["system_instruction"] = str(sys_prompt)

        # Save callbacks and ctx
        self._on_text = on_text
        self._on_audio = on_audio
        self._should_stop = should_stop or (lambda: False)
        self._ctx = ctx
        self._last_opts = opts

        # Control primitives
        self._response_done = asyncio.Event()
        self._send_lock = asyncio.Lock()
        self._turn_text_parts = []
        self._last_out_tr = ""

        # Connect session
        self._session_cm = client.aio.live.connect(model=model_id, config=live_cfg)
        self._session = await self._session_cm.__aenter__()
        if self.debug:
            print("[google.open_session] live session connected")

    async def _close_session_internal(self):
        """Close Live session and cleanup."""
        # If a turn receiver is active, let it finish (best effort)
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

        # Reset flow control
        self._response_active = False
        self._response_done = None
        self._send_lock = None
        self._turn_text_parts = []
        self._last_out_tr = ""
        self._audio_buf.clear()
        self._saw_data_stream = False

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
        Close current session and open a new one with provided or last-known parameters.

        :param ctx: Optional CtxItem (if None, use last known)
        :param opts: Optional RealtimeOptions (if None, use last known)
        :param on_text: Optional async callback for text deltas (if None, use last known)
        :param on_audio: Optional async callback for audio chunks (if None, use last known)
        :param should_stop: Optional sync callable to signal early termination (if None, use last known)
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
        Send one manual turn (optional text + optional audio inline_data) and receive its output.

        :param prompt: Optional text prompt
        :param audio_data: Optional audio bytes (will be converted to PCM16@16kHz)
        :param audio_format: Optional input audio format (e.g. "wav", "mp3", "flac"); if None, raw PCM16@16kHz assumed
        :param audio_rate: Optional input audio rate (e.g. 16000); if None, 16000 assumed
        :param wait_for_done: if True, await turn completion before returning
        """
        if not self._session:
            # Reopen if dropped
            if self._ctx and self._last_opts:
                await self._open_session_internal(self._ctx, self._last_opts, self._on_text, self._on_audio, self._should_stop)
            else:
                raise RuntimeError("Session not open. Call open_session(...) first.")

        async with self._send_lock:
            # Ensure previous turn finished
            if self._response_active and self._response_done:
                if self.debug:
                    print("[google.send_turn] waiting for previous response")
                await self._response_done.wait()

            # Build user parts (dicts for portability across SDK versions)
            parts: List[dict] = []
            if prompt and str(prompt).strip():
                parts.append({"text": str(prompt)})

            if audio_data:
                pcm, rate = self._to_pcm16_mono_16k(audio_data, audio_format, audio_rate)
                if pcm:
                    parts.append({
                        "inline_data": {"data": pcm, "mime_type": f"audio/pcm;rate={rate}"}
                    })

            if not parts:
                return  # nothing to send

            # Reset per-turn collectors
            self._turn_text_parts = []
            self._last_out_tr = ""
            self._audio_buf.clear()
            self._saw_data_stream = False

            # Send user turn (server stores it as part of the conversation)
            await self._session.send_client_content(
                turns={"role": "user", "parts": parts},
                turn_complete=True,
            )

            # Start a per-turn receiver task
            self._response_active = True
            self._response_done.clear()
            self._turn_task = asyncio.create_task(self._recv_one_turn(), name="google-live-turn")

        # Optionally wait until this turn completes
        if wait_for_done and self._turn_task:
            try:
                await self._turn_task
            except Exception:
                pass

    async def _recv_one_turn(self):
        """
        Receive exactly one model turn:

        - Prefer audio frames from response.data (PCM16@24kHz).
        - Ignore model_turn.parts.inline_data if response.data already appears in this turn (to avoid duplicates).
        - Stream text (output transcription / text parts).
        - On completion: flush jitter buffer, emit done=True once, and set response_done.
        """
        if self.debug:
            print("[google._recv_one_turn] start")

        try:
            async for response in self._session.receive():
                # 1) Preferred audio source: response.data
                data = getattr(response, "data", None)
                if isinstance(data, (bytes, bytearray)):
                    self._saw_data_stream = True
                    await self._audio_push(bytes(data), final=False)

                # 2) Server content (text + optional inline audio on some backends)
                sc = getattr(response, "server_content", None) or getattr(response, "serverContent", None)
                if not sc:
                    continue

                # 2a) Text transcription for AUDIO responses (often cumulative)
                out_tr = getattr(sc, "output_transcription", None) or getattr(sc, "outputTranscription", None)
                if out_tr and getattr(out_tr, "text", None) and self._on_text:
                    full = str(out_tr.text)
                    # Many backends send cumulative transcript; take only the new delta
                    delta = full[len(self._last_out_tr):] if full.startswith(self._last_out_tr) else full
                    self._last_out_tr = full
                    if delta.strip():
                        self._turn_text_parts.append(delta)
                        try:
                            await self._on_text(delta)
                        except Exception:
                            pass

                # 2b) Model turn parts: text; inline audio only if no response.data in this turn
                model_turn = getattr(sc, "model_turn", None) or getattr(sc, "modelTurn", None)
                if model_turn:
                    parts = getattr(model_turn, "parts", None) or []
                    for p in parts:
                        # text part (TEXT modality)
                        txt = getattr(p, "text", None) or (p.get("text") if isinstance(p, dict) else None)
                        if txt and self._on_text:
                            self._turn_text_parts.append(str(txt))
                            try:
                                await self._on_text(str(txt))
                            except Exception:
                                pass

                        # inline audio (fallback only if data stream absent)
                        if not self._saw_data_stream:
                            inline = getattr(p, "inline_data", None) or (p.get("inline_data") if isinstance(p, dict) else None)
                            if inline:
                                blob = inline if isinstance(inline, gtypes.Blob) else None
                                pdata = getattr(blob, "data", None) if blob else (inline.get("data") if isinstance(inline, dict) else None)
                                if isinstance(pdata, (bytes, bytearray)):
                                    await self._audio_push(bytes(pdata), final=False)

            # Turn finished: flush jitter buffer and mark done
            await self._audio_push(b"", final=True)

        except asyncio.CancelledError:
            # Task cancelled by close/reset; flush best-effort
            try:
                await self._audio_push(b"", final=True)
            except Exception:
                pass
        except Exception as e:
            if self.debug:
                print(f"[google._recv_one_turn] exception: {e!r}")
            # Flush best-effort so playback pipeline closes the stream
            try:
                await self._audio_push(b"", final=True)
            except Exception:
                pass
        finally:
            # Persist textual output to ctx (smart-joined, no artificial newlines)
            try:
                if self.window and self.window.core and self._ctx:
                    txt = self._coalesce_text(self._turn_text_parts)
                    if txt:
                        self._ctx.output = txt
                    self.window.core.ctx.update_item(self._ctx)
            except Exception:
                pass

            # Unblock waiters and clear flags
            self._response_active = False
            if self._response_done:
                try:
                    self._response_done.set()
                except Exception:
                    pass

            if self.debug:
                print("[google._recv_one_turn] done")

    # -----------------------------
    # Helpers
    # -----------------------------

    def _preferred_voice(self) -> str:
        """
        Resolve preferred Google voice from settings.

        :return: voice name
        """
        try:
            v = self.window.core.plugins.get_option("audio_output", "google_genai_tts_voice")
            if v:
                mapping = {"kore": "Kore", "puck": "Puck", "charon": "Charon", "verse": "Verse", "legend": "Legend"}
                return mapping.get(str(v).strip().lower(), str(v))
        except Exception:
            pass
        return "Kore"

    def _coalesce_text(self, parts: List[str]) -> str:
        """
        Join streaming text chunks into a clean final string:

        - Preserve only "hard" line breaks that actually arrived in chunks.
        - Collapse intra-line whitespace; remove artificial spaces before punctuation.

        :param parts: list of text chunks
        :return: clean joined text
        """
        if not parts:
            return ""

        # Build while preserving explicit newlines inside chunks
        out: List[str] = []
        for piece in parts:
            if not piece:
                continue
            s = str(piece)

            # Normalize internal whitespace but preserve explicit newlines
            # 1) Collapse runs of spaces/tabs (not touching '\n')
            s = re.sub(r"[ \t\f\v]+", " ", s)
            # 2) Trim spaces around newlines
            s = re.sub(r"[ \t]*\n[ \t]*", "\n", s)

            if not out:
                out.append(s.strip())
                continue

            # If the previous token ends with a newline or this piece starts with one, do not inject extra space
            if out[-1].endswith("\n") or s.startswith("\n"):
                out.append(s.lstrip())
            else:
                # Otherwise, append with a single space
                out.append((" " + s.strip()))

        text = "".join(out)

        # Remove space before punctuation like , . ; : ! ? %
        text = re.sub(r"[ \t]+([,.;:!?%])", r"\1", text)
        # Remove space before closing brackets/quotes
        text = re.sub(r"[ \t]+([\)\]\}])", r"\1", text)
        text = re.sub(r"[ \t]+(['\"])", r"\1", text)

        # Collapse multiple blank lines to a single blank line
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    async def _audio_push(self, data: bytes, final: bool = False):
        """
        Accumulate PCM16 mono @ 24kHz into a jitter buffer and flush in ~_OUT_CHUNK_MS chunks.

        :param data: bytes of PCM16 mono @ 24kHz
        :param final: if True, flush remainder and emit done=True
        """
        if not self._on_audio:
            return

        if data:
            self._audio_buf.extend(data)

        threshold = self._OUT_BYTES_PER_MS * self._OUT_CHUNK_MS

        # Emit full-size chunks
        while len(self._audio_buf) >= threshold:
            chunk = self._audio_buf[:threshold]
            del self._audio_buf[:threshold]
            try:
                await self._on_audio(bytes(chunk), "audio/pcm", self._OUT_RATE, 1, False)
            except Exception:
                pass

        if final:
            # Flush remainder (if any), then send a single done=True
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

    def _to_pcm16_mono_16k(
        self,
        data: bytes,
        fmt: Optional[str],
        rate_hint: Optional[int],
    ) -> Tuple[bytes, int]:
        """
        Convert input audio to PCM16 mono @ 16kHz for inline_data.

        :param data: input audio bytes
        :param fmt: input audio format (e.g. "wav", "mp3", "flac"); if None, raw PCM16@16kHz assumed
        :param rate_hint: input audio rate (e.g. 16000); if None, 16000 assumed
        :return: tuple (pcm_bytes, rate)
        """
        if not data:
            return b"", self._IN_RATE

        fmt = (fmt or "").lower().strip()

        # Raw PCM16
        if fmt in ("pcm16", "pcm", "raw"):
            src_rate = int(rate_hint) if rate_hint else self._IN_RATE
            pcm = data
            if src_rate != self._IN_RATE:
                try:
                    pcm, _ = audioop.ratecv(pcm, 2, 1, src_rate, self._IN_RATE, None)
                except Exception:
                    return b"", self._IN_RATE
            return pcm, self._IN_RATE

        # WAV container
        try:
            with wave.open(io.BytesIO(data), "rb") as wf:
                sr = wf.getframerate() or self._IN_RATE
                ch = wf.getnchannels() or 1
                sw = wf.getsampwidth() or 2
                frames = wf.readframes(wf.getnframes())

            if sw != 2:
                frames = audioop.lin2lin(frames, sw, 2)
            if ch == 2:
                frames = audioop.tomono(frames, 2, 0.5, 0.5)
            elif ch != 1:
                frames = audioop.tomono(frames, 2, 1.0, 0.0)
            if sr != self._IN_RATE:
                frames, _ = audioop.ratecv(frames, 2, 1, sr, self._IN_RATE, None)

            return frames, self._IN_RATE
        except Exception:
            try:
                self.window.core.debug.info("[google.live] Failed to parse input audio; dropping.")
            except Exception:
                pass
            return b"", self._IN_RATE