#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.13 19:00:00                  #
# ================================================== #

from ..base_plugin import BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "self_loop"
        self.name = "Self Loop"
        self.description = "Allows to execute self talk (AI to AI) loop and connect output to input."
        self.iteration = 0
        self.prev_output = None
        self.window = None
        self.order = 9998
        self.init_options()

    def init_options(self):
        """
        Initializes options
        """
        self.add_option("iterations", "int", 3,
                        "Iterations",
                        "How many iterations to run? 0 = infinite.\nWARNING: setting this to 0 can cause a lot of "
                        "requests and heavy tokens usage!",
                        min=0, max=100, multiplier=1, step=1, slider=True)
        self.add_option("clear_output", "bool", True,
                        "Clear context output",
                        "If enabled, previous context output will be cleared before sending new input.")
        self.add_option("reverse_roles", "bool", True,
                        "Reverse roles between iterations",
                        "If enabled, roles will be reversed between iterations.")

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
        self.iteration = 0
        self.prev_output = None
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
        iterations = int(self.options["iterations"]["value"])
        if iterations == 0 or self.iteration < iterations:
            self.iteration += 1
            if self.prev_output is not None and self.prev_output != "":
                self.window.log(
                    "Plugin: self_loop:on_ctx_end [sending prev_output...]: {}".format(self.prev_output))  # log
                self.window.controller.input.send(self.prev_output)
        return ctx

    def on_system_prompt(self, prompt):
        """
        Event: On prepare system prompt

        :param prompt: Prompt
        :return: Prompt
        """
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
        Event: On set user name

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
        :return: ctx
        """
        self.prev_output = ctx.output
        if self.options["clear_output"]["value"]:
            self.window.log("Plugin: self_loop:on_ctx_after [before]: {}".format(ctx.dump()))  # log
            ctx.output = ""
            self.window.log("Plugin: self_loop:on_ctx_after [after]: {}".format(ctx.dump()))  # log
        return ctx
