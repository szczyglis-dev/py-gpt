#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.19 02:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


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
        self.is_user = True
        self.stop = False
        self.allowed_cmds = [
            "goal_update",
        ]
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
        self.add_option("auto_stop", "bool", True,
                        "Auto-stop after goal is reached",
                        "If enabled, plugin will stop after goal is reached.")
        prompt = "AUTONOMOUS MODE:\n1. You will now enter self-dialogue mode, where you will be conversing with " \
                 "yourself, not with a human.\n2. When you enter self-dialogue mode, remember that you are engaging " \
                 "in a conversation with yourself. Any user input will be considered a reply featuring your " \
                 "previous response.\n3. The objective of this self-conversation is well-defined—focus " \
                 "on achieving it.\n4. Your new message should be a continuation of the last response you generated, " \
                 "essentially replying" \
                 " to yourself and extending it.\n5. After each response, critically evaluate its effectiveness " \
                 "and alignment with the goal. If necessary, refine your approach.\n6. Incorporate self-critique " \
                 "after every response to capitalize on your strengths and address areas needing improvement.\n7. To " \
                 "advance towards the goal, utilize all the strategic thinking and resources at your disposal.\n" \
                 "8. Ensure that the dialogue remains coherent and logical, with each response serving as a stepping " \
                 "stone towards the ultimate objective.\n9. Treat the entire dialogue as a monologue aimed at devising" \
                 " the best possible solution to the problem.\n10. Conclude the self-dialogue upon realizing the " \
                 "goal or reaching a pivotal conclusion that meets the initial criteria.\n11. You are allowed to use " \
                 "any commands and tools without asking for it.\n12. While using commands, always use the correct " \
                 "syntax and never interrupt the command before generating the full instruction.\n13. ALWAYS break " \
                 "down the main task into manageable logical subtasks, systematically addressing and analyzing each" \
                 " one in sequence.\n14. With each subsequent response, make an effort to enhance your previous " \
                 "reply by enriching it with new ideas and do it automatically without asking for it.\n15. Any input " \
                 "that begins with 'user: ' will come from me, and I will be able to provide you with ANY additional " \
                 "commands or goal updates in this manner. " \
                 "The other inputs, not prefixed with 'user: ' will represent" \
                 " your previous responses.\n16. Start by breaking down the task into as many smaller sub-tasks as " \
                 "possible, then proceed to complete each one in sequence.  Next, break down each sub-task into even " \
                 "smaller tasks, carefully and step by step go through all of them until the required goal is fully " \
                 "and correctly achieved.\n"
        extended_prompt = "AUTONOMOUS MODE:\n1. You will now enter self-dialogue mode, where you will be conversing " \
                          "with yourself, not with a human.\n2. When you enter self-dialogue mode, remember that you " \
                          "are engaging in a conversation with yourself. Any user input will be considered a reply " \
                          "featuring your previous response.\n3. The objective of this self-conversation is " \
                          "well-defined—focus on achieving it.\n4. Your new message should be a continuation of " \
                          "the last response you generated, essentially replying to yourself and extending it.\n" \
                          "5. After each response, critically evaluate its effectiveness and alignment with the goal." \
                          " If necessary, refine your approach.\n6. Incorporate self-critique after every response " \
                          "to capitalize on your strengths and address areas needing improvement.\n7. To advance " \
                          "towards the goal, utilize all the strategic thinking and resources at your disposal.\n" \
                          "8. Ensure that the dialogue remains coherent and logical, with each response serving " \
                          "as a stepping stone towards the ultimate objective.\n9. Treat the entire dialogue " \
                          "as a monologue aimed at devising the best possible solution to the problem.\n" \
                          "10. Conclude the self-dialogue upon realizing the goal or reaching a pivotal conclusion " \
                          "that meets the initial criteria.\n11. You are allowed to use any commands and tools " \
                          "without asking for it.\n12. While using commands, always use the correct syntax " \
                          "and never interrupt the command before generating the full instruction.\n13. Break down " \
                          "the main task into manageable logical subtasks, systematically addressing and analyzing " \
                          "each one in sequence.\n14. With each subsequent response, make an effort to enhance " \
                          "your previous reply by enriching it with new ideas and do it automatically without " \
                          "asking for it.\n15. Any input that begins with 'user: ' will come from me, and I will " \
                          "be able to provide you with ANY additional commands or goal updates in this manner. " \
                          "The other inputs, not prefixed with 'user: ' will represent your previous responses.\n" \
                          "16. Start by breaking down the task into as many smaller sub-tasks as possible, then " \
                          "proceed to complete each one in sequence.  Next, break down each sub-task into even " \
                          "smaller tasks, carefully and step by step go through all of them until the required " \
                          "goal is fully and correctly achieved.\n17. Always split every step into parts: " \
                          "main goal, current sub-task, potential problems, pros and cons, criticism of the " \
                          "previous step, very detailed (about 10-15 paragraphs) response to current subtask, " \
                          "possible improvements, next sub-task to achieve and summary.\n18. Do not start the " \
                          "next subtask until you have completed the previous one.\n19. Ensure to address and " \
                          "correct any criticisms or mistakes from the previous step before starting the next " \
                          "subtask.\n20. Do not finish until all sub-tasks and the main goal are fully achieved " \
                          "in the best possible way. If possible, improve the path to the goal until the full " \
                          "objective is achieved.\n21. Conduct the entire discussion in my native language.\n" \
                          "22. Upon reaching the final goal, provide a comprehensive summary including " \
                          "all solutions found, along with a complete, expanded response."
        self.add_option("prompt", "textarea", prompt,
                        "Prompt",
                        "Prompt used to instruct how to handle autonomous mode",
                        tooltip="Prompt", advanced=True)
        self.add_option("extended_prompt", "textarea", extended_prompt,
                        "Extended Prompt",
                        "Prompt used to instruct how to handle autonomous mode (extended step-by-step reasoning)",
                        tooltip="Extended Prompt", advanced=True)
        self.add_option("use_extended", "bool", False,
                        "Use extended prompt",
                        "If enabled, plugin will use extended prompt.")

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

        if name == Event.CTX_BEFORE:
            self.on_ctx_before(ctx)
        elif name == Event.CTX_AFTER:
            self.on_ctx_after(ctx)
        elif name == Event.CTX_END:
            self.on_ctx_end(ctx)
        elif name == Event.USER_SEND:
            self.on_user_send(data['value'])
        elif name == Event.FORCE_STOP:
            self.on_stop()
        elif name == Event.SYSTEM_PROMPT:
            data['value'] = self.on_system_prompt(data['value'])
        elif name == Event.INPUT_BEFORE:
            data['value'] = self.on_input_before(data['value'])
        elif name == Event.CMD_INLINE or name == Event.CMD_EXECUTE:
            if self.get_option_value("auto_stop"):
                self.cmd(ctx, data['commands'])

    def on_system_prompt(self, prompt: str) -> str:
        """
        Event: On prepare system prompt

        :param prompt: prompt
        :return: updated prompt
        """
        stop_cmd = ""
        if self.get_option_value("auto_stop"):
            stop_cmd = '\n\nON FINISH: When you believe that the task has been completed 100% and all goals have ' \
                       'been achieved, include the following command in your response, which will stop further ' \
                       'conversation. Remember to put it in the form as given, at the end of response and including ' \
                       'the surrounding ~###~ marks: ~###~{"cmd": "goal_update", "params": {"status": "finished"}}~###~'

        # select prompt to use
        append_prompt = self.get_option_value("prompt")
        if self.get_option_value("use_extended"):
            append_prompt = self.get_option_value("extended_prompt")

        prompt += "\n" + append_prompt + stop_cmd
        return prompt

    def on_input_before(self, prompt: str) -> str:
        """
        Event: On user input before

        :param prompt: prompt
        :return: updated prompt
        """
        if not self.is_user:
            return prompt

        return "user: " + prompt

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: On command

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        is_cmd = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
            return

        for item in my_commands:
            try:
                if item["cmd"] == "goal_update":
                    if item["params"]["status"] == "finished":
                        self.on_stop()
                        self.window.ui.status(trans('status.finished'))  # show info
            except Exception as e:
                self.log("Error: " + str(e))
                return

    def on_stop(self):
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
        self.is_user = True
        if self.stop:
            self.stop = False

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
                # internal call will not trigger async mode and will hide the message from previous iteration

    def on_ctx_before(self, ctx: CtxItem):
        """
        Event: Before ctx

        :param ctx: CtxItem
        """
        ctx.internal = True  # always force internal call
        self.is_user = False
        if self.iteration == 0:
            ctx.first = True

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
