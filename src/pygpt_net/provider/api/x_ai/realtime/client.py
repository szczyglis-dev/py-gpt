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
import io
import json
import websockets

from typing import Optional, Callable, Awaitable
from urllib.parse import urlencode

from pygpt_net.core.events import RealtimeEvent
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
    tools_signature,
    build_tool_outputs_payload,
)
from pygpt_net.core.realtime.shared.turn import TurnMode, apply_turn_mode_openai
from pygpt_net.core.realtime.shared.session import set_ctx_rt_handle, set_rt_session_expires_at


class xAIIRealtimeClient:
    """
    xAI Realtime API client with persistent session and a dedicated background event loop.

    Key points:
    - A single background asyncio loop runs in its own thread for the lifetime of the client.
    - One websocket connection (session) at a time; multiple "turns" (send_turn) are serialized.
    - Supports server VAD (auto-turn) and manual turn control (input_audio_buffer.* + response.create).
    - Safe to call run()/send_turn()/reset()/shutdown() from any thread or event loop.

    Session resumption:
    - The official Realtime API does not expose a documented server-side "resume" for closed WS sessions.
      We still persist the server-provided handle (session or conversation id) and surface it via ctx.extra["rt_session_id"].
      If opts.rt_session_id is provided and differs from the current in-memory handle, we reset the connection and attempt
      to reconnect with a "session_id" query parameter. If that fails, we fall back to the standard URL.
    """

    WS_URL = "wss://api.x.ai/v1/realtime"

    def __init__(self, window=None, debug: bool = False):
        """
        xAI Realtime API client

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
        self._bg = BackgroundLoop(name="xAI-RT-Loop")

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
        on_audio: Optional[Callable[[bytes, str], Awaitable[None]]] = None,
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

    def _xai_tool_shape(self, tool: dict) -> dict:
        """
        Ensure xAI-compatible tool shape:
        - function tools use top-level name/parameters (no nested "function" object)
        - known provider tools: file_search (vector_store_ids), web_search, x_search
        Unknown provider-only tools are dropped to avoid server-side validation issues.
        """
        try:
            if not isinstance(tool, dict):
                return tool

            t = dict(tool)

            # Convert OpenAI Realtime "function": {...} into xAI top-level form
            if t.get("type") == "function":
                if "function" in t and isinstance(t["function"], dict):
                    f = t["function"]
                    name = f.get("name") or t.get("name")
                    desc = f.get("description") or t.get("description") or ""
                    params = f.get("parameters") or t.get("parameters") or {"type": "object"}
                    return {
                        "type": "function",
                        "name": name,
                        "description": desc,
                        "parameters": params if isinstance(params, dict) else {"type": "object"},
                    }
                # Already top-level form, return as-is
                return {
                    "type": "function",
                    "name": t.get("name"),
                    "description": t.get("description") or "",
                    "parameters": t.get("parameters") or {"type": "object"},
                }

            # Map collections_search -> file_search
            if t.get("type") == "collections_search":
                vec_ids = t.get("collection_ids") or t.get("vector_store_ids") or []
                max_num = t.get("max_num_results") if isinstance(t.get("max_num_results"), int) else None
                out = {
                    "type": "file_search",
                    "vector_store_ids": vec_ids if isinstance(vec_ids, list) else [],
                }
                if max_num is not None:
                    out["max_num_results"] = max_num
                return out

            # Pass-through for known provider tools
            if t.get("type") in ("file_search", "web_search", "x_search"):
                return t

            # code_interpreter is not documented for xAI Voice Agent; drop it
            if t.get("type") == "code_interpreter":
                return {}

            return t
        except Exception:
            return tool

    def _compose_xai_tools(self, tools: Optional[list], remote_tools: Optional[list]) -> list:
        """
        Compose a single list of tools in xAI shape; filters out unsupported ones.
        """
        out: list = []
        try:
            fn = tools or []
            rt = remote_tools or []

            # Sanitize function tools from our shared helper first
            fn = sanitize_function_tools(fn) or fn

            # Merge order: provider tools first (as in xAI docs), then function tools
            for t in (rt or []):
                shaped = self._xai_tool_shape(t)
                if isinstance(shaped, dict) and shaped:
                    out.append(shaped)
            for t in (fn or []):
                shaped = self._xai_tool_shape(t)
                if isinstance(shaped, dict) and shaped:
                    out.append(shaped)
        except Exception:
            pass
        return out

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
        api_key = self.window.core.config.get("api_key_xai")
        if not api_key:
            raise RuntimeError("xAPI key not configured")

        model_id = getattr(opts, "model", None) or (ctx.model if ctx and ctx.model else "grok-3")
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

        # Prefer plain WS URL; fallback to query-parameter variant
        url_plain = self.WS_URL
        q = {"model": model_id}
        if resume_sid:
            q["session_id"] = resume_sid
        url_with_q = f"{self.WS_URL}?{urlencode(q)}"

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

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

        # Connect WS with robust fallback
        try:
            self.ws = await websockets.connect(
                url_plain,
                additional_headers=headers,
                max_size=16 * 1024 * 1024,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
            )
        except Exception as e:
            if self.debug:
                print(f"[open_session] connect plain failed: {e!r}")
            try:
                self.ws = await websockets.connect(
                    url_with_q,
                    additional_headers=headers,
                    max_size=16 * 1024 * 1024,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                )
            except Exception as e2:
                if self.debug:
                    print(f"[open_session] fallback connect failed: {e2!r}")
                self.ws = None

        if not self.ws:
            raise RuntimeError("xAI Realtime: WebSocket connect failed")

        if self.debug:
            print("[open_session] WS connected")

        # Session payload compatible with xAI Voice Agent
        session_payload = {
            "type": "session.update",
            "session": {
                "voice": voice,
                "audio": {
                    "input": {"format": {"type": "audio/pcm", "rate": self._DEFAULT_RATE}},
                    "output": {"format": {"type": "audio/pcm", "rate": self._DEFAULT_RATE}},
                },
            },
        }
        if getattr(opts, "system_prompt", None):
            session_payload["session"]["instructions"] = str(getattr(opts, "system_prompt"))

        # Turn detection (server VAD) or manual turns
        turn_mode = TurnMode.AUTO if bool(getattr(opts, "auto_turn", False)) else TurnMode.MANUAL
        apply_turn_mode_openai(session_payload, turn_mode)
        self._tune_openai_vad(session_payload, opts)

        # Attach tools to session (xAI expects tools only in session.update)
        try:
            session_tools = self._compose_xai_tools(
                getattr(opts, "tools", None),
                getattr(opts, "remote_tools", None),
            )
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

        # Unblock any waiters before clearing handles
        try:
            if self._response_done and not self._response_done.is_set():
                self._response_done.set()
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

        # Determine whether we should trigger a response for this turn
        def _bool(v) -> bool:
            try:
                return bool(v)
            except Exception:
                return False

        is_auto_turn = _bool(getattr(self._last_opts or object(), "auto_turn", False))
        has_text = False
        if prompt is not None:
            p = str(prompt).strip()
            has_text = bool(p and p != "...")
        has_audio = bool(audio_data)
        reply_hint = False
        try:
            extra = getattr(self._last_opts, "extra", None)
            if isinstance(extra, dict):
                reply_hint = bool(extra.get("reply", False))
        except Exception:
            pass

        if not has_text and not has_audio and not reply_hint:
            if self.debug:
                print("[send_turn] skipped: manual mode with empty input; waiting for explicit commit")
            return

        wait_prev: Optional[asyncio.Event] = None
        wait_curr: Optional[asyncio.Event] = None

        async with self._send_lock:
            # Ensure previous response is finished (snapshot the handle to avoid race with close)
            if self._response_active and self._response_done:
                wait_prev = self._response_done

            # Optional text
            if has_text:
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

            # Optional audio (manual turn control flow)
            if has_audio:
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

                # Append PCM and commit input buffer
                for chunk in iter_pcm_chunks(pcm, sr, ms=50):
                    if not chunk:
                        continue
                    await self.ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(chunk).decode("utf-8"),
                    }))
                await self.ws.send(json.dumps({"type": "input_audio_buffer.commit"}))

            # If we were waiting for a previous response, do it inside lock handoff-safe
            if wait_prev:
                try:
                    if self.debug:
                        print("[send_turn] waiting for previous response")
                    await wait_prev.wait()
                except Exception:
                    pass

            # Prepare wait handle for the response about to start
            if self._response_done is None:
                self._response_done = asyncio.Event()
            else:
                try:
                    self._response_done.clear()
                except Exception:
                    self._response_done = asyncio.Event()
            wait_curr = self._response_done  # snapshot for race-free waiting

            # Build minimal response payload for xAI (tools are configured only via session.update)
            payload = {
                "type": "response.create",
                "response": {"modalities": ["text", "audio"]},
            }

            await self.ws.send(json.dumps(payload))
            if self.debug:
                print("[send_turn] response.create sent")

        # Optionally wait for response.done (otherwise return immediately)
        if wait_for_done and wait_curr:
            if self.debug:
                print("[send_turn] waiting for response.done")
            try:
                await wait_curr.wait()
            except Exception:
                pass
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

            # With server VAD enabled, the server commits the buffer automatically.
            if is_final:
                if self.debug:
                    print("[_rt_handle_audio_input] final chunk sent (server VAD will commit)")

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

            # 3) Trigger the assistant response now
            try:
                await self.ws.send(json.dumps({
                    "type": "response.create",
                    "response": {"modalities": ["text", "audio"]},
                }))
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

        # Compose xAI-shaped session tools (provider tools + function tools)
        try:
            session_tools = self._compose_xai_tools(
                tools if tools is not None else getattr(self._last_opts, "tools", None),
                remote_tools if remote_tools is not None else getattr(self._last_opts, "remote_tools", None),
            )
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

        wait_ev: Optional[asyncio.Event] = None
        async with self._send_lock:
            # Emit one conversation.item.create per tool output
            for it in outputs:
                payload = {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": it["call_id"],
                        "output": it["output"],
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
                wait_ev = self._response_done  # snapshot for race-free waiting
                await self.ws.send(json.dumps({
                    "type": "response.create",
                    "response": {"modalities": ["text", "audio"]},
                }))

        # Wait for the follow-up response to complete
        if continue_turn and wait_for_done and wait_ev:
            try:
                await wait_ev.wait()
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
                    continue

                try:
                    ev = json.loads(raw)
                except Exception:
                    continue

                etype = ev.get("type")

                # ---- session / conversation lifecycle ----
                if etype in ("session.created", "session.updated"):
                    sess = ev.get("session") or {}
                    sid = sess.get("id")
                    if isinstance(sid, str) and sid.strip():
                        self._rt_session_id = sid.strip()
                        set_ctx_rt_handle(self._ctx, self._rt_session_id, self.window)
                        if self.debug:
                            print(f"[_recv_loop] session id: {self._rt_session_id}")
                    exp = sess.get("expires_at") or sess.get("expiresAt")
                    try:
                        if isinstance(exp, (int, float)) and exp > 0:
                            self._rt_session_expires_at = int(exp)
                            set_rt_session_expires_at(self._ctx, self._rt_session_expires_at, self.window)
                    except Exception:
                        pass
                    continue

                if etype == "conversation.created":
                    conv = ev.get("conversation") or {}
                    cid = conv.get("id")
                    if isinstance(cid, str) and cid.strip():
                        self._rt_session_id = cid.strip()
                        set_ctx_rt_handle(self._ctx, self._rt_session_id, self.window)
                        if self.debug:
                            print(f"[_recv_loop] conversation id: {self._rt_session_id}")
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

                elif etype in ("conversation.item.committed", "input_audio_buffer.committed"):
                    if self.debug:
                        print("[_recv_loop] audio_buffer committed")
                    if self._last_opts:
                        self._last_opts.rt_signals.response.emit(RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_COMMIT, {
                            "ctx": self._ctx,
                        }))

                elif etype == "input_audio_buffer.cleared":
                    if self.debug:
                        print("[_recv_loop] audio_buffer.cleared")

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

                elif etype in ("conversation.item.created", "conversation.item.added"):
                    if self.debug:
                        print("[_recv_loop] conversation item event")
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

                elif etype in ("response.audio_transcript.delta", "response.output_audio_transcript.delta"):
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

                elif etype in ("response.text.done", "response.output_text.done",
                               "response.audio_transcript.done", "response.output_audio_transcript.done"):
                    if self.debug:
                        print("[_recv_loop] text/transcript done")

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

                elif etype in ("response.audio.delta", "response.output_audio.delta"):
                    b64 = ev.get("delta")
                    if b64 and self._on_audio:
                        try:
                            data = base64.b64decode(b64)
                            await self._on_audio(data, "audio/pcm", DEFAULT_RATE, 1, False)
                        except Exception:
                            pass

                elif etype in ("response.audio.done", "response.output_audio.done"):
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
                    if not audio_done and self._on_audio:
                        try:
                            await self._on_audio(b"", "audio/pcm", DEFAULT_RATE, 1, True)
                        except Exception:
                            pass
                        audio_done = True

                    self._response_active = False

                    try:
                        resp_obj = ev.get("response") or {}
                        self._rt_capture_usage(resp_obj)
                    except Exception:
                        pass

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

                            if self._rt_state and self._rt_state["citations"]:
                                if self._ctx.urls is None:
                                    self._ctx.urls = []
                                for u in self._rt_state["citations"]:
                                    if u not in self._ctx.urls:
                                        self._ctx.urls.append(u)

                            if self._rt_state and self._rt_state["image_paths"]:
                                if not isinstance(self._ctx.images, list):
                                    self._ctx.images = []
                                for p in self._rt_state["image_paths"]:
                                    if p not in self._ctx.images:
                                        self._ctx.images.append(p)

                            self.window.core.ctx.update_item(self._ctx)
                    except Exception:
                        pass

                    try:
                        files = (self._rt_state or {}).get("files") or []
                        if files:
                            self.window.core.api.openai.container.download_files(self._ctx, files)
                    except Exception:
                        pass

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

                    try:
                        tcs = (self._rt_state or {}).get("tool_calls") or []
                        if tcs:
                            self._last_tool_calls = list(tcs)
                    except Exception:
                        pass

                    if self._response_done:
                        self._response_done.set()

                    if self._last_opts:
                        self._last_opts.rt_signals.response.emit(RealtimeEvent(RealtimeEvent.RT_OUTPUT_TURN_END, {
                            "ctx": self._ctx,
                        }))

                    self._rt_state = None

                elif etype == "error":
                    if self.debug:
                        print(f"[_recv_loop] error event: {ev}")
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
                if self._response_done and not self._response_done.is_set():
                    self._response_done.set()
            except Exception:
                pass
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
        return "Ara"

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
                self._ctx.extra["input_transcript"] = str(transcript)
                if not getattr(self._last_opts, "prompt", None):
                    self._ctx.input = str(transcript)
                self.window.core.ctx.update_item(self._ctx)
        except Exception:
            pass

    def _tune_openai_vad(self, session_payload: dict, opts) -> None:
        """
        Increase end-of-speech hold for server VAD (auto-turn) to reduce premature turn endings.
        """
        try:
            sess = session_payload.get("session") or {}
            td = sess.get("turn_detection")
            if not isinstance(td, dict):
                return

            target_ms = getattr(opts, "vad_end_silence_ms", None)
            if not isinstance(target_ms, (int, float)) or target_ms <= 0:
                base = int(td.get("silence_duration_ms") or 500)
                target_ms = max(base, 2000)

            td["silence_duration_ms"] = int(target_ms)

            prefix_ms = getattr(opts, "vad_prefix_padding_ms", None)
            if isinstance(prefix_ms, (int, float)) and prefix_ms >= 0:
                td["prefix_padding_ms"] = int(prefix_ms)
        except Exception:
            pass

    def update_session_autoturn_sync(
        self,
        enabled: bool,
        silence_ms: Optional[int] = None,
        prefix_ms: Optional[int] = None,
        timeout: float = 5.0,
    ):
        """
        Synchronous helper to enable/disable auto-turn (VAD) mode on the live session.
        You can override silence and prefix (ms) as 2nd and 3rd args.
        If WS is not open, this updates self._last_opts and returns.
        """
        self._ensure_background_loop()
        try:
            self._bg.run_sync(
                self._update_session_autoturn_internal(enabled, silence_ms, prefix_ms),
                timeout=timeout
            )
        except Exception:
            pass

    async def _update_session_autoturn_internal(
        self,
        enabled: bool,
        silence_ms: Optional[int] = None,
        prefix_ms: Optional[int] = None,
    ):
        """
        Owner-loop implementation for toggling auto-turn (server/semantic VAD) at runtime
        with optional silence and prefix overrides (milliseconds).
        """
        # If socket is not open, just cache into last opts
        if not self.ws:
            try:
                if self._last_opts:
                    setattr(self._last_opts, "auto_turn", bool(enabled))
                    if silence_ms is not None:
                        setattr(self._last_opts, "vad_end_silence_ms", int(silence_ms))
                    if prefix_ms is not None:
                        setattr(self._last_opts, "vad_prefix_padding_ms", int(prefix_ms))
            except Exception:
                pass
            if self.debug:
                print("[update_session_autoturn] WS not open; cached for next session")
            return

        if self._send_lock is None:
            self._send_lock = asyncio.Lock()

        async with self._send_lock:
            try:
                payload: dict = {"type": "session.update", "session": {}}
                turn_mode = TurnMode.AUTO if enabled else TurnMode.MANUAL
                apply_turn_mode_openai(payload, turn_mode)

                if enabled:
                    sess = payload.get("session", {})
                    td = sess.get("turn_detection")

                    try:
                        vad_type = getattr(self._last_opts, "vad_type", None)
                        if isinstance(vad_type, str) and vad_type in ("server_vad", "semantic_vad"):
                            if isinstance(td, dict):
                                td["type"] = vad_type
                    except Exception:
                        pass

                    try:
                        thr = getattr(self._last_opts, "vad_threshold", None)
                        if isinstance(thr, (int, float)) and isinstance(td, dict) and td.get("type") == "server_vad":
                            td["threshold"] = float(thr)
                    except Exception:
                        pass

                    self._tune_openai_vad(payload, self._last_opts)

                    if isinstance(td, dict):
                        if silence_ms is not None:
                            td["silence_duration_ms"] = int(silence_ms)
                        if prefix_ms is not None:
                            td["prefix_padding_ms"] = int(prefix_ms)

                        try:
                            cr = getattr(self._last_opts, "vad_create_response", None)
                            if isinstance(cr, bool):
                                td["create_response"] = cr
                        except Exception:
                            pass
                        try:
                            ir = getattr(self._last_opts, "vad_interrupt_response", None)
                            if isinstance(ir, bool):
                                td["interrupt_response"] = ir
                        except Exception:
                            pass

                await self.ws.send(json.dumps(payload))

                try:
                    if self._last_opts:
                        setattr(self._last_opts, "auto_turn", bool(enabled))
                        if silence_ms is not None:
                            setattr(self._last_opts, "vad_end_silence_ms", int(silence_ms))
                        if prefix_ms is not None:
                            setattr(self._last_opts, "vad_prefix_padding_ms", int(prefix_ms))
                except Exception:
                    pass

                if self.debug:
                    td_dbg = (payload.get("session", {}) or {}).get("turn_detection")
                    print(f"[update_session_autoturn] session.update sent; auto_turn={enabled}, td={td_dbg}")

            except Exception as e:
                if self.debug:
                    print(f"[update_session_autoturn] send error: {e}")

    def set_debug(self, enabled: bool):
        """
        Enable or disable debug logging.

        :param enabled: True to enable debug logging, False to disable.
        """
        self.debug = bool(enabled)

    def is_session_active(self) -> bool:
        """Check if the WS session is currently open."""
        return self.ws is not None and self._running

    def is_session(self) -> bool:
        """Check if the WS session is currently open."""
        return self.ws is not None

    def update_ctx(self, ctx: CtxItem):
        """Update the current CtxItem (for session handle persistence)."""
        self._ctx = ctx