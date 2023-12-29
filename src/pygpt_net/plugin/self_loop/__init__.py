#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.18 04:00:00                  #
# ================================================== #

from pygpt_net.plugin.base_plugin import BasePlugin


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
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """
        Initialize options
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

    def handle(self, event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == 'ctx.before':
            self.on_ctx_before(ctx)
        elif name == 'ctx.after':
            self.on_ctx_after(ctx)
        elif name == 'ctx.end':
            self.on_ctx_end(ctx)
        elif name == 'user.send':
            self.on_user_send(data['value'])

    def on_user_send(self, text):
        """
        Event: On user send text

        :param text: text
        """
        self.iteration = 0
        self.prev_output = None

    def on_ctx_end(self, ctx):
        """
        Event: On context end

        :param ctx: CtxItem
        """
        iterations = int(self.get_option_value("iterations"))
        if iterations == 0 or self.iteration < iterations:
            self.iteration += 1
            if self.prev_output is not None and self.prev_output != "":
                self.debug(
                    "Plugin: self_loop:on_ctx_end: {}".format(self.prev_output))  # log
                self.window.controller.input.send(self.prev_output)

    def on_ctx_before(self, ctx):
        """
        Event: Before ctx

        :param ctx: CtxItem
        """
        if self.iteration > 0 and self.iteration % 2 != 0 and self.get_option_value("reverse_roles"):
            self.debug("Plugin: self_loop:on_ctx_before [before]: {}".format(ctx.dump()))  # log
            tmp_input_name = ctx.input_name
            tmp_output_name = ctx.output_name
            ctx.input_name = tmp_output_name
            ctx.output_name = tmp_input_name
            self.debug("Plugin: self_loop:on_ctx_before [after]: {}".format(ctx.dump()))  # log

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: CtxItem
        """
        self.prev_output = ctx.output
        if self.get_option_value("clear_output"):
            self.debug("Plugin: self_loop:on_ctx_after [before]: {}".format(ctx.dump()))  # log
            ctx.output = ""
            self.debug("Plugin: self_loop:on_ctx_after [after]: {}".format(ctx.dump()))  # log
