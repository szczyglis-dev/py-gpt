#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.30 13:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "extra_prompt"
        self.name = "System Prompt Extra (append)"
        self.description = "Appends extra system prompt from list to every system prompt."
        self.iteration = 0
        self.prev_output = None
        self.order = 9998
        self.use_locale = True
        self.stop = False
        self.init_options()

    def init_options(self):
        """
        Initialize options
        """
        # extra prompts
        keys = {
            "enabled": "bool",
            "name": "text",
            "prompt": "textarea",
        }
        items = []
        desc = "Prompt that will be appended to every system prompt. " \
               "All active prompts will be appended to the system prompt in the order they are listed here."
        tooltip = desc
        self.add_option(
            "prompts",
            type="dict",
            value=items,
            label="Prompts",
            description=desc,
            tooltip=tooltip,
            keys=keys,
        )

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
