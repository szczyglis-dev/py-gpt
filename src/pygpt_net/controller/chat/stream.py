#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.28 20:00:00                  #
# ================================================== #

from typing import Optional

from PySide6.QtCore import Slot

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.events import RenderEvent
from pygpt_net.core.types import MODE_ASSISTANT
from pygpt_net.item.ctx import CtxItem

from .handler.stream_worker import StreamWorker

class Stream:
    def __init__(self, window=None):
        """
        Stream controller

        :param window: Window instance
        """
        self.window = window
        self.ctx = None
        self.mode = None
        self.thread = None
        self.worker = None
        self.is_response = False
        self.reply = False
        self.internal = False
        self.context = None
        self.extra = {}

    def append(
            self,
            ctx: CtxItem,
            mode: str = None,
            is_response: bool = False,
            reply: str = False,
            internal: bool = False,
            context: Optional[BridgeContext] = None,
            extra: Optional[dict] = None
    ):
        """
        Asynchronous append of stream worker to the thread.

        :param ctx: Context item
        :param mode: Mode of operation (e.g., MODE_ASSISTANT)
        :param is_response: Whether this is a response stream
        :param reply: Reply identifier
        :param internal: Whether this is an internal stream
        :param context: Optional BridgeContext for additional context
        :param extra: Additional data to pass to the stream
        """
        self.ctx = ctx
        self.mode = mode
        self.is_response = is_response
        self.reply = reply
        self.internal = internal
        self.context = context
        self.extra = extra if extra is not None else {}

        worker = StreamWorker(ctx, self.window)
        worker.stream = ctx.stream
        worker.signals.eventReady.connect(self.handleEvent)
        worker.signals.errorOccurred.connect(self.handleError)
        worker.signals.end.connect(self.handleEnd)
        ctx.stream = None
        self.worker = worker

        self.window.core.debug.info("[chat] Stream begin...")
        self.window.threadpool.start(worker)

    @Slot(object)
    def handleEnd(self, ctx: CtxItem):
        """
        Slot for handling end of stream

        :param ctx: Context item
        """
        self.window.controller.ui.update_tokens()

        data = {"meta": self.ctx.meta, "ctx": self.ctx}
        event = RenderEvent(RenderEvent.STREAM_END, data)
        self.window.dispatch(event)
        self.window.controller.chat.output.handle_after(
            ctx=ctx,
            mode=self.mode,
            stream=True,
        )

        if self.mode == MODE_ASSISTANT:
            self.window.controller.assistant.threads.handle_output_message_after_stream(ctx)
        else:
            if self.is_response:
                self.window.controller.chat.response.post_handle(
                    ctx=ctx,
                    mode=self.mode,
                    stream=True,
                    reply=self.reply,
                    internal=self.internal
                )

        self.worker = None

    def handleEvent(self, event):
        """
        Slot for handling stream events

        :param event: RenderEvent
        """
        self.window.dispatch(event)

    def handleError(self, error):
        """
        Slot for handling stream errors

        :param error: Exception or error message
        """
        self.window.core.debug.log(error)
        if self.is_response:
            if not isinstance(self.extra, dict):
                self.extra = {}
            self.extra["error"] = error
            self.window.controller.chat.response.failed(self.context, self.extra)
            self.window.controller.chat.response.post_handle(
                ctx=self.ctx,
                mode=self.mode,
                stream=True,
                reply=self.reply,
                internal=self.internal,
            )

    def log(self, data: object):
        """
        Log data to the debug console

        :param data: object to log
        """
        self.window.core.debug.info(data)