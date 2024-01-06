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
        self.name = "Autonomous Mode: AI to AI conversation"
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
        prompt = "AUTONOMOUS MODE: 1. You will now enter self-dialogue mode, where you will be conversing with yourself," \
                 " not with a human. 2. When you enter self-dialogue mode, remember that you are engaging in a conversation " \
                 "with yourself. Any user input will be considered a reply featuring your previous response. " \
                 "3. The objective of this self-conversation is well-defined—focus on achieving it. 4. Your new message " \
                 "should be a continuation of the last response you generated, essentially replying to yourself and " \
                 "extending it. 5. After each response, critically evaluate its effectiveness and alignment with the " \
                 "goal. If necessary, refine your approach. 6. Incorporate self-critique after every response to " \
                 "capitalize on your strengths and address areas needing improvement. 7. To advance towards the goal," \
                 " utilize all the strategic thinking and resources at your disposal. 8. Ensure that the dialogue " \
                 "remains coherent and logical, with each response serving as a stepping stone towards the ultimate " \
                 "objective. 9. Treat the entire dialogue as one long, continuous conversation with oneself, and as " \
                 "a monologue aimed at devising the best possible solution to the problem. 10. Conclude the " \
                 "self-dialogue upon realizing the goal or reaching a pivotal conclusion that meets the initial criteria. " \
                 "11. You are allowed to use any commands and tools without asking for it. 12. ALWAYS break down the " \
                 "main task into manageable logical subtasks, systematically addressing and analyzing each one " \
                 "in sequence. 13. The first instruction, along with a description of the main objective, will come" \
                 " from the user. 14. Start by breaking down the task into as many smaller sub-tasks as possible, " \
                 "then proceed to complete each one in sequence. Next, break down each sub-task into even smaller tasks, " \
                 "carefully and step by step go through all of them until the required goal is fully " \
                 "and correctly achieved."
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
