#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 00:00:00                  #
# ================================================== #

from typing import Any

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_ASSISTANT,
    MODE_IMAGE,
)
from pygpt_net.core.events import Event, AppEvent, RenderEvent, KernelEvent
from pygpt_net.item.ctx import CtxItem


class Output:
    def __init__(self, window=None):
        """
        Output controller

        :param window: Window instance
        """
        self.window = window
        self.not_stream_modes = [
            MODE_ASSISTANT,
            MODE_IMAGE,
        ]

    def handle(
            self,
            ctx: CtxItem,
            mode: str,
            stream_mode: bool = False
    ):
        """
        Handle response from LLM

        :param ctx: CtxItem
        :param mode: mode (global)
        :param stream_mode: stream mode
        """
        self.window.stateChanged.emit(self.window.STATE_BUSY)

        # if stream mode then append chunk by chunk
        stream_enabled = self.window.core.config.get("stream")  # global stream enabled
        if stream_mode:  # local stream enabled
            if mode not in self.not_stream_modes:
                self.window.controller.chat.stream.append(ctx)

        # check if tool calls detected
        if ctx.tool_calls:
            # if not internal commands in a text body then append tool calls as commands (prevent double commands)
            if not self.window.core.command.has_cmds(ctx.output):
                self.window.core.command.append_tool_calls(ctx)  # append tool calls as commands
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra["tool_calls"] = ctx.tool_calls
                stream_mode = False  # disable stream mode, show tool calls at the end
                self.log("Tool call received...")
            else:  # prevent execute twice
                self.log("Ignoring tool call because command received...")

        # agent mode
        if mode == MODE_AGENT:
            self.window.controller.agent.legacy.on_ctx_after(ctx)

        # event: context after
        event = Event(Event.CTX_AFTER)
        event.ctx = ctx
        self.window.dispatch(event)

        self.log("Appending output to chat window...")

        # only append output if not in stream mode, TODO: plugin output add
        if not stream_mode:
            if stream_enabled:  # use global stream settings here to persist previously added input
                data = {
                    "meta": ctx.meta,
                    "ctx": ctx,
                    "flush": True,
                    "append": True,
                }
                event = RenderEvent(RenderEvent.INPUT_APPEND, data)
                self.window.dispatch(event)

            data = {
                "meta": ctx.meta,
                "ctx": ctx,
            }
            event = RenderEvent(RenderEvent.OUTPUT_APPEND, data)
            self.window.dispatch(event)

            data = {
                "meta": ctx.meta,
                "ctx": ctx,
                "footer": True,
            }
            event = RenderEvent(RenderEvent.EXTRA_APPEND, data)
            self.window.dispatch(event)  # + icons

        self.handle_complete(ctx)

    def handle_complete(self, ctx: CtxItem):
        """
        Handle completed context

        :param ctx: CtxItem
        """
        mode = self.window.core.config.get('mode')
        self.window.core.ctx.post_update(mode)  # post update context, store last mode, etc.
        self.window.core.ctx.store()
        self.window.controller.ctx.update_ctx()  # update current ctx info

        # update response tokens
        self.window.controller.chat.common.show_response_tokens(ctx)

        # handle audio output
        self.window.controller.chat.audio.handle_output(ctx)

        # store to history
        if self.window.core.config.get('store_history'):
            self.window.core.history.append(ctx, "output")

        if self.window.controller.chat.common.can_unlock(ctx):
            if not self.window.controller.kernel.stopped():
                self.window.controller.chat.common.unlock_input()  # unlock input

        # reset state to: idle
        self.window.dispatch(KernelEvent(KernelEvent.STATE_IDLE, {
            "id": "chat",
        }))

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
        # if commands enabled: post-execute commands (not assistant mode)
        if mode != MODE_ASSISTANT:
            ctx.clear_reply()  # reset results

            # extract expert mentions and handle experts reply
            num_calls = self.window.controller.agent.experts.handle(ctx)
            if num_calls == 0:
                # handle commands only if no expert calls in queue
                self.window.controller.chat.command.handle(ctx)

            ctx.from_previous()  # append previous result again before save
            self.window.core.ctx.update_item(ctx)  # update ctx in DB

        # render: end
        if ctx.sub_calls == 0:  # if no experts called
            data = {
                "meta": ctx.meta,
                "ctx": ctx,
                "stream": stream,
            }
            event = RenderEvent(RenderEvent.END, data)
            self.window.dispatch(event)

        # don't unlock input and leave stop btn if assistant mode or if agent/autonomous is enabled
        # send btn will be unlocked in agent mode on stop
        if self.window.controller.chat.common.can_unlock(ctx):
            if not self.window.controller.kernel.stopped():
                self.window.controller.chat.common.unlock_input()  # unlock input

        # handle ctx name (generate title from summary if not initialized)
        if not reply and not internal:  # don't call if reply or internal mode
            if self.window.core.config.get('ctx.auto_summary'):
                self.log("Calling for prepare context name...")
                self.window.controller.ctx.prepare_name(ctx)  # async

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
        # clear attachments after send, only if attachments has been provided before send
        auto_clear = self.window.core.config.get('attachments_send_clear')
        if self.window.controller.attachment.clear_allowed(ctx):
            if auto_clear and not self.window.controller.attachment.is_locked():
                self.window.controller.attachment.clear(force=True, auto=True)
                self.window.controller.attachment.update()
                self.log("Attachments cleared.")  # log

        if self.window.core.config.get("log.ctx"):
            self.log("Context: END: {}".format(ctx))
        else:
            self.log("Context: END.")

        # agent mode
        if mode == MODE_AGENT:
            agent_iterations = int(self.window.core.config.get("agent.iterations"))
            self.log("Agent: ctx end, iterations: {}".format(agent_iterations))
            self.window.controller.agent.legacy.on_ctx_end(
                ctx,
                iterations=agent_iterations,
            )

        # event: context end
        event = Event(Event.CTX_END)
        event.ctx = ctx
        self.window.dispatch(event)
        self.window.controller.ui.update_tokens()  # update UI
        self.window.controller.chat.input.generating = False  # unlock

        if (mode not in self.window.controller.chat.input.no_ctx_idx_modes
                and not self.window.controller.agent.legacy.enabled()):
            self.window.controller.idx.on_ctx_end(ctx, mode=mode)  # update ctx DB index
            # disabled in agent mode here to prevent loops, handled in agent flow internally if agent mode

        self.log("End.")
        self.window.dispatch(AppEvent(AppEvent.CTX_END))  # app event

        # restore state to idle if no errors
        if self.window.state != self.window.STATE_ERROR:
            self.window.stateChanged.emit(self.window.STATE_IDLE)

        if mode != MODE_ASSISTANT:
            self.window.controller.kernel.stack.handle()  # handle reply
            event = RenderEvent(RenderEvent.RELOAD)
            self.window.dispatch(event)  # reload chat window

    def log(self, data: Any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.controller.chat.log(data)
