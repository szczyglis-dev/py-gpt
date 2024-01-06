#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.04 06:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "self_loop"
        self.name = "Self Loop: AI to AI (Autonomous mode)"
        self.description = "Enables autonomous conversation (AI to AI), manages loop, and connects output back to input."
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
        self.add_option("iterations", "int", 3,
                        "Iterations",
                        "How many iterations to run? 0 = infinite.\nWARNING: setting this to 0 can cause a lot of "
                        "requests and heavy tokens usage!",
                        min=0, max=100, multiplier=1, step=1, slider=True)
        self.add_option("reverse_roles", "bool", True,
                        "Reverse roles between iterations",
                        "If enabled, roles will be reversed between iterations.")
        prompt = "AUTONOMOUS MODE: \n1. You will now enter self-dialogue mode, where you will be conversing with yourself," \
                 " not with a human. \n2. you enter self-dialogue mode, remember that you are engaging in a conversation " \
                 "with yourself. Any user input will be considered a reply featuring your previous response. " \
                 "\n3. The objective of this self-conversation is well-defined—focus on achieving it. \n4. Your new message" \
                 " should be a continuation of the last response you generated, essentially replying to yourself and extending it. " \
                 "\n5. After each response, critically evaluate its effectiveness and alignment with the goal. " \
                 "If necessary, refine your approach. \n6. Incorporate self-critique after every response to capitalize " \
                 "on your strengths and address areas needing improvement. \n7. To advance towards the goal, utilize all" \
                 " the strategic thinking and resources at your disposal. \n8. Ensure that the dialogue remains coherent" \
                 " and logical, with each response serving as a stepping stone towards the ultimate objective. " \
                 "\n9. Conclude the self-dialogue upon realizing the goal or reaching a pivotal conclusion that meets " \
                 "the initial criteria. \n10. You are allowed to use any commands and tools without asking for it. \n11. " \
                 "ALWAYS BREAK DOWN the main task into manageable logical subtasks, " \
                 "systematically addressing and analyzing each one in sequence. 12. The first instruction, along with a " \
                 "description of the main objective, will come from the user."
        self.add_option("prompt", "textarea", prompt,
                        "Prompt",
                        "Prompt used to instruct how to handle autonomous mode",
                        tooltip="Prompt", advanced=True)

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
        elif name == 'force.stop':
            self.on_stop(data['value'])
        elif name == 'system.prompt':
            data['value'] = self.on_system_prompt(data['value'])

    def on_system_prompt(self, prompt: str):
        """
        Event: On prepare system prompt

        :param prompt: prompt
        :return: updated prompt
        """
        prompt += "\n" + self.get_option_value("prompt")
        return prompt

    def on_stop(self, value: bool):
        """
        Event: On force stop

        :param value: value
        """
        self.iteration = 0
        self.prev_output = None
        self.stop = True

    def on_user_send(self, text: str):
        """
        Event: On user send text

        :param text: text
        """
        self.iteration = 0
        self.prev_output = None

    def on_ctx_end(self, ctx: CtxItem):
        """
        Event: On context end

        :param ctx: CtxItem
        """
        if self.stop:
            self.stop = False
            self.iteration = 0
            self.prev_output = None

        iterations = int(self.get_option_value("iterations"))
        if iterations == 0 or self.iteration < iterations:
            self.iteration += 1
            if self.prev_output is not None and self.prev_output != "":
                self.debug(
                    "Plugin: self_loop:on_ctx_end: {}".format(self.prev_output))  # log
                self.window.controller.chat.input.send(self.prev_output, force=True, internal=True)

    def on_ctx_before(self, ctx: CtxItem):
        """
        Event: Before ctx

        :param ctx: CtxItem
        """
        if self.iteration > 0 and self.iteration % 2 != 0 and self.get_option_value("reverse_roles"):
            tmp_input_name = ctx.input_name
            tmp_output_name = ctx.output_name
            ctx.input_name = tmp_output_name
            ctx.output_name = tmp_input_name

    def on_ctx_after(self, ctx: CtxItem):
        """
        Event: After ctx

        :param ctx: CtxItem
        """
        self.prev_output = ctx.output
