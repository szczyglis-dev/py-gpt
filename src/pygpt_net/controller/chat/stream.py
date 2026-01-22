#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.22 04:00:00                  #
# ================================================== #

from typing import Optional, Any

from PySide6.QtCore import Slot, QObject

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.events import RenderEvent
from pygpt_net.core.types import MODE_ASSISTANT
from pygpt_net.item.ctx import CtxItem

from .stream_worker import StreamWorker

class Stream(QObject):
    def __init__(self, window=None):
        """
        Stream controller

        :param window: Window instance
        """
        super().__init__()
        self.window = window
        self.instance = None  # cached get renderer instance method
        self.pids = {} # {pid -> {data}}, workers are tracked per PID

    def get_pid_by_ctx(self, ctx: CtxItem) -> Optional[int]:
        """
        Get process ID by context item

        :param ctx: Context item
        :return: Process ID or None
        """
        if ctx and ctx.meta:
            return self.window.core.ctx.output.get_pid(ctx.meta)
        return None

    def get_pid_ids(self) -> list[int]:
        """
        Get all active process IDs

        :return: List of process IDs
        """
        return list(self.pids.keys())

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
        pid = self.get_pid_by_ctx(ctx)
        if pid is None:
            return  # abort streaming if no PID found
        if pid not in self.pids:
            self.pids[pid] = {}

        pid_data = self.pids[pid]
        pid_data["ctx"] = ctx
        pid_data["mode"] = mode
        pid_data["is_response"] = is_response
        pid_data["reply"] = reply
        pid_data["internal"] = internal
        pid_data["context"] = context
        pid_data["extra"] = extra if extra is not None else {}

        # cache the get renderer instance method
        if self.instance is None:
            self.instance = self.window.controller.chat.render.instance # callable

        worker = StreamWorker(ctx, self.window)
        worker.stream = ctx.stream
        worker.signals.eventReady.connect(self.handleEvent)
        worker.signals.errorOccurred.connect(self.handleError)
        worker.signals.end.connect(self.handleEnd)
        worker.signals.chunk.connect(self.handleChunk)
        ctx.stream = None # clear reference to generator

        pid_data["worker"] = worker # keep reference to avoid GC, per PID
        self.window.core.debug.info(f"[chat] Stream begin... PID={pid}")
        self.window.threadpool.start(worker)

    @Slot(object)
    def handleEnd(self, ctx: CtxItem):
        """
        Slot for handling end of stream

        :param ctx: Context item
        """
        pid = self.get_pid_by_ctx(ctx)
        if pid is None or pid not in self.pids:
            return  # abort if no PID found or not tracked
        pid_data = self.pids[pid]

        controller = self.window.controller
        controller.ui.update_tokens()
        mode = pid_data["mode"]

        data = {
            "meta": pid_data["ctx"].meta,
            "ctx": pid_data["ctx"]
        }
        event = RenderEvent(RenderEvent.STREAM_END, data)
        self.window.dispatch(event)
        controller.chat.output.handle_after(
            ctx=ctx,
            mode=mode,
            stream=True,
        )

        if mode == MODE_ASSISTANT:
            controller.assistant.threads.handle_output_message_after_stream(ctx)
        else:
            if pid_data["is_response"]:
                controller.chat.response.post_handle(
                    ctx=ctx,
                    mode=mode,
                    stream=True,
                    reply=pid_data["reply"],
                    internal=pid_data["internal"],
                )

        pid_data["worker"] = None  # release worker reference
        del self.pids[pid]  # remove PID tracking

    @Slot(object, str, bool)
    def handleChunk(
            self,
            ctx: CtxItem,
            chunk: str,
            begin: bool = False
    ):
        """
        Handle a chunk of data in the stream

        :param ctx: Context item
        :param chunk: Chunk of data
        :param begin: Whether this is the beginning of the stream
        """
        # direct call to the renderer to avoid overhead of event queue
        self.instance().append_chunk(
            ctx.meta,
            ctx,
            chunk,
            begin,
        )
        chunk = None  # free reference

    @Slot(object)
    def handleEvent(self, event):
        """
        Slot for handling stream events

        :param event: RenderEvent
        """
        self.window.dispatch(event)

    @Slot(object, object)
    def handleError(self, ctx: CtxItem, error: Any):
        """
        Slot for handling stream errors

        :param ctx: Context item
        :param error: Exception or error message
        """
        pid = self.get_pid_by_ctx(ctx)
        if pid is None or pid not in self.pids:
            return  # abort if no PID found or not tracked
        pid_data = self.pids[pid]

        self.window.core.debug.log(error)
        if pid_data["is_response"]:
            if not isinstance(pid_data["extra"], dict):
                pid_data["extra"] = {}
            pid_data["extra"]["error"] = error
            self.window.controller.chat.response.failed(pid_data["context"], pid_data["extra"])
            self.window.controller.chat.response.post_handle(
                ctx=pid_data["ctx"],
                mode=pid_data["mode"],
                stream=True,
                reply=pid_data["reply"],
                internal=pid_data["internal"],
            )
        # TODO: remove PID from tracking on error?

    def log(self, data: object):
        """
        Log data to the debug console

        :param data: object to log
        """
        self.window.core.debug.info(data)