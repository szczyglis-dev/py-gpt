#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 21:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        """
        Set default options for plugin

        :param plugin: plugin instance
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
        plugin.add_option(
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
        plugin.add_option(
            "prompts",
            type="dict",
            value=items,
            label="Prompts",
            description=desc,
            tooltip=tooltip,
            keys=keys,
        )
        plugin.add_option(
            "auto_stop",
            type="bool",
            value=True,
            label="Auto-stop after goal is reached",
            description="If enabled, plugin will stop after goal is reached.",
        )
        plugin.add_option(
            "reverse_roles",
            type="bool",
            value=True,
            label="Reverse roles between iterations",
            description="If enabled, roles will be reversed between iterations.",
        )