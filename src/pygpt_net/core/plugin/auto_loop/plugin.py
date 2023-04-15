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
        self.id = "self_loop"
        self.name = "Self Loop"
        self.description = "Allows to execute self talk (AI to AI) loop and connects output to input."
        self.options = {}
        self.options["iterations"] = {
            "type": "int",  # int, float, bool, text, textarea
            "slider": True,  # show slider
            "label": "Iterations",
            "description": "How many iterations to run? 0 = infinite.\n"
                           "WARNING: setting this to 0 can cause a lot of requests and heavy tokens usage!",
            "tooltip": "Some tooltip...",
            "value": 3,
            "min": 0,
            "max": 100,
            "multiplier": 1,
            "step": 1,
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