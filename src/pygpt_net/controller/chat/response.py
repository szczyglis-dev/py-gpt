#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

from typing import Dict, Any

from pygpt_net.core.types import (
    MODE_AGENT_LLAMA,
    MODE_ASSISTANT,
    MODE_CHAT,
)
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import RenderEvent, KernelEvent
from pygpt_net.utils import trans


class Response:
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
        ctx = context.ctx
        if not status:
            error = None
            if "error" in extra:
                error = extra.get("error")
            self.window.controller.chat.log("Bridge response: ERROR")
            if error is not None:
                self.window.ui.dialogs.alert(error)
                self.window.update_status(error)
            else:
                self.window.ui.dialogs.alert(trans('status.error'))
                self.window.update_status(trans('status.error'))
        else:
            self.window.controller.chat.log_ctx(ctx, "output")  # log
            if self.window.controller.kernel.stopped():
                return

        ctx.current = False  # reset current state
        stream = context.stream
        mode = extra.get('mode', MODE_CHAT)
        reply = extra.get('reply', False)
        internal = extra.get('internal', False)
        self.window.core.ctx.update_item(ctx)

        # fix frozen chat
        if not status:
            data = {
                "meta": ctx.meta,
            }
            event = RenderEvent(RenderEvent.TOOL_CLEAR, data)
            self.window.dispatch(event)  # hide cmd waiting
            if not self.window.controller.kernel.stopped():
                self.window.controller.chat.common.unlock_input()  # unlock input
            # set state to: error
            self.window.dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
                "id": "chat",
            }))
            return

        try:
            if mode != MODE_ASSISTANT:
                ctx.from_previous()  # append previous result if exists
                self.window.controller.chat.output.handle(
                    ctx,
                    mode,
                    stream,
                )
        except Exception as e:
            extra["error"] = e
            self.failed(context, extra)

        # post-handle, execute cmd, etc.
        self.window.controller.chat.output.post_handle(ctx, mode, stream, reply, internal)
        self.window.controller.chat.output.handle_end(ctx, mode)  # handle end.

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
        if self.window.controller.kernel.stopped():
            return

        ctx = context.ctx
        # at first, handle previous context (user input) if not handled yet
        prev_ctx = ctx.prev_ctx
        stream = False
        if prev_ctx.current:
            prev_ctx.current = False  # reset previous context
            self.window.core.ctx.update_item(prev_ctx)
            prev_ctx.from_previous()  # append previous result if exists
            self.window.controller.chat.output.handle(
                ctx=prev_ctx,
                mode=prev_ctx.mode,
                stream_mode=False,
            )
            self.window.controller.chat.output.post_handle(ctx=prev_ctx,
                                                           mode=prev_ctx.mode,
                                                           stream=False,
                                                           reply=False,
                                                           internal=False)

            self.window.controller.chat.output.handle_end(ctx=prev_ctx,
                                                          mode=prev_ctx.mode)  # end previous context

        # handle current step
        ctx.current = False  # reset current state
        mode = ctx.mode
        reply = ctx.reply
        internal = ctx.internal

        self.window.core.ctx.set_last_item(ctx)
        data = {
            "meta": ctx.meta,
            "ctx": ctx,
            "stream": stream,
        }
        event = RenderEvent(RenderEvent.BEGIN, data)
        self.window.dispatch(event)

        # append step input to chat window
        data = {
            "meta": ctx.meta,
            "ctx": ctx,
        }
        event = RenderEvent(RenderEvent.INPUT_APPEND, data)
        self.window.dispatch(event)
        self.window.core.ctx.add(ctx)
        self.window.controller.ctx.update(
            reload=True,
            all=False,
        )
        self.window.core.ctx.update_item(ctx)

        # update ctx meta
        if mode == MODE_AGENT_LLAMA and ctx.meta is not None:
            self.window.core.ctx.replace(ctx.meta)
            self.window.core.ctx.save(ctx.meta.id)
            # update preset if exists
            preset = self.window.controller.presets.get_current()
            if preset is not None:
                if ctx.meta.assistant is not None:
                    preset.assistant_id = ctx.meta.assistant
                    self.window.core.presets.update_and_save(preset)

        try:
            self.window.controller.chat.output.handle(ctx, mode, stream)
        except Exception as e:
            self.window.controller.chat.log("Output ERROR: {}".format(e))  # log
            self.window.controller.chat.handle_error(e)
            print("Error in append text: " + str(e))

        # post-handle, execute cmd, etc.
        self.window.controller.chat.output.post_handle(ctx, mode, stream, reply, internal)

        data = {
            "meta": ctx.meta,
        }
        event = RenderEvent(RenderEvent.TOOL_BEGIN, data)
        self.window.dispatch(event)  # show cmd waiting
        self.window.controller.chat.output.handle_end(ctx, mode)  # handle end.

        event = RenderEvent(RenderEvent.RELOAD)
        self.window.dispatch(event)

        # if continue reasoning
        if ctx.extra is None or (type(ctx.extra) == dict and "agent_finish" not in ctx.extra):
            self.window.update_status(trans("status.agent.reasoning"))
            self.window.controller.chat.common.lock_input()  # lock input, re-enable stop button

        if ctx.extra is not None and (type(ctx.extra) == dict and "agent_finish" in ctx.extra):
            self.window.controller.agent.llama.on_finish(ctx)  # evaluate response and continue if needed

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
        msg = extra.get("msg", "")
        status = trans("status.finished")
        if msg:
            status = msg
        self.window.update_status(status)
        self.window.controller.agent.llama.on_end()
        self.window.controller.chat.common.unlock_input()  # unlock input
        # set state to: idle
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
        err = extra.get("error") if "error" in extra else None
        self.window.controller.chat.log("Output ERROR: {}".format(err))  # log
        self.window.controller.chat.handle_error(err)
        self.window.controller.chat.common.unlock_input()  # unlock input
        print("Error in sending text: " + str(err))
        # set state to: error
        self.window.dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
            "id": "chat",
        }))

    def update_status(
            self,
            context: BridgeContext,
            extra: Dict[str, Any]
    ):
        """
        Handle Bridge evaluate

        :param context: BridgeContext
        :param extra: Extra data
        """
        msg = extra.get("msg", "")
        self.window.update_status(msg)