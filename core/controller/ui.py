# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

from core.tokens import num_tokens_prompt, num_tokens_extra
from core.utils import trans


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
        user_name = self.window.config.data['user_name']
        max_total_tokens = self.window.config.data['max_total_tokens']
        extra_tokens = num_tokens_extra(model)

        # prompt tokens
        prompt_tokens = num_tokens_prompt(self.window.config.data['prompt'], user_name, model)

        # input tokens
        input_text = self.window.data['input'].toPlainText().strip()
        input_tokens = num_tokens_prompt(input_text, user_name, model)

        # used tokens
        used_tokens = prompt_tokens + input_tokens

        # context tokens
        ctx_len_all = len(self.window.gpt.context.items)
        ctx_len, ctx_tokens = self.window.gpt.context.count_prompt_items(model, used_tokens, max_total_tokens)

        # zero if context not used
        if not self.window.config.data['use_context']:
            ctx_tokens = 0
            ctx_len = 0

        # total tokens
        total_tokens = prompt_tokens + input_tokens + ctx_tokens + extra_tokens

        # update counters
        string = "{} / {} ~ {} {}".format(ctx_len, ctx_len_all, ctx_tokens, trans('ctx.tokens'))
        self.window.data['prompt.context'].setText(string)

        threshold = str(int(self.window.config.data['context_threshold']))

        string = "~ {} + {} + {} + {} = {} / {} (-{})".format(input_tokens, prompt_tokens, ctx_tokens, extra_tokens,
                                                              total_tokens,
                                                              str(int(max_total_tokens)), threshold)
        self.window.data['input.counter'].setText(string)
