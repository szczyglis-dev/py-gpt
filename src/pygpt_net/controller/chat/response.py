#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 03:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, QObject

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Response(QObject):
    def __init__(self, window=None):
        """
        Response controller

        :param window: Window instance
        """
        super(Response, self).__init__()
        self.window = window

    @Slot(bool, object, dict)
    def handle_success(self, status: bool, bridge_context: BridgeContext, extra: dict):
        """
        Handle Bridge success

        :param status: Result status
        :param bridge_context: BridgeContext
        :param extra: Extra data
        """
        ctx = bridge_context.ctx
        if not status:
            error = None
            if "error" in extra:
                error = extra.get("error")
            self.window.controller.chat.log("Bridge response: ERROR")
            if error is not None:
                self.window.ui.dialogs.alert(error)
                self.window.ui.status(error)
            else:
                self.window.ui.dialogs.alert(trans('status.error'))
                self.window.ui.status(trans('status.error'))
        else:
            self.window.controller.chat.log_ctx(ctx, "output")  # log
            if self.window.controller.chat.common.stopped():
                return

        ctx.current = False  # reset current state
        stream = bridge_context.stream
        mode = extra.get('mode', 'chat')
        reply = extra.get('reply', False)
        internal = extra.get('internal', False)
        has_attachments = extra.get('has_attachments', False)
        self.window.core.ctx.update_item(ctx)

        # fix frozen chat
        if not status:
            self.window.controller.chat.render.tool_output_clear(ctx.meta)  # hide cmd waiting
            if not self.window.controller.chat.common.stopped():
                self.window.controller.chat.common.unlock_input()  # unlock input
            return

        try:
            if mode != "assistant":
                ctx.from_previous()  # append previous result if exists
                self.window.controller.chat.output.handle(
                    ctx,
                    mode,
                    stream,
                )
        except Exception as e:
            self.handle_failed(e)

        # post-handle, execute cmd, etc.
        self.window.controller.chat.output.post_handle(ctx, mode, stream, reply, internal)
        self.window.controller.chat.output.handle_end(ctx, mode, has_attachments)  # handle end.

    @Slot(object)
    def handle_failed(self, err: any):
        """
        Handle Bridge failed

        :param err: Exception
        """
        self.window.controller.chat.log("Output ERROR: {}".format(err))  # log
        self.window.controller.chat.handle_error(err)
        self.window.controller.chat.common.unlock_input()  # unlock input
        print("Error in sending text: " + str(err))

    @Slot(object)
    def handle_end(self, ctx: CtxItem, msg: str = ""):
        """
        Handle Bridge end

        :param ctx: CtxItem
        :param msg: Message
        """
        status = trans("status.finished")
        if msg:
            status = msg
        self.window.ui.status(status)
        self.window.controller.agent.llama.flow_end()
        self.window.controller.chat.common.unlock_input()  # unlock input

    @Slot(object)
    def handle_begin(self, ctx: CtxItem, msg: str = ""):
        """
        Handle Bridge begin

        :param ctx: CtxItem
        :param msg: Message
        """
        self.window.controller.chat.common.lock_input()  # lock input
        if msg:
            self.window.ui.status(msg)

    @Slot(str)
    def handle_evaluate(self, msg: str):
        """
        Handle Bridge evaluate

        :param msg: Message
        """
        self.window.ui.status(msg)

    @Slot(object)
    def handle_append(self, ctx: CtxItem):
        """
        Handle Bridge append (agent mode)

        :param ctx: CtxItem
        """
        if self.window.controller.chat.common.stopped():
            return

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
                                                          mode=prev_ctx.mode,
                                                          has_attachments=False)  # end previous context

        # handle current step
        ctx.current = False  # reset current state
        mode = ctx.mode
        reply = ctx.reply
        internal = ctx.internal
        has_attachments = False
        self.window.core.ctx.set_last_item(ctx)
        self.window.controller.chat.render.begin(ctx.meta, ctx, stream=stream)

        # append step input to chat window
        self.window.controller.chat.render.append_input(ctx.meta, ctx)
        self.window.core.ctx.add(ctx)
        self.window.controller.ctx.update(
            reload=True,
            all=False,
        )
        self.window.core.ctx.update_item(ctx)

        # update ctx meta
        if mode == "agent_llama" and ctx.meta is not None:
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
        self.window.controller.chat.render.tool_output_begin(ctx.meta)  # show cmd waiting
        self.window.controller.chat.output.handle_end(ctx, mode, has_attachments)  # handle end.
        self.window.controller.chat.render.reload()

        # if continue reasoning
        if ctx.extra is None or (type(ctx.extra) == dict and "agent_finish" not in ctx.extra):
            self.window.ui.status(trans("status.agent.reasoning"))
            self.window.controller.chat.common.lock_input()  # lock input, re-enable stop button

        if ctx.extra is not None and (type(ctx.extra) == dict and "agent_finish" in ctx.extra):
            self.window.controller.agent.llama.on_finish(ctx)  # evaluate response and continue if needed
