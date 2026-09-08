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

        source_ctx = ctx
        is_continuation = bool(getattr(source_ctx, "turn_parent", None))
        is_agent_continue = bool(
            is_continuation
            and isinstance(getattr(source_ctx, "extra", None), dict)
            and source_ctx.extra.get("agent_continue")
        )
        durable_ctx = source_ctx
        if is_continuation:
            # The stream worker has now consumed the provider generator and
            # populated source_ctx.output/tool_calls. Only now is it safe to fold
            # the ephemeral continuation into the durable user turn.
            durable_ctx = self.window.core.ctx.merge_continuation(source_ctx)
            pid_data["ctx"] = durable_ctx
            bridge_context = pid_data.get("context")
            if bridge_context is not None:
                bridge_context.ctx = durable_ctx

        data = {
            "meta": durable_ctx.meta,
            "ctx": durable_ctx
        }
        event = RenderEvent(RenderEvent.STREAM_END, data)
        self.window.dispatch(event)
        controller.chat.output.handle_after(
            ctx=durable_ctx,
            mode=mode,
            stream=True,
        )

        if is_continuation:
            # Materialize the completed continuation in the durable parent before
            # post_handle(). Autonomous iterations are plain assistant partials,
            # not post-tool hand-offs, so they must not clear a tool status that
            # belongs to an unrelated/previous round.
            self.window.dispatch(RenderEvent(RenderEvent.RELOAD, {"meta": durable_ctx.meta, "ctx": durable_ctx}))
            if not is_agent_continue:
                self.window.dispatch(RenderEvent(RenderEvent.TOOL_CLEAR, {
                    "meta": durable_ctx.meta,
                    "ctx": durable_ctx,
                }))

        if mode == MODE_ASSISTANT:
            controller.assistant.threads.handle_output_message_after_stream(durable_ctx)
        else:
            if pid_data["is_response"]:
                controller.chat.response.post_handle(
                    ctx=durable_ctx,
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
        # Tool feedback is an ephemeral provider call, but its visible prose
        # belongs to the same durable user turn. Once text appears after a tool,
        # materialize the completed tool round and stream the new text into a
        # nested partial of the *parent* msg-box. Never open another live msg-box
        # for the continuation, because that looks like a new CtxItem.
        parent = getattr(ctx, "turn_parent", None)
        if parent is not None:
            renderer = self.instance()
            is_agent_continue = bool(
                isinstance(getattr(ctx, "extra", None), dict)
                and ctx.extra.get("agent_continue")
            )
            if begin and not is_agent_continue:
                # Tool-result continuation: promote the finished tool round into
                # the durable timeline before prose starts streaming.
                previous_part = getattr(ctx, "turn_previous_part", None)
                if previous_part is not None:
                    self.window.core.ctx.mark_part_tasks_ui_ready(previous_part, True)
                    self.window.core.ctx.update_part(parent, previous_part, sync_item=True)
                if hasattr(renderer, "discard_part_streams"):
                    renderer.discard_part_streams(parent.meta)
                self.window.dispatch(RenderEvent(RenderEvent.RELOAD, {"meta": parent.meta, "ctx": parent}))
                self.window.dispatch(RenderEvent(RenderEvent.TOOL_CLEAR, {
                    "meta": parent.meta, "ctx": parent,
                }))

            # Autonomous continuation already owns a freshly persisted empty
            # CtxItemPart. Stream directly into that part under the existing
            # durable message; a tool-style RELOAD on the first token races the
            # live partial and makes the iteration appear non-streaming. Use the
            # part UUID as a stable stream key so batching never changes identity.
            part = getattr(ctx, "turn_part", None)
            part_key = getattr(part, "uuid", None) or f"chat-{getattr(ctx, 'pid', id(ctx))}"
            if hasattr(renderer, "append_part_chunk"):
                renderer.append_part_chunk(
                    parent.meta,
                    parent,
                    part_key,
                    chunk,
                    begin,
                )
            else:
                # Non-Web renderers do not implement nested partial streaming.
                # Fall back to their ordinary stream path instead of dropping
                # autonomous deltas or raising from the GUI slot.
                renderer.append_chunk(
                    parent.meta,
                    parent,
                    chunk,
                    begin,
                )
            return

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
        failed_meta = getattr(pid_data.get("ctx"), "meta", None)
        self.window.dispatch(RenderEvent(RenderEvent.TOOL_CLEAR, {"meta": failed_meta}))
        self.window.dispatch(RenderEvent(RenderEvent.AGENT_STATUS_CLEAR, {"meta": failed_meta, "ctx": pid_data.get("ctx")}))
        if pid_data["is_response"]:
            if not isinstance(pid_data["extra"], dict):
                pid_data["extra"] = {}
            pid_data["extra"]["error"] = error
            pid_data["extra"]["_stream_worker_error"] = True
            failed_ctx = pid_data["ctx"]
            parent = getattr(failed_ctx, "turn_parent", None)
            if parent is not None:
                failed_ctx = parent
                if pid_data.get("context") is not None:
                    pid_data["context"].ctx = parent
            self.window.controller.chat.response.failed(pid_data["context"], pid_data["extra"])
            self.window.controller.chat.response.post_handle(
                ctx=failed_ctx,
                mode=pid_data["mode"],
                stream=True,
                reply=pid_data["reply"],
                internal=pid_data["internal"],
            )

            # response.failed()+post_handle() above is the complete response
            # error lifecycle. Consume the paired end signal by removing this
            # worker now, otherwise handleEnd() would finalize it a second time.
            pid_data["worker"] = None
            self.pids.pop(pid, None)

    def log(self, data: object):
        """
        Log data to the debug console

        :param data: object to log
        """
        self.window.core.debug.info(data)