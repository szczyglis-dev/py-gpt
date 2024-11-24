#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 03:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event

from .config import Config


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "extra_prompt"
        self.name = "System Prompt Extra"
        self.description = "Appends extra system prompt from list to every system prompt."
        self.prefix = "Prompt"
        self.iteration = 0
        self.prev_output = None
        self.order = 9998
        self.use_locale = True
        self.stop = False
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: args
        :param kwargs: kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.SYSTEM_PROMPT:
            data['value'] = self.on_system_prompt(data['value'])

    def on_system_prompt(self, prompt: str) -> str:
        """
        Event: SYSTEM_PROMPT

        :param prompt: prompt
        :return: updated prompt
        """
        to_append = []
        for item in self.get_option_value("prompts"):
            if item["enabled"]:
                to_append.append(item["prompt"])
        append_prompt = "\n".join(to_append)
        prompt += "\n" + append_prompt
        return prompt
