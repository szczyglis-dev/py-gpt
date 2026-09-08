#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 21:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        """
        Set default options for plugin

        :param plugin: plugin instance
        """
        prompt = """AUTONOMOUS MODE:
- Execute the user's task as one autonomous run.
- Work iteratively: take the next useful action, inspect the result, then continue until the task is complete.
- Use available tools when useful and prefer native tool/function calls when supported.
- Verify tool results instead of assuming success.
- Do not simulate user replies or a self-dialogue and do not repeat earlier text just to continue.
- If user input is required, pause/wait instead of guessing.
- When complete, provide the final user-facing result and finish the run with goal_update(status=\"finished\") when available.
"""
        extended_prompt = """AUTONOMOUS MODE:
- Execute the user's task as one autonomous run until complete, paused, failed, or limited by the configured iteration count.
- Break complex work into practical subtasks, but act on them instead of narrating an artificial internal debate.
- On each iteration, review what is already done and perform the next useful action.
- Use available tools whenever they improve correctness or are required to complete the task. Prefer native tool/function calls when supported.
- Inspect every tool result and adapt the next step to the actual result.
- Avoid repeating previous assistant content. Keep intermediate output focused on useful progress and artifacts.
- Do not expose private chain-of-thought or forced self-critique.
- If more user information is required, finish the current response with goal_update(status=\"wait\") when available.
- If the task cannot be completed, use goal_update(status=\"failed\"); for an intentional pause use status=\"pause\".
- When all requested work is complete, provide the final user-facing result and use goal_update(status=\"finished\") when available.
"""
        plugin.add_option(
            "iterations",
            type="int",
            value=3,
            label="Iterations",
            description="How many iterations to run? 0 = infinite.\n"
                        "WARNING: setting this to 0 can cause a lot of requests and heavy tokens usage!",
            min=0,
            max=100,
            multiplier=1,
            step=1,
            slider=True,
        )
        # prompts list
        keys = {
            "enabled": "bool",
            "name": "text",
            "prompt": "textarea",
        }
        items = [
            {
                "enabled": True,
                "name": "Default",
                "prompt": prompt,
            },
            {
                "enabled": False,
                "name": "Extended",
                "prompt": extended_prompt,
            },
        ]
        desc = "Prompt used to instruct how to handle autonomous mode, you can create as many prompts as you want." \
               "First active prompt on list will be used to handle autonomous mode."
        tooltip = desc
        plugin.add_option(
            "prompts",
            type="dict",
            value=items,
            label="Prompts",
            description=desc,
            tooltip=tooltip,
            keys=keys,
        )
        plugin.add_option(
            "auto_stop",
            type="bool",
            value=True,
            label="Auto-stop after goal is reached",
            description="If enabled, plugin will stop after goal is reached.",
        )
        plugin.add_option(
            "always_continue",
            type="bool",
            value=False,
            label="Always continue",
            description="If enabled, plugin will always continue to the next iteration, even if the goal is reached.",
        )
        plugin.add_option(
            "reverse_roles",
            type="bool",
            value=True,
            label="Reverse roles between iterations",
            description="If enabled, roles will be reversed between iterations.",
        )