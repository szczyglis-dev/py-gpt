#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.31 23:00:00                  #
# ================================================== #

import json
from typing import Optional, Dict, Any, List

from pygpt_net.core.events import KernelEvent, RenderEvent
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.item.ctx import CtxItem

class Reply:
    def __init__(self, window=None):
        """
        Reply handler (response from plugins, tools, etc.)

        :param window: Window instance
        """
        self.window = window
        self.reply_stack = []
        self.reply_ctx = None
        self.last_result = None
        self.reply_idx = -1

    def add(
            self,
            context: BridgeContext,
            extra: Dict[str, Any] = None
    ) -> List[Dict]:
        """
        Send reply from plugins to model

        :param context: bridge context
        :param extra: extra data
        :return: list of results
        """
        flush = extra.get("flush", False) if isinstance(extra, dict) else False
        ctx = context.ctx
        if ctx is None:
            return []

        core = self.window.core
        self.last_result = ctx.results
        self.on_post_response(ctx, extra)

        if ctx.agent_call:
            # TODO: clear() here?
            return ctx.results # abort if called by agent, TODO: check if needed!!!!!

        core.debug.info("Reply...")
        if core.debug.enabled() and self.is_log():
            core.debug.debug("CTX REPLY: " + str(ctx))

        if ctx.reply:
            if self.reply_idx >= ctx.pid:  # prevent multiple replies per ctx
                return []
            self.reply_idx = ctx.pid
            self.append(ctx)

        if flush or self.window.controller.kernel.async_allowed(ctx):
            self.flush()

        return ctx.results

    def append(self, ctx: CtxItem):
        """
        Add reply to stack

        :param ctx: context item
        """
        self.window.core.debug.info("Reply stack (add)...")
        self.reply_stack.append(ctx.results)
        self.reply_ctx = ctx
        self.reply_ctx.results = []  # clear results

    def flush(self):
        """Flush reply stack"""
        if self.reply_ctx is None or len(self.reply_stack) == 0:
            return

        core = self.window.core
        dispatch = self.window.dispatch
        core.debug.info("Reply stack (flush)...")

        results = []
        for responses in self.reply_stack:
            for result in responses:
                results.append(result)

        self.window.update_status("")  # clear status
        self.window.controller.agent.on_reply(self.reply_ctx)  # handle reply in agent

        # prepare data to send as reply
        tool_data = json.dumps(results)
        if (len(self.reply_stack) < 2
                and self.reply_ctx.extra_ctx
                and core.config.get("ctx.use_extra")):
            tool_data = self.reply_ctx.extra_ctx  # if extra content is set, use it as data to send

        prev_ctx = core.ctx.as_previous(self.reply_ctx)  # copy result to previous ctx and clear current ctx
        core.ctx.update_item(self.reply_ctx)  # update context in db
        self.window.update_status('...')

        # append tool calls from previous context (used for tool results handling)
        if self.reply_ctx.tool_calls:
            prev_ctx.extra["prev_tool_calls"] = self.reply_ctx.tool_calls

        # tool output append
        dispatch(RenderEvent(RenderEvent.TOOL_UPDATE, {
            "meta": self.reply_ctx.meta,
            "tool_data": tool_data,
        }))
        self.clear()

        # disable reply if LlamaIndex agent is used
        mode = core.config.get("mode")
        if mode == MODE_LLAMA_INDEX and core.config.get("llama.idx.react", False):
            return

        # send reply
        context = BridgeContext()
        context.ctx = prev_ctx
        context.prompt = str(tool_data)
        dispatch(KernelEvent(KernelEvent.REPLY_RETURN, {
            'context': context,
            'extra': {
                "force": True,
                "reply": True,
                "internal": True,
            },
        }))

    def on_post_response(
            self,
            ctx: CtxItem,
            extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Run post-response operations

        :param ctx: context (CtxItem)
        :param extra_data: extra data
        """
        if isinstance(extra_data, dict):
            if (ctx is None or not ctx.agent_call) or not self.window.controller.kernel.is_threaded():
                if "post_update" in extra_data and isinstance(extra_data["post_update"], list):
                    if "file_explorer" in extra_data["post_update"]:
                        self.window.controller.files.update_explorer()  # update file explorer view

    def clear(self):
        """Clear reply stack"""
        self.window.core.debug.info("Reply stack (clear)...")
        self.reply_ctx = None
        self.reply_stack = []

    def is_log(self) -> bool:
        """
        Check if event can be logged

        :return: true if can be logged
        """
        return self.window.core.config.get("log.events", False)
