#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 23:55:00                  #
# ================================================== #

from typing import Any

from pygpt_net.core.types import MODE_AGENT, MODE_EXPERT


class Experts:
    """Experts mode prompt/state controller.

    expert_call execution is owned by the Experts plugin and follows the common
    command/tool lifecycle; there is no separate Expert reply flow here.
    """

    def __init__(self, window=None):
        self.window = window
        self.is_stop = False

    def append_prompts(self, mode: str, sys_prompt: str) -> str:
        """Append the manager/legacy-agent Expert instructions."""
        core = self.window.core
        controller = self.window.controller

        if controller.agent.legacy.enabled():
            prev_prompt = sys_prompt
            sys_prompt = controller.agent.legacy.normalize_instruction_prompt(
                core.prompt.get("agent.instruction")
            )
            if prev_prompt is not None and prev_prompt.strip() != "":
                sys_prompt = sys_prompt + "\n\n" + prev_prompt

        if self.enabled() or controller.agent.legacy.enabled(check_inline=False):
            if controller.agent.legacy.enabled():
                sys_prompt += "\n\n" + core.experts.get_prompt()
            else:
                sys_prompt = core.experts.get_prompt()

        if mode == MODE_AGENT:
            sys_prompt = controller.agent.legacy.on_system_prompt(
                sys_prompt,
                append_prompt=None,
                auto_stop=core.config.get("agent.auto_stop"),
            )

        return sys_prompt

    def enabled(self, check_inline: bool = True) -> bool:
        """Return True for dedicated Experts mode or enabled inline Experts."""
        mode = self.window.core.config.get("mode")
        if not check_inline:
            return mode == MODE_EXPERT
        return mode == MODE_EXPERT or self.window.controller.plugins.is_type_enabled("expert")

    def stopped(self) -> bool:
        return self.is_stop

    def stop(self):
        self.is_stop = True

    def unlock(self):
        self.is_stop = False

    def log(self, data: Any):
        self.window.core.debug.info(data)
