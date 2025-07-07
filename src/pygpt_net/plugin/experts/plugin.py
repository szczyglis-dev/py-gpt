#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 20:00:00                  #
# ================================================== #

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_EXPERT,
)
from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event

from .config import Config

class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "experts"
        self.name = "Experts (inline)"
        self.description = "Enables inline experts in current mode."
        self.prefix = "Experts"
        self.type = [
            "expert",
        ]
        self.allowed_cmds = [
            "expert_call",
        ]
        self.order = 9998
        self.use_locale = True
        self.disallowed_modes = [MODE_AGENT, MODE_EXPERT]
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        """
        Initialize options
        """
        self.config.from_defaults(self)

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
