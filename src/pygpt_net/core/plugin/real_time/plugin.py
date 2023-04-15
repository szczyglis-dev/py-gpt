#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.04.15 02:00:00                  #
# ================================================== #
from datetime import datetime

from ..base_plugin import BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "real_time"
        self.name = "Real Time"
        self.description = "Appends real-time (hour and date) to every system prompt."
        self.options = {}
        self.options["hour"] = {
            "type": "bool",
            "slider": False,
            "label": "Append time",
            "description": "If enabled, current time will be appended to system prompt.",
            "tooltip": "Hour will be appended to system prompt.",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["date"] = {
            "type": "bool",
            "slider": False,
            "label": "Append date",
            "description": "If enabled, current date will be appended to system prompt.",
            "tooltip": "Date will be appended to system prompt.",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["tpl"] = {
            "type": "textarea",
            "slider": False,
            "label": "Template",
            "description": "Template to append to system prompt."
                           "\nPlaceholder {time} will be replaced with current date and time in real-time.",
            "tooltip": "Text to append to system prompt.",
            "value": " Current time is {time}.",
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.window = None

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
        """Event: On user send text"""
        return text

    def on_ctx_begin(self, ctx):
        """Event: On new context begin"""
        return ctx

    def on_ctx_end(self, ctx):
        """Event: On context end"""
        return ctx

    def on_system_prompt(self, prompt):
        """Event: On prepare system prompt"""
        if self.options["hour"]["value"] or self.options["date"]["value"]:
            if self.options["hour"]["value"] and self.options["date"]["value"]:
                prompt += self.options["tpl"]["value"].format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            elif self.options["hour"]["value"]:
                prompt += self.options["tpl"]["value"].format(time=datetime.now().strftime('%H:%M:%S'))
            elif self.options["date"]["value"]:
                prompt += self.options["tpl"]["value"].format(time=datetime.now().strftime('%Y-%m-%d'))
        return prompt

    def on_ai_name(self, name):
        """Event: On set AI name"""
        return name

    def on_user_name(self, name):
        """Event: On set username"""
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
        """
        return text

    def on_ctx_before(self, ctx):
        """
        Event: Before ctx

        :param ctx: Text
        """
        return ctx

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: ctx
        """
        return ctx
