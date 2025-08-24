#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 02:00:00                  #
# ================================================== #

from typing import Dict, Any

from pygpt_net.core.text.utils import has_unclosed_code_tag
from pygpt_net.core.types import (
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_ASSISTANT,
    MODE_CHAT,
)
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import RenderEvent, KernelEvent, AppEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Response:

    AGENT_MODES_ALLOWED = (MODE_AGENT_LLAMA, MODE_AGENT_OPENAI)

    def __init__(self, window=None):
        """
        Response controller

        :param window: Window instance
        """
        super(Response, self).__init__()
        self.window = window

    def handle(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            status: bool
    ):
        """
        Handle Bridge success

        :param status: Result status
        :param context: BridgeContext
        :param extra: Extra data
        """
        core = self.window.core
        controller = self.window.controller
        dispatch = self.window.dispatch
        ctx = context.ctx

        if not status:
            error = extra.get("error", None)
            controller.chat.log("Bridge response: ERROR")
            if error is not None:
                self.window.ui.dialogs.alert(error)
                self.window.update_status(error)
            else:
                self.window.ui.dialogs.alert(trans('status.error'))
                self.window.update_status(trans('status.error'))
        else:
            controller.chat.log_ctx(ctx, "output")  # log
            if controller.kernel.stopped():
                return

        ctx.current = False  # reset current state
        stream = context.stream
        mode = extra.get('mode', MODE_CHAT)
        reply = extra.get('reply', False)
        internal = extra.get('internal', False)
        core.ctx.update_item(ctx)

        # fix frozen chat
        if not status:
            dispatch(RenderEvent(RenderEvent.TOOL_CLEAR, {
                "meta": ctx.meta,
            }))  # hide cmd waiting
            if not controller.kernel.stopped():
                controller.chat.common.unlock_input()  # unlock input
            dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
                "id": "chat",
            }))
            return

        try:
            if mode != MODE_ASSISTANT:
                ctx.from_previous()  # append previous result if exists
                controller.chat.output.handle(
                    ctx,
                    mode,
                    stream,
                    is_response=True,
                    reply=reply,
                    internal=internal,
                    context=context,
                    extra=extra,
                )
        except Exception as e:
            extra["error"] = e
            self.failed(context, extra)

        if stream: 
            if mode not in controller.chat.output.NOT_STREAM_MODES:
                return # handled in stream:handleEnd()

        # post-handle, execute cmd, etc.
        self.post_handle(
            ctx=ctx,
            mode=mode,
            stream=stream,
            reply=reply,
            internal=internal,
        )

    def post_handle(
            self,
            ctx: CtxItem,
            mode: str,
            stream: bool,
            reply: bool,
            internal: bool
    ):
        """
        Post-handle response

        :param ctx: CtxItem
        :param mode: Mode of operation
        :param stream: True if stream mode
        :param reply: True if reply mode
        :param internal: True if internal mode
        """
        output = self.window.controller.chat.output
        output.post_handle(ctx, mode, stream, reply, internal)
        output.handle_end(ctx, mode)  # handle end.

    def begin(
            self,
            context: BridgeContext,
            extra: Dict[str, Any]
    ):
        """
        Handle Bridge begin

        :param context: BridgeContext
        :param extra: Extra data
        """
        msg = extra.get("msg", "")
        self.window.controller.chat.common.lock_input()  # lock input
        if msg:
            self.window.update_status(msg)

    def append(
            self,
            context: BridgeContext,
            extra: Dict[str, Any]
    ):
        """
        Handle Bridge append (agent mode)

        :param context: BridgeContext
        :param extra: Extra data
        """
        core = self.window.core
        controller = self.window.controller
        log = controller.chat.log
        chat_output = controller.chat.output
        dispatch = self.window.dispatch
        global_mode = core.config.get("mode", MODE_AGENT_LLAMA)
        ctx = context.ctx

        # if stopped
        if controller.kernel.stopped():
            output = ctx.output
            if output and has_unclosed_code_tag(output):
                ctx.output += "\n```"
            ctx.msg_id = None
            if ctx.id is None:
                if not ctx.is_empty():
                    core.ctx.add(ctx)  # store context to prevent current output from being lost
                controller.ctx.prepare_name(ctx)  # summarize if not yet
            dispatch(AppEvent(AppEvent.CTX_END))  # finish render
            dispatch(RenderEvent(RenderEvent.RELOAD))  # reload chat window
            return

        prev_ctx = ctx.prev_ctx
        if prev_ctx and prev_ctx.current:
            prev_ctx.current = False  # reset previous context
            core.ctx.update_item(prev_ctx)
            prev_ctx.from_previous()  # append previous result if exists
            controller.chat.output.handle(
                ctx=prev_ctx,
                mode=prev_ctx.mode,
                stream=False,
            )
            controller.chat.output.post_handle(ctx=prev_ctx, mode=prev_ctx.mode, stream=False, reply=False, internal=False)
            controller.chat.output.handle_end(ctx=prev_ctx, mode=prev_ctx.mode)  # end previous context

        stream = context.stream

        # if next in agent cycle
        if ctx.partial:
            dispatch(AppEvent(AppEvent.CTX_END))  # app event

        # handle current step
        ctx.current = False  # reset current state
        mode = ctx.mode
        reply = ctx.reply
        internal = ctx.internal

        core.ctx.set_last_item(ctx)
        dispatch(RenderEvent(RenderEvent.BEGIN, {
            "meta": ctx.meta,
            "ctx": ctx,
            "stream": stream,
        }))

        # append step input to chat window
        dispatch(RenderEvent(RenderEvent.INPUT_APPEND, {
            "meta": ctx.meta,
            "ctx": ctx,
        }))

        # CTX OUTPUT INFO:
        # - ctx.output may be empty here if stream in OpenAI agents
        # - ctx.live_output may be used against output in LlamaIndex agents
        if ctx.id is None:
            core.ctx.add(ctx)

        core.ctx.update_item(ctx)

        # update ctx meta
        if mode in self.AGENT_MODES_ALLOWED and ctx.meta:
            core.ctx.replace(ctx.meta)  # update meta in items
            core.ctx.save(ctx.meta.id)

            # update preset if exists
            preset = controller.presets.get_current()
            if preset is not None:
                if ctx.meta.assistant is not None:
                    preset.assistant_id = ctx.meta.assistant
                    core.presets.update_and_save(preset)

        try:
            chat_output.handle(ctx, mode, stream)
        except Exception as e:
            log(f"Output ERROR: {e}")  # log
            controller.chat.handle_error(e)
            print(f"Error in append text: {e}")

        # post-handle, execute cmd, etc.
        chat_output.post_handle(ctx, mode, stream, reply, internal)
        chat_output.handle_end(ctx, mode)  # handle end.
        dispatch(RenderEvent(RenderEvent.RELOAD))

        # ----------- EVALUATE AGENT RESPONSE -----------

        # if continue reasoning
        if global_mode not in self.AGENT_MODES_ALLOWED:
            return  # no agent mode, nothing to do

        # not agent final response
        if ctx.extra is None or (isinstance(ctx.extra, dict) and "agent_finish" not in ctx.extra):
            self.window.update_status(trans("status.agent.reasoning"))
            controller.chat.common.lock_input()  # lock input, re-enable stop button

        # agent final response
        if ctx.extra is not None and (isinstance(ctx.extra, dict) and "agent_finish" in ctx.extra):
            controller.agent.llama.on_finish(ctx)  # evaluate response and continue if needed

    def end(
            self,
            context: BridgeContext,
            extra: Dict[str, Any]
    ):
        """
        Handle Bridge end

        :param context: BridgeContext
        :param extra: Extra data
        """
        status = extra.get("msg", trans("status.finished"))
        self.window.update_status(status)
        self.window.controller.agent.llama.on_end()
        self.window.controller.chat.common.unlock_input()  # unlock input
        self.window.dispatch(KernelEvent(KernelEvent.STATE_IDLE, {
            "id": "chat",
        }))

    def failed(
            self,
            context: BridgeContext,
            extra: Dict[str, Any]
    ):
        """
        Handle Bridge failed

        :param context: BridgeContext
        :param extra: Extra data
        """
        msg = extra.get("error") if "error" in extra else None
        self.window.controller.chat.log(f"Output ERROR: {msg}")  # log
        self.window.controller.chat.handle_error(msg)
        self.window.controller.chat.common.unlock_input()  # unlock input
        print(f"Error in sending text: {msg}")
        self.window.dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
            "id": "chat",
        }))

    def live_append(
            self,
            context: BridgeContext,
            extra: Dict[str, Any]
    ):
        """
        Handle Bridge live append

        :param context: BridgeContext
        :param extra: Extra data
        """
        self.window.dispatch(RenderEvent(RenderEvent.LIVE_APPEND, {
            "meta": context.ctx.meta,
            "ctx": context.ctx,
            "chunk": extra.get("chunk", ""),
            "begin": extra.get("begin", False),
        }))

    def live_clear(
            self,
            context: BridgeContext,
            extra: Dict[str, Any]
    ):
        """
        Handle Bridge live clear

        :param context: BridgeContext
        :param extra: Extra data
        """
        self.window.dispatch(RenderEvent(RenderEvent.LIVE_CLEAR, {
            "meta": context.ctx.meta,
            "ctx": context.ctx,
        }))