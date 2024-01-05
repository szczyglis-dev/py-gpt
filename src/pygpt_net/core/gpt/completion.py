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

class Completion:
    def __init__(self, window=None):
        """
        Completion wrapper

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0

    def send(self, prompt: str, max_tokens: int, stream_mode: bool = False, system_prompt: str = None,
             ai_name: str = None, user_name: str = None):
        """
        Call OpenAI API for completion

        :param prompt: prompt (user message)
        :param max_tokens: max output tokens
        :param stream_mode: stream mode
        :param system_prompt: system prompt (optional)
        :param ai_name: AI name
        :param user_name: username
        :return: response or stream chunks
        """
        # build prompt message
        message = self.build(prompt, system_prompt=system_prompt, ai_name=ai_name, user_name=user_name)

        # prepare stop word if user_name is set
        stop = ""
        if user_name is not None and user_name != '':
            stop = [user_name + ':']

        client = self.window.core.gpt.get_client()
        model = self.window.core.gpt.get_model('completion')

        response = client.completions.create(
            prompt=message,
            model=model,
            max_tokens=int(max_tokens),
            temperature=self.window.core.config.get('temperature'),
            top_p=self.window.core.config.get('top_p'),
            frequency_penalty=self.window.core.config.get('frequency_penalty'),
            presence_penalty=self.window.core.config.get('presence_penalty'),
            stop=stop,
            stream=stream_mode,
        )
        return response

    def build(self, input_prompt: str, system_prompt: str = None, ai_name: str = None, user_name: str = None) -> str:
        """
        Build completion string

        :param input_prompt: prompt (user input)
        :param system_prompt: system prompt (optional)
        :param ai_name: AI name
        :param user_name: username
        :return: message string (parsed with context)
        """
        message = ""

        # tokens config
        model = self.window.core.config.get('model')
        mode = self.window.core.config.get('mode')

        used_tokens = self.window.core.tokens.from_user(input_prompt, system_prompt)
        max_tokens = self.window.core.config.get('max_total_tokens')
        model_ctx = self.window.core.models.get_num_ctx(model)

        # fit to max model ctx tokens
        if max_tokens > model_ctx:
            max_tokens = model_ctx

        # input tokens: reset
        self.reset_tokens()

        if system_prompt is not None and system_prompt != "":
            message += system_prompt

        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_prompt_items(model, mode, used_tokens, max_tokens)
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

    def get_used_tokens(self) -> int:
        """Get input tokens counter"""
        return self.input_tokens
