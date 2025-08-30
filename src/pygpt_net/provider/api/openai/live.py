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
import base64
import io
import json
import threading
import wave
import audioop
from typing import Optional, Callable, Awaitable

import websockets

from pygpt_net.core.types import MODE_AUDIO
from pygpt_net.item.ctx import CtxItem


class OpenAIRealtimeClient:
    """
    OpenAI Realtime API client with persistent session and a dedicated background event loop.

    Key points:
    - A single background asyncio loop runs in its own thread for the lifetime of the client.
    - One websocket connection (session) at a time; multiple "turns" (send_turn) are serialized.
    - No server VAD: manual turn control via input_audio_buffer.* + response.create.
    - Safe to call run()/send_turn()/reset()/shutdown() from any thread or event loop.
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

        # Background event loop in a dedicated thread
        self._owner_loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None

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
        self._ctx = None

        self._DEFAULT_RATE = 24000

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

        This is the main entrypoint.

        :param ctx: CtxItem with model and conversation
        :param opts: Options object with prompt/audio/voice/etc.
        :param on_text: Async callback for text deltas
        :param on_audio: Async callback for audio chunks
        :param should_stop: Sync callback to signal barge-in (cancel active response)
        """
        self._ensure_background_loop()
        self._ctx = ctx

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

        :param ctx: CtxItem with model and conversation
        :param opts: Options object with prompt/audio/voice/etc.
        :param on_text: Async callback for text deltas
        :param on_audio: Async callback for audio chunks
        :param should_stop: Sync callback to signal barge-in (cancel active response)
        """
        self._ensure_background_loop()
        await self._run_on_owner(self._open_session_internal(ctx, opts, on_text, on_audio, should_stop))

    async def close_session(self):
        """Close the websocket session but keep the background loop alive."""
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
        Close the current session and open a fresh one (new conversation on the server).

        If parameters are omitted, last-known ones are used.

        :param ctx: Optional CtxItem with model and conversation
        :param opts: Optional Options object with prompt/audio/voice/etc.
        :param on_text: Optional async callback for text deltas
        :param on_audio: Optional async callback for audio chunks
        :param should_stop: Optional sync callback to signal barge-in (cancel active response)
        """
        self._ensure_background_loop()
        await self._run_on_owner(self._reset_session_internal(ctx, opts, on_text, on_audio, should_stop))

    async def shutdown(self):
        """
        Gracefully close the current session (if any).
        Does NOT stop the background loop; use stop_loop_sync() or shutdown_and_stop() to also stop the loop.
        """
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
        Synchronous wrapper around close_session().

        Closes the WS but leaves the loop alive for reuse.

        :param timeout: Timeout in seconds to wait for the close operation
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
        Synchronous wrapper around reset_session().

        Closes the current session and opens a new one with provided or last-known parameters.

        :param ctx: Optional CtxItem with model and conversation
        :param opts: Optional Options object with prompt/audio/voice/etc.
        :param on_text: Optional async callback for text deltas
        :param on_audio: Optional async callback for audio chunks
        :param should_stop: Optional sync callback to signal barge-in (cancel active response)
        :param timeout: Timeout in seconds to wait for the reset operation
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
        Synchronous wrapper around shutdown() — closes the WS but leaves the loop alive.

        :param timeout: Timeout in seconds to wait for the shutdown operation
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
        Stop the background event loop thread. Call this at app shutdown
        if you don't plan to reuse the client.

        :param timeout: Timeout in seconds to wait for the thread to join
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
            name="OpenAI-RT-Loop", daemon=True
        )
        self._loop_thread.start()

    async def _run_on_owner(self, coro):
        """
        Await a coroutine scheduled on the owner loop from any thread/loop.

        :param coro: Coroutine to run on the owner loop
        :return: Result of the coroutine
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
        Open WS and configure the Realtime session on the owner loop.

        :param ctx: CtxItem with model and conversation
        :param opts: RuntimeOptions object with prompt/audio/voice/etc.
        :param on_text: Async callback for text deltas
        :param on_audio: Async callback for audio chunks
        :param should_stop: Sync callback to signal barge-in (cancel active response)
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

        url = f"{self.WS_URL}?model={model_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1",
        }

        # Save callbacks and context
        self._on_text = on_text
        self._on_audio = on_audio
        self._should_stop = should_stop or (lambda: False)
        self._ctx = ctx
        self._last_opts = opts

        # Create control primitives on the owner loop
        self._response_done = asyncio.Event()
        self._send_lock = asyncio.Lock()

        if self.debug:
            print(f"[open_session] owner_loop={id(asyncio.get_running_loop())}")

        # Connect WS
        self.ws = await websockets.connect(
            url,
            additional_headers=headers,
            max_size=16 * 1024 * 1024,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
        )
        if self.debug:
            print("[open_session] WS connected")

        # Configure session (manual turns: we will call response.create ourselves)
        session_update = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "voice": voice,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": None,
                **({"instructions": str(getattr(opts, "system_prompt"))} if getattr(opts, "system_prompt", None) else {}),
            },
        }
        await self.ws.send(json.dumps(session_update))
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

        # Reset control primitives (they belong to old session/loop state)
        self._response_active = False
        self._response_done = None
        self._send_lock = None

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

        :param ctx: Optional CtxItem with model and conversation
        :param opts: Optional Options object with prompt/audio/voice/etc.
        :param on_text: Optional async callback for text deltas
        :param on_audio: Optional async callback for audio chunks
        :param should_stop: Optional sync callback to signal barge-in (cancel active response)
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

        :param prompt: Optional text prompt
        :param audio_data: Optional audio data (raw PCM16 mono or WAV)
        :param audio_format: Optional audio format hint (e.g. "wav", "pcm16", "raw")
        :param audio_rate: Optional audio sample rate hint (e.g. 16000, 24000)
        :param wait_for_done: If True, await response.done before returning
        :raises RuntimeError: If session is not open
        """
        if not self.ws:
            # If session dropped remotely, try to reopen from last state
            if self._ctx and self._last_opts:
                await self._open_session_internal(self._ctx, self._last_opts, self._on_text, self._on_audio, self._should_stop)
            else:
                raise RuntimeError("Session not open. Call open_session(...) first.")

        # Serialize all sends to a single WS writer
        async with self._send_lock:
            # Ensure previous response is finished
            if self._response_active and self._response_done:
                if self.debug:
                    print("[send_turn] waiting for previous response")
                await self._response_done.wait()

            # Optional text
            if prompt and str(prompt).strip():
                await self.ws.send(json.dumps({
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": str(prompt)}],
                    },
                }))

            # Optional audio (PCM16 mono chunks)
            if audio_data:
                sr, _ch, pcm = self._coerce_to_pcm16_mono(audio_data, audio_format, audio_rate)
                # Pad to at least ~100ms to avoid tiny buffers
                min_bytes_100ms = int(sr * 2 * 0.100)
                if len(pcm) < min_bytes_100ms:
                    pcm += b"\x00" * (min_bytes_100ms - len(pcm))

                await self.ws.send(json.dumps({"type": "input_audio_buffer.clear"}))
                for chunk in self._iter_pcm_chunks(pcm, sr, ms=50):
                    print(chunk)
                    if not chunk:
                        continue
                    await self.ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(chunk).decode("utf-8"),
                    }))
                await self.ws.send(json.dumps({"type": "input_audio_buffer.commit"}))

            # Trigger exactly one assistant response
            if self._response_done:
                self._response_done.clear()
            await self.ws.send(json.dumps({"type": "response.create"}))
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
    # Internal: receive loop
    # -----------------------------

    async def _recv_loop(self):
        """
        Single receiver loop for the entire session.

        Processes incoming events and dispatches to callbacks.
        Runs on the owner loop.

        Events:
        - response.created
        - response.text.delta
        - response.text.done
        - response.audio.delta
        - response.audio.done
        - response.done
        - error
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
                if self.debug:
                    # print("[_recv_loop]", etype)
                    pass

                if etype == "response.created":
                    self._response_active = True
                    audio_done = False

                elif etype in ("response.text.delta", "response.output_text.delta", "response.audio_transcript.delta"):
                    delta = ev.get("delta") or ev.get("text")
                    if isinstance(delta, dict) and "text" in delta:
                        delta = delta["text"]
                    if delta and self._on_text:
                        try:
                            await self._on_text(str(delta))
                        except Exception:
                            pass

                elif etype in ("response.text.done", "response.output_text.done", "response.audio_transcript.done"):
                    # Final for text/transcript; response.done will conclude the turn
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
                    if not audio_done and self._on_audio:
                        try:
                            await self._on_audio(b"", "audio/pcm", DEFAULT_RATE, 1, True)
                        except Exception:
                            pass
                        audio_done = True

                elif etype == "response.done":
                    # Ensure audio finalized
                    if not audio_done and self._on_audio:
                        try:
                            await self._on_audio(b"", "audio/pcm", DEFAULT_RATE, 1, True)
                        except Exception:
                            pass
                        audio_done = True

                    self._response_active = False
                    if self._response_done:
                        self._response_done.set()

                    # Persist context (Realtime has no token usage reporting)
                    try:
                        if self.window and self.window.core and self._ctx:
                            try:
                                transcript = self._extract_text_from_response_done(ev)
                                print(transcript)
                                if transcript:
                                    self._ctx.output = transcript
                            except Exception:
                                pass
                            self.window.core.ctx.update_item(self._ctx)
                        # else ignore silently
                    except Exception as e:
                        print(e)
                        pass

                elif etype == "error":
                    msg = (ev.get("error") or {}).get("message") or ""
                    # If server reports active response collision, just wait for response.done
                    if "already has an active response" in msg.lower():
                        continue
                    # Unblock waiters to avoid deadlocks
                    if self._response_done:
                        self._response_done.set()
                    if self.debug:
                        print(f"[_recv_loop] error: {msg}")

                # Other events (session.created/updated, conversation.item.created, etc.) are ignored

        except Exception as e:
            if self.debug:
                print(f"[_recv_loop] exception: {e!r}")
        finally:
            if self.debug:
                print("[_recv_loop] stopped")
            # Best-effort close and cleanup
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

        Returns voice ID or "alloy" if not set.
        """
        try:
            v = self.window.core.plugins.get_option("audio_output", "openai_voice")
            if v:
                return str(v)
        except Exception:
            pass
        return "alloy"

    def _coerce_to_pcm16_mono(
        self,
        data: bytes,
        fmt: Optional[str],
        rate_hint: Optional[int]
    ) -> tuple[int, int, bytes]:
        """
        Convert input audio (raw PCM or WAV) to PCM16 mono bytes.

        :param data: Input audio data
        :param fmt: Optional format hint ("pcm16", "wav", etc.)
        :param rate_hint: Optional sample rate hint (e.g. 16000, 24000)
        :return: Tuple (sample_rate, channels, pcm16_mono_bytes)
        """
        if not data:
            return (self._DEFAULT_RATE, 1, b"")

        fmt = (fmt or "").lower()
        if fmt in ("pcm16", "pcm", "raw"):
            sr = int(rate_hint) if rate_hint else self._DEFAULT_RATE
            return (sr, 1, data)

        # Treat everything else as WAV
        try:
            with wave.open(io.BytesIO(data), "rb") as wf:
                sr = wf.getframerate()
                ch = wf.getnchannels()
                sw = wf.getsampwidth()
                frames = wf.readframes(wf.getnframes())

            if sw != 2:
                frames = audioop.lin2lin(frames, sw, 2)

            if ch == 2:
                frames = audioop.tomono(frames, 2, 0.5, 0.5)
            elif ch != 1:
                frames = audioop.tomono(frames, 2, 1.0, 0.0)

            return (sr or self._DEFAULT_RATE, 1, frames)
        except Exception:
            sr = int(rate_hint) if rate_hint else self._DEFAULT_RATE
            return (sr, 1, data)

    def _iter_pcm_chunks(self, pcm: bytes, sr: int, ms: int = 50) -> list[bytes]:
        """
        Split PCM16 mono into ~ms byte chunks.

        :param pcm: PCM16 mono bytes
        :param sr: Sample rate (e.g. 16000, 24000)
        :param ms: Chunk size in milliseconds
        :return: List of byte chunks
        """
        bytes_per_ms = int(sr * 2 / 1000)
        n = max(bytes_per_ms * ms, 1)
        return [pcm[i:i + n] for i in range(0, len(pcm), n)]

    def _extract_text_from_response_done(self, ev: dict) -> str:
        """
        Extract assistant text from response.done payload.

        - prefers content.type == "audio" -> content.transcript
        - also collects content.type in {"text", "output_text", "input_text"} -> content.text
        Returns a joined string (may be empty if nothing textual found).

        :param ev: response.done event dict
        :return: Extracted text
        """
        res = ev.get("response") or {}
        out = res.get("output") or []
        parts: list[str] = []

        for item in out:
            if not isinstance(item, dict):
                continue
            if item.get("type") not in ("message", "tool_result", "function_call_result", "response"):
                # Most common is "message", but keep a few extras for future-proofing
                pass
            content_list = item.get("content") or []
            for c in content_list:
                if not isinstance(c, dict):
                    continue
                ctype = c.get("type")
                # Case 1: audio content with transcript
                if ctype == "audio":
                    tr = c.get("transcript")
                    if tr:
                        parts.append(str(tr))
                # Case 2: textual content variants
                elif ctype in ("text", "output_text", "input_text"):
                    txt = c.get("text")
                    if isinstance(txt, dict):
                        # Some variants use nested {"text": "..."} or {"value": "..."}
                        txt = txt.get("text") or txt.get("value")
                    if txt:
                        parts.append(str(txt))

        # Fallback: sometimes providers add a top-level text in other shapes (rare)
        text = "\n".join(t.strip() for t in parts if t and str(t).strip())
        return text