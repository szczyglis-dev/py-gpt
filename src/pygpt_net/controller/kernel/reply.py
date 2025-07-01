#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.01 01:00:00                  #
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
        Reply handler

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
        flush = False
        if "flush" in extra and extra["flush"]:
            flush = True
        ctx = context.ctx
        if ctx is not None:
            self.run_post_response(ctx, extra)
            self.last_result = ctx.results
            if ctx.agent_call:
                return ctx.results # abort if called in agent and return here, TODO: check if needed!!!!!
            self.window.core.debug.info("Reply...")
            if self.window.core.debug.enabled() and self.is_log():
                self.window.core.debug.debug("CTX REPLY: " + str(ctx))
            if ctx.reply:
                if self.reply_idx >= ctx.pid:  # skip if reply already sent for this context
                    # >>> this prevents multiple replies from the same ctx item <<<
                    return []
                self.reply_idx = ctx.pid 
                self.append(ctx)
            if flush or self.window.controller.kernel.async_allowed(ctx):
                self.flush()
            return ctx.results
        return []

    def append(self, ctx: CtxItem):
        """
        Add reply to stack

        :param ctx: context item
        """
        self.window.core.debug.info("Reply stack (add)...")
        self.reply_stack.append(ctx.results)
        ctx.results = []  # clear results
        self.reply_ctx = ctx

    def flush(self):
        """Flush reply stack"""
        if self.reply_ctx is None or len(self.reply_stack) == 0:
            return

        self.window.core.debug.info("Reply stack (flush)...")
        results = []
        for responses in self.reply_stack:
            for result in responses:
                results.append(result)

        self.window.update_status("")  # clear status
        if self.reply_ctx.internal:
            if self.window.controller.agent.legacy.enabled():
                self.window.controller.agent.legacy.add_run()
                self.window.controller.agent.legacy.update()

        # prepare data to send as reply
        tool_data = json.dumps(results)
        if (len(self.reply_stack) < 2
                and self.reply_ctx.extra_ctx
                and self.window.core.config.get("ctx.use_extra")):
            tool_data = self.reply_ctx.extra_ctx  # if extra content is set, use it as data to send

        prev_ctx = self.window.core.ctx.as_previous(self.reply_ctx)  # copy result to previous ctx and clear current ctx
        self.window.core.ctx.update_item(self.reply_ctx)  # update context in db
        self.window.update_status('...')

        # if response from sub call, from experts
        parent_id = None
        if self.reply_ctx.sub_call:
            if self.reply_ctx.meta is not None:
                parent_id = self.reply_ctx.meta.id  # slave meta id

        # tool output append
        data = {
            "meta": self.reply_ctx.meta,
            "tool_data": tool_data,
        }
        event = RenderEvent(RenderEvent.TOOL_UPDATE, data)
        self.window.dispatch(event)
        self.clear()

        # disable reply if LlamaIndex agent is used
        mode = self.window.core.config.get("mode")
        if mode == MODE_LLAMA_INDEX:
            if self.window.core.config.get("llama.idx.react", False):
                self.window.core.debug.info("Reply disabled for LlamaIndex ReAct agent")
                return

        # send reply
        context = BridgeContext()
        context.ctx = prev_ctx
        context.prompt = str(tool_data)
        extra = {
            "force": True,
            "reply": True,
            "internal": True,
            "parent_id": parent_id,
        }
        event = KernelEvent(KernelEvent.REPLY_RETURN, {
            'context': context,
            'extra': extra,
        })
        self.window.dispatch(event)

    def run_post_response(
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
                        # update file explorer view
                        self.window.controller.files.update_explorer()

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
        is_log = False
        if self.window.core.config.has("log.events") \
                and self.window.core.config.get("log.events"):
            is_log = True
        return is_log
