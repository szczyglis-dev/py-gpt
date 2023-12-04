#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.04.16 22:00:00                  #
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
            "type": "int",
            "slider": True,
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
        self.options["clear_output"] = {
            "type": "bool",
            "slider": False,
            "label": "Clear context output",
            "description": "If enabled, previous context output will be cleared before sending new input.",
            "tooltip": "Clear context output",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.options["reverse_roles"] = {
            "type": "bool",
            "slider": False,
            "label": "Reverse roles between iterations",
            "description": "If enabled, roles will be reversed between iterations.",
            "tooltip": "Reverse roles between iterations",
            "value": True,
            "min": None,
            "max": None,
            "multiplier": None,
            "step": None,
        }
        self.iteration = 0
        self.prev_output = None
        self.window = None
        self.order = 9998

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
        self.iteration = 0
        self.prev_output = None
        return text

    def on_ctx_begin(self, ctx):
        """Event: On new context begin"""
        return ctx

    def on_ctx_end(self, ctx):
        """Event: On context end"""
        iterations = int(self.options["iterations"]["value"])
        if iterations == 0 or self.iteration < iterations:
            self.iteration += 1
            if self.prev_output is not None and self.prev_output != "":
                self.window.log(
                    "Plugin: self_loop:on_ctx_end [sending prev_output...]: {}".format(self.prev_output))  # log
                self.window.controller.input.send(self.prev_output)
        return ctx

    def on_system_prompt(self, prompt):
        """Event: On prepare system prompt"""
        return prompt

    def on_ai_name(self, name):
        """Event: On set AI name"""
        return name

    def on_user_name(self, name):
        """Event: On set user name"""
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
        if self.iteration > 0 and self.iteration % 2 != 0 and self.options["reverse_roles"]["value"]:
            self.window.log("Plugin: self_loop:on_ctx_before [before]: {}".format(ctx.dump()))  # log
            tmp_input_name = ctx.input_name
            tmp_output_name = ctx.output_name
            ctx.input_name = tmp_output_name
            ctx.output_name = tmp_input_name
            self.window.log("Plugin: self_loop:on_ctx_before [after]: {}".format(ctx.dump()))  # log
        return ctx

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: ctx
        """
        self.prev_output = ctx.output
        if self.options["clear_output"]["value"]:
            self.window.log("Plugin: self_loop:on_ctx_after [before]: {}".format(ctx.dump()))  # log
            ctx.output = ""
            self.window.log("Plugin: self_loop:on_ctx_after [after]: {}".format(ctx.dump()))  # log
        return ctx
