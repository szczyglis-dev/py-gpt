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

from typing import Any

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_EXPERT,
)
from pygpt_net.core.events import KernelEvent, RenderEvent
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.ctx.reply import ReplyContext
from pygpt_net.item.ctx import CtxItem


class Experts:
    def __init__(self, window=None):
        """
        Experts controller

        :param window: Window instance
        """
        self.window = window
        self.is_stop = False

    def append_prompts(
            self,
            mode: str,
            sys_prompt: str,
    ) -> str:
        """
        Append prompt to the window

        :param mode: Mode
        :param sys_prompt: Prompt text
        :return: Updated system prompt
        """
        core = self.window.core
        controller = self.window.controller

        # if agent enabled
        if controller.agent.legacy.enabled():
            prev_prompt = sys_prompt
            sys_prompt = core.prompt.get("agent.instruction")
            if prev_prompt is not None and prev_prompt.strip() != "":
                sys_prompt = sys_prompt + "\n\n" + prev_prompt  # append previous prompt

        # if expert or agent mode
        if self.enabled() or controller.agent.legacy.enabled(check_inline=False):  # master expert has special prompt
            if controller.agent.legacy.enabled():  # if agent then leave agent prompt
                sys_prompt += "\n\n" + core.experts.get_prompt()  # both, agent + experts
            else:
                sys_prompt = core.experts.get_prompt()
                # mode = "chat"  # change mode to chat for expert

        # if global mode is agent
        if mode == MODE_AGENT:
            sys_prompt = controller.agent.legacy.on_system_prompt(
                sys_prompt,
                append_prompt=None,  # sys prompt from preset is used here
                auto_stop=core.config.get('agent.auto_stop'),
            )

        return sys_prompt

    def handle(self, ctx: CtxItem) -> int:
        """
        Handle mentions (calls) to experts

        :param ctx: CtxItem
        :return: Number of calls made to experts
        """
        core = self.window.core
        controller = self.window.controller
        dispatch = self.window.dispatch
        log = self.log
        stream = core.config.get('stream')
        num_calls = 0

        # extract expert mentions
        if self.enabled() or controller.agent.legacy.enabled(check_inline=False):
            # re-send to master
            if ctx.sub_reply:
                core.ctx.update_item(ctx)
                core.experts.reply(ctx)
            else:
                # abort if reply
                if ctx.reply:
                    return num_calls

                # call experts
                mentions = core.experts.extract_calls(ctx)

                if mentions:
                    log("Calling experts...")
                    dispatch(RenderEvent(RenderEvent.END, {
                        "meta": ctx.meta,
                        "ctx": ctx,
                        "stream": stream,
                    }))  # close previous render

                    for expert_id in mentions:
                        if not core.experts.exists(expert_id):
                            log(f"Expert not found: {expert_id}")
                            continue

                        log(f"Calling: {expert_id}")
                        ctx.sub_calls += 1

                        # add to reply stack
                        reply = ReplyContext()
                        reply.type = ReplyContext.EXPERT_CALL
                        reply.ctx = ctx
                        reply.parent_id = expert_id
                        reply.input = mentions[expert_id]

                        # send to kernel
                        context = BridgeContext()
                        context.ctx = ctx
                        context.reply_context = reply
                        dispatch(KernelEvent(KernelEvent.AGENT_CALL, {
                            'context': context,
                            'extra': {},
                        }))
                        num_calls += 1

        return num_calls

    def enabled(self, check_inline: bool = True) -> bool:
        """
        Check if experts are enabled

        :param check_inline: check inline mode
        :return: True if experts are enabled
        """
        modes = [MODE_EXPERT]
        mode = self.window.core.config.get('mode')
        if not check_inline:
            return mode in modes
        else:
            return mode in modes or self.window.controller.plugins.is_type_enabled("expert")

    def stopped(self) -> bool:
        """
        Check if experts are stopped

        :return: True if experts are stopped
        """
        return self.is_stop

    def stop(self):
        """Stop experts"""
        self.is_stop = True

    def unlock(self):
        """Unlock experts"""
        self.is_stop = False

    def log(self, data: Any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)