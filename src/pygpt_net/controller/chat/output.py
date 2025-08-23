#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.23 15:00:00                  #
# ================================================== #

from typing import Any, Optional

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import (
    MODE_ASSISTANT,
    MODE_IMAGE,
)
from pygpt_net.core.events import Event, AppEvent, RenderEvent, KernelEvent
from pygpt_net.item.ctx import CtxItem


class Output:

    STATE_PARAMS = {
        "id": "chat",
    }

    NOT_STREAM_MODES = (
        MODE_ASSISTANT,
        MODE_IMAGE
    )

    def __init__(self, window=None):
        """
        Output controller

        :param window: Window instance
        """
        self.window = window

    def handle(
            self,
            ctx: CtxItem,
            mode: str,
            stream: bool = False,
            is_response: bool = False,
            reply: bool = False,
            internal: bool = False,
            context: Optional[BridgeContext] = None,
            extra: Optional[dict] = None
    ):
        """
        Handle response from LLM

        :param ctx: CtxItem
        :param mode: mode (global)
        :param stream: stream enabled (local)
        :param is_response: Is response output
        :param reply: is reply
        :param internal: is internal command
        :param context: BridgeContext (optional)
        :param extra: Extra data (optional)
        """
        self.window.dispatch(KernelEvent(KernelEvent.STATE_BUSY))  # state: busy

        # if stream then append chunk by chunk
        end = True
        if stream:  # local, not global config
            if mode not in self.NOT_STREAM_MODES:
                end = False  # don't end if stream mode, append chunk by chunk
                self.window.controller.chat.stream.append(
                    ctx=ctx,
                    mode=mode,
                    is_response=is_response,
                    reply=reply,
                    internal=internal,
                    context=context,
                    extra=extra,
                )

        if end:
            self.handle_after(
                ctx=ctx,
                mode=mode,
                stream=stream,
            )

    def handle_after(
            self,
            ctx: CtxItem,
            mode: str,
            stream: bool = False
    ):
        """
        Handle response from LLM

        :param ctx: CtxItem
        :param mode: mode (global)
        :param stream: stream enabled (local)
        """
        core = self.window.core
        dispatch = self.window.dispatch
        log = self.window.controller.chat.log

        # check if tool calls detected
        if ctx.tool_calls:
            # if not internal commands in a text body then append tool calls as commands (prevent double commands)
            if not core.command.has_cmds(ctx.output):
                core.command.append_tool_calls(ctx)  # append tool calls as commands
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra["tool_calls"] = ctx.tool_calls
                stream = False  # disable stream mode, show tool calls at the end
                log("Tool call received...")
            else:  # prevent execute twice
                log("Ignoring tool call because command received...")

        # event: context after
        dispatch(Event(Event.CTX_AFTER, {
            'mode': mode,
        }, ctx=ctx))

        log("Appending output to chat window...")

        # only append output if not in stream mode, TODO: plugin output add
        stream_global = core.config.get('stream', False)
        if not stream:
            if stream_global:  # use global stream settings here to persist previously added input
                dispatch(RenderEvent(RenderEvent.INPUT_APPEND, {
                    "meta": ctx.meta,
                    "ctx": ctx,
                    "flush": True,
                    "append": True,
                }))

            dispatch(RenderEvent(RenderEvent.OUTPUT_APPEND, {
                "meta": ctx.meta,
                "ctx": ctx,
            }))
            dispatch(RenderEvent(RenderEvent.EXTRA_APPEND, {
                "meta": ctx.meta,
                "ctx": ctx,
                "footer": True,
            }))  # + icons

        self.handle_complete(ctx)

    def handle_complete(self, ctx: CtxItem):
        """
        Handle completed context

        :param ctx: CtxItem
        """
        core = self.window.core
        controller = self.window.controller
        dispatch = self.window.dispatch
        mode = core.config.get('mode')

        # post update context, store last mode, etc.
        core.ctx.post_update(mode)
        core.ctx.store()

        controller.ctx.update_ctx()
        controller.ctx.store_history(ctx, "output")  # store to history

        controller.chat.audio.handle_output(ctx)  # handle audio output
        controller.chat.common.auto_unlock(ctx)  # unlock input if allowed
        controller.chat.common.show_response_tokens(ctx)  # update tokens
        dispatch(KernelEvent(KernelEvent.STATE_IDLE, self.STATE_PARAMS))  # state: idle

    def post_handle(
            self,
            ctx: CtxItem,
            mode: str,
            stream: bool = False,
            reply: bool = False,
            internal: bool = False
    ):
        """
        Post handle results

        :param ctx: CtxItem
        :param mode: mode (global)
        :param stream: stream mode
        :param reply: is reply
        :param internal: is internal
        """
        core = self.window.core
        controller = self.window.controller
        dispatch = self.window.dispatch

        # if commands enabled: post-execute commands (not assistant mode)
        if mode != MODE_ASSISTANT:
            ctx.clear_reply()  # reset results
            expert_calls = controller.agent.experts.handle(ctx)
            if expert_calls == 0:  # handle commands only if no expert calls in queue
                controller.chat.command.handle(ctx)

            ctx.from_previous()  # append previous result again before save
            core.ctx.update_item(ctx)  # update ctx in DB

        # render: end
        if ctx.sub_calls == 0:  # if no experts called
            dispatch(RenderEvent(RenderEvent.END, {
                "meta": ctx.meta,
                "ctx": ctx,
                "stream": stream,
            }))

        controller.chat.common.auto_unlock(ctx)  # unlock input if allowed
        controller.ctx.prepare_summary(ctx)  # prepare ctx name

        if self.window.state != self.window.STATE_ERROR and mode != MODE_ASSISTANT:
            dispatch(KernelEvent(KernelEvent.STATE_IDLE, self.STATE_PARAMS))  # state: idle

    def handle_end(
            self,
            ctx: CtxItem,
            mode: str
    ):
        """
        Handle context end (finish output)

        :param ctx: CtxItem
        :param mode: mode
        """
        controller = self.window.controller
        dispatch = self.window.dispatch
        log = controller.chat.log

        controller.attachment.cleanup(ctx)  # clear after send
        log(f"Context: END: {ctx}" if self.window.core.config.get("log.ctx") else "Context: END.")

        # event: context end
        dispatch(Event(Event.CTX_END, {
            'mode': mode,
        }, ctx=ctx))
        controller.chat.input.generating = False  # unlock

        log("End.")
        dispatch(AppEvent(AppEvent.CTX_END))  # app event

        # restore state to idle if no errors
        if self.window.state != self.window.STATE_ERROR:
            dispatch(KernelEvent(KernelEvent.STATE_IDLE, self.STATE_PARAMS))

        if mode != MODE_ASSISTANT:
            controller.kernel.stack.handle()  # handle reply
            dispatch(RenderEvent(RenderEvent.RELOAD))  # reload chat window