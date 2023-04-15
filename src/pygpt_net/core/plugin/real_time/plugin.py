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

from ..base_plugin import BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "real_time"
        self.name = "Real Time"
        self.description = "Appends real-time (hour and date) to every system prompt."
        self.options = {}
        self.options["hour"] = {
            "type": "bool",  # int, float, bool, text, textarea
            "slider": False,  # show slider
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
            "type": "bool",  # int, float, bool, text, textarea
            "slider": False,  # show slider
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
            "type": "textarea",  # int, float, bool, text, textarea
            "slider": False,  # show slider
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

    def on_send(self, text):
        """Event: On send text"""
        pass

    def on_ctx_begin(self):
        """Event: On new context begin"""
        pass

    def on_system_prompt(self):
        """Event: On prepare system prompt"""
        pass

    def on_ai_name(self):
        """Event: On set AI name"""
        pass

    def on_user_name(self):
        """Event: On set user name"""
        pass

    def on_enable(self):
        """Event: On plugin enable"""
        pass

    def on_disable(self):
        """Event: On plugin disable"""
        pass

    def on_before_input(self, text):
        """
        Event: Before input

        :param text: Text
        """
        return text

    def on_after_input(self, text):
        """
        Event: After input

        :param text: Text
        """
        return text

    def on_before_output(self, text):
        """
        Event: Before output

        :param text: Text
        """
        return text

    def on_after_output(self, text):
        """
        Event: After output

        :param text: Text
        """
        return text