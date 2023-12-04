# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.02 22:00:00                  #
# ================================================== #

from ..tokens import num_tokens_prompt, num_tokens_only, num_tokens_extra
from ..utils import trans


class UI:
    def __init__(self, window=None):
        """
        UI update controller

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """Setups UI"""
        self.update()

    def update(self):
        """Updates UI"""
        self.update_counters()

    def update_counters(self):
        """Updates tokens counters"""
        model = self.window.config.data['model']
        mode = self.window.config.data['mode']
        user_name = self.window.config.data['user_name']
        ai_name = self.window.config.data['ai_name']
        max_total_tokens = self.window.config.data['max_total_tokens']
        extra_tokens = num_tokens_extra(model)

        prompt_tokens = 0
        input_tokens = 0

        if mode == "chat" or mode == "vision":
            # prompt tokens (without extra tokens)
            system_prompt = str(self.window.config.data['prompt'].strip())
            prompt_tokens = num_tokens_prompt(system_prompt, "", model)
            prompt_tokens += num_tokens_only("system", model)

            # input tokens
            input_text = str(self.window.data['input'].toPlainText().strip())
            input_tokens = num_tokens_prompt(input_text, "", model)
            input_tokens += num_tokens_only("user", model)
        elif mode == "completion":
            # prompt tokens (without extra tokens)
            system_prompt = str(self.window.config.data['prompt'].strip())
            prompt_tokens = num_tokens_only(system_prompt, model)

            # input tokens
            input_text = str(self.window.data['input'].toPlainText().strip())
            message = ""
            if user_name is not None \
                    and ai_name is not None \
                    and user_name != "" \
                    and ai_name != "":
                message += "\n" + user_name + ": " + str(input_text)
                message += "\n" + ai_name + ":"
            else:
                message += "\n" + str(input_text)
            input_tokens = num_tokens_only(message, model)
            extra_tokens = 0  # no extra tokens in completion mode

        # used tokens
        used_tokens = prompt_tokens + input_tokens

        # context tokens
        ctx_len_all = len(self.window.gpt.context.items)
        ctx_len, ctx_tokens = self.window.gpt.context.count_prompt_items(model, mode, used_tokens, max_total_tokens)

        # zero if context not used
        if not self.window.config.data['use_context']:
            ctx_tokens = 0
            ctx_len = 0

        # total tokens
        total_tokens = prompt_tokens + input_tokens + ctx_tokens + extra_tokens

        # update counters
        string = "{} / {} - {} {}".format(ctx_len, ctx_len_all, ctx_tokens, trans('ctx.tokens'))
        self.window.data['prompt.context'].setText(string)

        threshold = str(int(self.window.config.data['context_threshold']))

        parsed_total = str(int(total_tokens))
        parsed_total = parsed_total.replace("000000", "M").replace("000", "k")

        parsed_max_total = str(int(max_total_tokens))
        parsed_max_total = parsed_max_total.replace("000000", "M").replace("000", "k")

        string = "{} + {} + {} + {} = {} / {} (-{})".format(input_tokens, prompt_tokens, ctx_tokens, extra_tokens,
                                                            parsed_total, parsed_max_total, threshold)
        self.window.data['input.counter'].setText(string)
