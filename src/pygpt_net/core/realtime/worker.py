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

        # STREAM_BEGIN -> UI
        try:
            event = RealtimeEvent(RealtimeEvent.RT_OUTPUT_READY, {
                "ctx": self.ctx,
            })
            self.opts.rt_signals.response.emit(event) if self.opts.rt_signals else None
        except Exception:
            pass

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def _amain():
                # Text deltas -> UI
                async def on_text(delta: str):
                    if not delta:
                        return
                    event = RealtimeEvent(RealtimeEvent.RT_OUTPUT_TEXT_DELTA, {
                        "ctx": self.ctx,
                        "chunk": delta,
                    })
                    self.opts.rt_signals.response.emit(event) if self.opts.rt_signals else None

                # Audio -> enqueue to main-thread
                async def on_audio(
                        data: bytes,
                        mime: str,
                        rate: Optional[int],
                        channels: Optional[int],
                        final: bool = False
                ):
                    event = RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_DELTA, {
                        "payload":  {
                            "ctx": self.ctx,
                            "data": data or b"",
                            "mime": mime or "audio/pcm",
                            "rate": int(rate) if rate is not None else None,
                            "channels": int(channels) if channels is not None else None,
                            "final": bool(final),
                            "provider": self.opts.provider,
                            "model": self.opts.model,
                        }
                    })
                    self.opts.rt_signals.response.emit(event) if self.opts.rt_signals else None

                def _should_stop() -> bool:
                    try:
                        return bool(self.window.controller.kernel.stopped())
                    except Exception:
                        return False

                # run the client
                client = self.get_client(self.opts.provider)
                await client.run(self.ctx, self.opts, on_text, on_audio, _should_stop)

            loop.run_until_complete(_amain())
            # print("[rt] STREAM_END")

        except Exception as e:
            try:
                event = RealtimeEvent(RealtimeEvent.RT_OUTPUT_AUDIO_ERROR, {"error": e})
                self.opts.rt_signals.response.emit(event) if self.opts.rt_signals else None
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