#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.06 20:00:00                  #
# ================================================== #

import asyncio
from typing import Optional

from PySide6.QtCore import Slot, QRunnable, QObject, Signal

from pygpt_net.core.qt import safe_emit
from pygpt_net.core.events import RealtimeEvent
from pygpt_net.item.ctx import CtxItem

from .options import RealtimeOptions

class RealtimeSignals(QObject):
    """Realtime signals"""
    response = Signal(object)  # RealtimeEvent

class RealtimeWorker(QRunnable):
    """
    QRunnable worker that runs a provider-specific realtime session (websocket).

    - RT_OUTPUT_READY is emitted when the audio output is ready (STREAM_BEGIN).
    - RT_OUTPUT_TEXT_DELTA is emitted for text deltas.
    - RT_OUTPUT_AUDIO_DELTA is emitted for audio chunks to be handled by the main-thread AudioDispatcher.
    - RT_OUTPUT_AUDIO_END is emitted when the session ends.
    - RT_OUTPUT_AUDIO_ERROR is emitted on error.
    """
    def __init__(
            self,
            window,
            ctx: CtxItem,
            opts: RealtimeOptions
    ):
        """
        Initialize the worker.

        :param window: Window instance
        :param ctx: CtxItem
        :param opts: RealtimeOptions
        """
        super().__init__()
        self.window = window
        self.ctx = ctx
        self.opts = opts

    def get_client(self, provider: str):
        """
        Get the appropriate client based on the provider

        :param provider: Provider name
        :return: Client instance
        """
        provider = (provider or "openai").lower()
        if provider == "google":
            return self.window.core.api.google.realtime.handler
        elif provider == "openai":
            return self.window.core.api.openai.realtime.handler
        elif provider == "x_ai":
            return self.window.core.api.xai.realtime.handler
        else:
            raise RuntimeError(f"Unsupported realtime provider: {provider}")

    @Slot()
    def run(self):
        loop = None  # ensure defined for cleanup
        session_was_active = False

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def _amain():
                nonlocal session_was_active
                ready_ctx = None

                def output_ready(event_ctx: Optional[CtxItem] = None):
                    nonlocal ready_ctx
                    target_ctx = event_ctx or self.ctx
                    if target_ctx is None or getattr(target_ctx, "_realtime_interrupted", False):
                        return
                    if ready_ctx is target_ctx:
                        return
                    ready_ctx = target_ctx
                    event = RealtimeEvent(RealtimeEvent.RT_OUTPUT_READY, {"ctx": target_ctx})
                    safe_emit(self.opts.rt_signals, "response", event) if self.opts.rt_signals else None

                # Text deltas -> UI. Providers may pass the CtxItem that owned the
                # response when it started; this prevents late deltas from an
                # interrupted turn being rebound to a newer microphone CtxItem.
                async def on_text(delta: str, event_ctx: Optional[CtxItem] = None):
                    target_ctx = event_ctx or self.ctx
                    if not delta or target_ctx is None or getattr(target_ctx, "_realtime_interrupted", False):
                        return
                    output_ready(target_ctx)
                    event = RealtimeEvent(RealtimeEvent.RT_OUTPUT_TEXT_DELTA, {
                        "ctx": target_ctx,
                        "chunk": delta,
                    })
                    safe_emit(self.opts.rt_signals, "response", event) if self.opts.rt_signals else None

                # Audio -> enqueue to main-thread. Keep the same response owner
                # isolation as text so stale playback cannot revive after barge-in.
                async def on_audio(
                        data: bytes,
                        mime: str,
                        rate: Optional[int],
                        channels: Optional[int],
                        final: bool = False,
                        event_ctx: Optional[CtxItem] = None,
                ):
                    target_ctx = event_ctx or self.ctx
                    if target_ctx is None or getattr(target_ctx, "_realtime_interrupted", False):
                        return
                    if data:
                        output_ready(target_ctx)
                    event = RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_DELTA, {
                        "payload":  {
                            "ctx": target_ctx,
                            "data": data or b"",
                            "mime": mime or "audio/pcm",
                            "rate": int(rate) if rate is not None else None,
                            "channels": int(channels) if channels is not None else None,
                            "final": bool(final),
                            "provider": self.opts.provider,
                            "model": self.opts.model,
                        }
                    })
                    safe_emit(self.opts.rt_signals, "response", event) if self.opts.rt_signals else None

                def _should_stop() -> bool:
                    try:
                        return bool(self.window.controller.kernel.stopped())
                    except Exception:
                        return False

                # run the client
                client = self.get_client(self.opts.provider)
                try:
                    session_was_active = bool(client.is_session_active())
                except Exception:
                    session_was_active = False
                # Buffered microphone input is already submitted by the user;
                # unlike VAD session setup it can open the response stream now.
                if getattr(self.opts, "audio_data", None):
                    output_ready()
                await client.run(self.ctx, self.opts, on_text, on_audio, _should_stop)

            loop.run_until_complete(_amain())
            # print("[rt] STREAM_END")

        except Exception as e:
            try:
                # Distinguish session/bootstrap failures from errors in an already
                # established live conversation. The main-thread controller uses
                # this metadata for a useful error dialog and cleanup policy.
                phase = "turn" if session_was_active else "session_start"
                event = RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_ERROR, {
                    "ctx": self.ctx,
                    "error": e,
                    "provider": getattr(self.opts, "provider", None),
                    "phase": phase,
                })
                safe_emit(self.opts.rt_signals, "response", event) if self.opts.rt_signals else None
            finally:
                pass
        finally:
            # Robust asyncio teardown to avoid hangs on subsequent runs
            if loop is not None:
                try:
                    pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                    for t in pending:
                        t.cancel()
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception:
                    pass
                try:
                    loop.close()
                except Exception:
                    pass
                try:
                    asyncio.set_event_loop(None)
                except Exception:
                    pass
