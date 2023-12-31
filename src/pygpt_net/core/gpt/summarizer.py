#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

from pygpt_net.item.ctx import CtxItem


class Summarizer:
    def __init__(self, window=None):
        """
        Summarizer

        :param window: Window instance
        """
        self.window = window

    def summary_ctx(self, ctx: CtxItem) -> str:
        """
        Summarize conversation begin

        :param ctx: context item (CtxItem)
        :return: response text (generated summary)
        """
        # default values
        model = 'gpt-3.5-turbo-1106'
        sys_prompt = "You are an expert in conversation summarization"
        text = "Summarize topic of this conversation in one sentence. Use best keywords to describe it. " \
               "Summary must be in the same language as the conversation and it will be used for conversation title " \
               "so it must be EXTREMELY SHORT and concise - use maximum 5 words: \n\n"
        text += "User: " + str(ctx.input) + "\nAI Assistant: " + str(ctx.output)

        # custom values
        if self.window.core.config.get('ctx.auto_summary.system') is not None \
                and self.window.core.config.get('ctx.auto_summary.system') != "":
            sys_prompt = self.window.core.config.get('ctx.auto_summary.system')
        if self.window.core.config.get('ctx.auto_summary.prompt') is not None \
                and self.window.core.config.get('ctx.auto_summary.prompt') != "":
            text = self.window.core.config.get('ctx.auto_summary.prompt'). \
                replace("{input}", str(ctx.input)).replace("{output}", str(ctx.output))
        if self.window.core.config.get('ctx.auto_summary.model') is not None \
                and self.window.core.config.get('ctx.auto_summary.model') != "":
            model = self.window.core.config.get('ctx.auto_summary.model')

        # quick call OpenAI API
        response = self.window.core.gpt.quick_call(text, sys_prompt, False, 500, model)
        if response is not None:
            return response
