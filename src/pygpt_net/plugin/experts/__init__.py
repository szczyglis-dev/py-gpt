#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 05:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "experts"
        self.name = "Experts (inline)"
        self.description = "Enables inline experts in current mode."
        self.type = [
            "expert",
        ]
        self.allowed_cmds = [
            "expert_call",
        ]
        self.order = 9998
        self.use_locale = True
        self.disallowed_modes = ["agent", "expert"]
        self.init_options()

    def init_options(self):
        """
        Initialize options
        """
        pass  # no options

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

    def is_allowed(self) -> bool:
        """
        Check if plugin is allowed to run

        :return: True if plugin is allowed to run
        """
        return self.window.core.config.get("mode") not in self.disallowed_modes

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: event args
        :param kwargs: event kwargs
        """
        if not self.is_allowed():
            return

        name = event.name
        data = event.data
        if name == Event.SYSTEM_PROMPT:
            if "is_expert" in data and data["is_expert"]:
                return  # disable if called inside expert
            data['value'] = self.on_system_prompt(data['value'])

    def on_system_prompt(self, prompt: str) -> str:
        """
        Event: SYSTEM_PROMPT

        :param prompt: prompt
        :return: updated prompt
        """
        if prompt is not None and prompt.strip() != "":
            prompt+= "\n\n"
        return prompt + self.window.core.experts.get_prompt()
