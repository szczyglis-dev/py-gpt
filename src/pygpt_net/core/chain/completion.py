#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 21:00:00                  #
# ================================================== #

class Completion:
    def __init__(self, window=None):
        """
        Langchain Wrapper

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0

    def send(self, input_prompt, stream_mode=False, system_prompt=None, ai_name=None, user_name=None):
        """
        Chat with LLM

        :param input_prompt: prompt
        :param stream_mode: stream mode
        :param system_prompt: system prompt (optional)
        :param ai_name: AI name (optional)
        :param user_name: username (optional)
        :return: LLM response
        """
        llm = None
        model_config = self.window.core.models.get(self.window.core.config.get('model'))
        if 'provider' in model_config.langchain:
            provider = model_config.langchain['provider']
            if provider in self.window.core.chain.llms:
                try:
                    llm = self.window.core.chain.llms[provider].completion(
                        self.window.core.config.all(), model_config.langchain, stream_mode)
                except Exception as e:
                    self.window.core.debug.log(e)
        if llm is None:
            raise Exception("Invalid LLM")

        message = self.build(input_prompt, system_prompt=system_prompt, ai_name=ai_name, user_name=user_name)
        if stream_mode:
            return llm.stream(message)
        else:
            return llm.invoke(message)

    def build(self, input_prompt, system_prompt=None, ai_name=None, user_name=None):
        """
        Build completion string

        :param input_prompt: prompt (current)
        :param system_prompt: system prompt (optional)
        :param ai_name: AI name (optional)
        :param user_name: username (optional)
        :return: message string (parsed with context)
        :rtype: str
        """
        message = ""

        # tokens config
        model = self.window.core.config.get('model')
        mode = self.window.core.config.get('mode')

        # input tokens: reset
        self.reset_tokens()

        if system_prompt is not None and system_prompt != "":
            message += system_prompt

        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_all_items()
            for item in items:
                if item.input_name is not None \
                        and item.output_name is not None \
                        and item.input_name != "" \
                        and item.output_name != "":
                    if item.input is not None and item.input != "":
                        message += "\n" + item.input_name + ": " + item.input
                    if item.output is not None and item.output != "":
                        message += "\n" + item.output_name + ": " + item.output
                else:
                    if item.input is not None and item.input != "":
                        message += "\n" + item.input
                    if item.output is not None and item.output != "":
                        message += "\n" + item.output

        # append names
        if user_name is not None \
                and ai_name is not None \
                and user_name != "" \
                and ai_name != "":
            message += "\n" + user_name + ": " + str(input_prompt)
            message += "\n" + ai_name + ":"
        else:
            message += "\n" + str(input_prompt)

        # input tokens: update
        self.input_tokens += self.window.core.tokens.from_text(message, model)

        return message

    def reset_tokens(self):
        """Reset input tokens counter"""
        self.input_tokens = 0

    def get_used_tokens(self):
        """Get input tokens counter"""
        return self.input_tokens
