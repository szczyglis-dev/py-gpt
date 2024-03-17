#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.13 15:00:00                  #
# ================================================== #

from datetime import datetime

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "real_time"
        self.name = "Real Time"
        self.type = ["time"]
        self.description = "Appends current time and date to every system prompt."
        self.order = 2
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """
        Initialize options
        """
        self.add_option(
            "hour",
            type="bool",
            value=True,
            label="Append time",
            description="If enabled, current time will be appended to system prompt.",
            tooltip="Hour will be appended to system prompt.",
        )
        self.add_option(
            "date",
            type="bool",
            value=True,
            label="Append date",
            description="If enabled, current date will be appended to system prompt.",
            tooltip="Date will be appended to system prompt.",
        )

        desc = "Template to append to system prompt.\n" \
               "Placeholder {time} will be replaced with current date and time in real-time. "
        tooltip = "Text to append to system prompt."
        self.add_option(
            "tpl",
            type="textarea",
            value="Current time is {time}.",
            label="Template",
            description=desc,
            tooltip=tooltip,
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

        if name == Event.SYSTEM_PROMPT:
            silent = False
            if 'silent' in data and data['silent']:
                silent = True
            data['value'] = self.on_system_prompt(
                data['value'],
                silent,
            )

    def on_system_prompt(self, prompt: str, silent: bool = False) -> str:
        """
        Event: SYSTEM_PROMPT

        :param prompt: prompt
        :param silent: silent mode (no logs)
        :return: updated prompt
        """
        if self.get_option_value("hour") or self.get_option_value("date"):
            if prompt.strip() != "":
                prompt += "\n\n"
            if self.get_option_value("hour") and self.get_option_value("date"):
                prompt += self.get_option_value("tpl").\
                    format(time=datetime.now().strftime('%A, %Y-%m-%d %H:%M:%S'))
            elif self.get_option_value("hour"):
                prompt += self.get_option_value("tpl").\
                    format(time=datetime.now().strftime('%H:%M:%S'))
            elif self.get_option_value("date"):
                prompt += self.get_option_value("tpl").\
                    format(time=datetime.now().strftime('%A, %Y-%m-%d'))
        return prompt
