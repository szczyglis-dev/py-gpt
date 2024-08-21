#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.22 00:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "agent"
        self.name = "Autonomous Agent (inline)"
        self.description = "Enables inline autonomous mode (Agent) in current mode. " \
                           "WARNING: Please use with caution - this mode, when connected with other plugins, " \
                           "may produce unexpected results!"
        self.type = [
            "agent",
            "cmd.inline",
        ]
        self.order = 9998
        self.use_locale = True
        self.init_options()

    def init_options(self):
        """
        Initialize options
        """
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
                 "stone towards the ultimate objective.\n" \
                 "9. Treat the entire dialogue as a monologue aimed at devising" \
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
                          "proceed to complete each one in sequence. Next, break down each sub-task into even " \
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
        self.add_option(
            "iterations",
            type="int",
            value=3,
            label="Iterations",
            description="How many iterations to run? 0 = infinite.\n"
                        "WARNING: setting this to 0 can cause a lot of requests and heavy tokens usage!",
            min=0,
            max=100,
            multiplier=1,
            step=1,
            slider=True,
        )
        # prompts list
        keys = {
            "enabled": "bool",
            "name": "text",
            "prompt": "textarea",
        }
        items = [
            {
                "enabled": True,
                "name": "Default",
                "prompt": prompt,
            },
            {
                "enabled": False,
                "name": "Extended",
                "prompt": extended_prompt,
            },
        ]
        desc = "Prompt used to instruct how to handle autonomous mode, you can create as many prompts as you want." \
               "First active prompt on list will be used to handle autonomous mode."
        tooltip = desc
        self.add_option(
            "prompts",
            type="dict",
            value=items,
            label="Prompts",
            description=desc,
            tooltip=tooltip,
            keys=keys,
        )
        self.add_option(
            "auto_stop",
            type="bool",
            value=True,
            label="Auto-stop after goal is reached",
            description="If enabled, plugin will stop after goal is reached.",
        )
        self.add_option(
            "reverse_roles",
            type="bool",
            value=True,
            label="Reverse roles between iterations",
            description="If enabled, roles will be reversed between iterations.",
        )

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

    def is_allowed(self) -> bool:
        """
        Check if plugin is allowed to run

        :return: True if plugin is allowed to run
        """
        return self.window.core.config.get("mode") != "agent"  # check global mode

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: event args
        :param kwargs: event kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        always_events = [Event.FORCE_STOP, Event.PLUGIN_SETTINGS_CHANGED, Event.ENABLE, Event.DISABLE]

        if not self.is_allowed() and name != Event.DISABLE:
            return

        if name not in always_events and not self.is_active_prompt():
            return

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

        elif name in [
            Event.ENABLE,
            Event.DISABLE,
        ]:
            if data['value'] == self.id:
                self.window.controller.agent.update()  # update agent status bar

        elif name == Event.PLUGIN_SETTINGS_CHANGED:
            self.window.controller.agent.update()  # update agent status bar

        elif name in [
            Event.CMD_INLINE,
            Event.CMD_EXECUTE,
        ]:
            if self.get_option_value("auto_stop"):
                self.cmd(
                    ctx,
                    data['commands'],
                )

    def is_active_prompt(self) -> bool:
        """
        Check if active prompt is enabled

        :return: True if active prompt is enabled
        """
        for item in self.get_option_value("prompts"):
            if item["enabled"]:
                return True
        return False

    def on_system_prompt(self, prompt: str) -> str:
        """
        Event: SYSTEM_PROMPT

        :param prompt: prompt
        :return: updated prompt
        """
        pre_prompt = ("YOU ARE NOW AN AUTONOMOUS AGENT AND YOU ARE ENTERING NOW INTO AGENT MODE.\n"
                      "Use below instructions in every agent run iteration:\n\n")
        return pre_prompt + self.window.controller.agent.flow.on_system_prompt(
            prompt,
            append_prompt=self.get_first_active_prompt(),
            auto_stop=self.get_option_value("auto_stop"),
        )

    def on_input_before(self, prompt: str) -> str:
        """
        Event: INPUT_BEFORE

        :param prompt: prompt
        :return: updated prompt
        """
        return self.window.controller.agent.flow.on_input_before(prompt)

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Events: CMD_INLINE, CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        self.window.controller.agent.flow.cmd(ctx, cmds)  # force execute

    def on_stop(self):
        """
        Event: FORCE_STOP
        """
        self.window.controller.agent.flow.on_stop()  # force stop

    def on_user_send(self, text: str):
        """
        Event: USER_SEND

        :param text: text
        """
        self.window.controller.agent.flow.on_user_send(text)

    def on_ctx_end(self, ctx: CtxItem):
        """
        Event: CTX_END

        :param ctx: CtxItem
        """
        self.window.controller.agent.flow.on_ctx_end(
            ctx,
            iterations=int(self.get_option_value("iterations")),
        )

    def on_ctx_before(self, ctx: CtxItem):
        """
        Event: CTX_BEFORE

        :param ctx: CtxItem
        """
        self.window.controller.agent.flow.on_ctx_before(
            ctx,
            reverse_roles=self.get_option_value("reverse_roles"),
        )

    def on_ctx_after(self, ctx: CtxItem):
        """
        Event: CTX_AFTER

        :param ctx: CtxItem
        """
        self.window.controller.agent.flow.on_ctx_after(ctx)

    def get_first_active_prompt(self) -> str:
        """
        Get first active prompt from prompts list

        :return: system prompt
        """
        for item in self.get_option_value("prompts"):
            if item["enabled"]:
                return item["prompt"]
        return ""
