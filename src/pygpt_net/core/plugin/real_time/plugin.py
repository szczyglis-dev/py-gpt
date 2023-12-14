#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.14 21:00:00                  #
# ================================================== #
from datetime import datetime

from ..base_plugin import BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "real_time"
        self.name = "Real Time"
        self.description = "Appends current time and date to every system prompt."
        self.window = None
        self.order = 2
        self.init_options()

    def init_options(self):
        """
        Initializes options
        """
        self.add_option("hour", "bool", True,
                        "Append time",
                        "If enabled, current time will be appended to system prompt.",
                        tooltip="Hour will be appended to system prompt.")
        self.add_option("date", "bool", True,
                        "Append date",
                        "If enabled, current date will be appended to system prompt.",
                        tooltip="Date will be appended to system prompt.")

        desc = "Template to append to system prompt.\nPlaceholder {time} will be replaced with current date and time " \
               "in real-time. "
        tooltip = "Text to append to system prompt."
        self.add_option("tpl", "textarea", " Current time is {time}.",
                        "Template", desc, tooltip=tooltip)

    def setup(self):
        """
        Returns available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attaches window

        :param window: Window
        """
        self.window = window

    def on_user_send(self, text):
        """
        Event: On user send text

        :param text: Text
        :return: Text
        """
        return text

    def on_ctx_begin(self, ctx):
        """
        Event: On new context begin

        :param ctx: Context
        :return: Context
        """
        return ctx

    def on_ctx_end(self, ctx):
        """
        Event: On context end

        :param ctx: Context
        :return: Context
        """
        return ctx

    def on_system_prompt(self, prompt):
        """
        Event: On prepare system prompt

        :param prompt: Prompt
        :return: Prompt
        """
        self.window.log("Plugin: real_time:on_system_prompt [before]: {}".format(prompt))  # log
        if self.get_option_value("hour") or self.get_option_value("date"):
            if self.get_option_value("hour") and self.get_option_value("date"):
                prompt += self.get_option_value("tpl").format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            elif self.get_option_value("hour"):
                prompt += self.get_option_value("tpl").format(time=datetime.now().strftime('%H:%M:%S'))
            elif self.get_option_value("date"):
                prompt += self.get_option_value("tpl").format(time=datetime.now().strftime('%Y-%m-%d'))
        self.window.log("Plugin: real_time:on_system_prompt [after]: {}".format(prompt))  # log
        return prompt

    def on_ai_name(self, name):
        """
        Event: On set AI name

        :param name: Name
        :return: Name
        """
        return name

    def on_user_name(self, name):
        """
        Event: On set username

        :param name: Name
        :return: Name
        """
        return name

    def on_enable(self):
        """Event: On plugin enable"""
        pass

    def on_disable(self):
        """Event: On plugin disable"""
        pass

    def on_input_before(self, text):
        """
        Event: Before input

        :param text: Text
        :return: Text
        """
        return text

    def on_ctx_before(self, ctx):
        """
        Event: Before ctx

        :param ctx: Context
        :return: Context
        """
        return ctx

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: ctx
        :return: ctx
        """
        return ctx
