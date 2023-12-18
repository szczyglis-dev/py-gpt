#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #

class BasePlugin:
    def __init__(self):
        self.id = ""
        self.name = ""
        self.type = []  # audio.input, audio.output
        self.description = ""
        self.urls = {}
        self.options = {}
        self.initial_options = {}
        self.window = None
        self.enabled = False
        self.order = 0

    def setup(self):
        """
        Return available config options

        :return: config options
        """
        return self.options

    def add_option(self, name, type, value=None, label="", description="",
                   tooltip=None, min=None, max=None, multiplier=1, step=1, slider=False,
                   keys=None, advanced=False, secret=False, persist=False, urls=None):
        """
        Add option

        :param name: Option name (ID, key)
        :param type: Option type (text, textarea, bool, int, float, dict)
        :param value: Option value
        :param label: Option label
        :param description: Option description
        :param tooltip: Option tooltip
        :param min: Option min value
        :param max: Option max value
        :param multiplier: Option float value multiplier
        :param step: Option step value (for slider)
        :param slider: Option slider (True/False)
        :param keys: Option keys (for dict type)
        :param advanced: Option advanced (True/False)
        :param secret: Option secret (True/False)
        :param persist: Option persist (True/False)
        :param urls: Option URLs
        """
        if tooltip is None:
            tooltip = description

        option = {
            "type": type,
            "value": value,
            "label": label,
            "description": description,
            "tooltip": tooltip,
            "min": min,
            "max": max,
            "multiplier": multiplier,
            "step": step,
            "slider": slider,
            "keys": keys,
            "advanced": advanced,
            "secret": secret,
            "persist": persist,
            "urls": urls,
        }
        self.options[name] = option

    def has_option(self, name):
        """
        Check if option exists

        :param name: option name
        :return: true if exists
        """
        return name in self.options

    def get_option(self, name):
        """
        Return option

        :param name: option name
        :return: option
        """
        if self.has_option(name):
            return self.options[name]

    def get_option_value(self, name):
        """
        Return option value

        :param name: option name
        :return: option value
        """
        if self.has_option(name):
            return self.options[name]["value"]

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

    def on_user_send(self, text):
        """
        Event: On user send text

        :param text: text
        :return: text
        """
        return text

    def on_ctx_begin(self, ctx):
        """
        Event: On new context begin

        :param ctx: context
        :return: context
        """
        return ctx

    def on_ctx_end(self, ctx):
        """
        Event: On context end

        :param ctx: context
        :return: context
        """
        return ctx

    def on_system_prompt(self, prompt):
        """
        Event: On prepare system prompt

        :param prompt: prompt
        :return: prompt
        """
        return prompt

    def on_ai_name(self, name):
        """
        Event: On set AI name

        :param name: name
        :return: name
        """
        return name

    def on_user_name(self, name):
        """
        Event: On set user name

        :param name: name
        :return: name
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

        :param text: text
        """
        return text

    def on_ctx_before(self, ctx):
        """
        Event: Before ctx

        :param ctx: text
        """
        return ctx

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: ctx
        """
        return ctx
