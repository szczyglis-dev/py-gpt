#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 21:00:00                  #
# ================================================== #

class Chat:
    def __init__(self, window=None):
        """
        ChatCompletion wrapper

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0

    def send(
            self,
            prompt: str,
            max_tokens: int,
            stream_mode: bool = False,
            system_prompt: str = None,
            ai_name: str = None,
            user_name: str = None
    ):
        """
        Call OpenAI API for chat

        :param prompt: prompt (user message)
        :param max_tokens: max output tokens
        :param stream_mode: stream mode
        :param system_prompt: system prompt (optional)
        :param ai_name: AI name
        :param user_name: user name
        :return: response or stream chunks
        """
        client = self.window.core.gpt.get_client()
        model = self.window.core.gpt.get_model('chat',  allow_change=False)

        # build chat messages
        messages = self.build(prompt, system_prompt=system_prompt, ai_name=ai_name, user_name=user_name)
        msg_tokens = self.window.core.tokens.from_messages(messages, self.window.core.config.get('model'))
        max_model_tokens = self.window.core.models.get_num_ctx(self.window.core.config.get('model'))

        # check if max tokens not exceeded
        if msg_tokens + int(max_tokens) > max_model_tokens:
            max_tokens = max_model_tokens - msg_tokens - 1
            if max_tokens < 1:
                max_tokens = 1

        response = client.chat.completions.create(
            messages=messages,
            model=model,
            max_tokens=int(max_tokens),
            temperature=self.window.core.config.get('temperature'),
            top_p=self.window.core.config.get('top_p'),
            frequency_penalty=self.window.core.config.get('frequency_penalty'),
            presence_penalty=self.window.core.config.get('presence_penalty'),
            stream=stream_mode,
        )
        return response

    def build(
            self,
            input_prompt: str,
            system_prompt: str = None,
            ai_name: str = None,
            user_name: str = None
    ) -> list:
        """
        Build chat messages list

        :param input_prompt: prompt (user input)
        :param system_prompt: system prompt (optional)
        :param ai_name: AI name
        :param user_name: username
        :return: messages list
        """
        messages = []

        # tokens config
        model = self.window.core.config.get('model')
        model_id = self.window.core.models.get_id(model)
        mode = self.window.core.config.get('mode')

        used_tokens = self.window.core.tokens.from_user(input_prompt, system_prompt)  # threshold and extra included
        max_tokens = self.window.core.config.get('max_total_tokens')
        model_ctx = self.window.core.models.get_num_ctx(model_id)

        # fit to max model tokens
        if max_tokens > model_ctx:
            max_tokens = model_ctx

        # input tokens: reset
        self.reset_tokens()

        # names fallback
        if ai_name is None or ai_name == "":
            ai_name = "assistant"
        if user_name is None or user_name == "":
            user_name = "user"

        # append system prompt
        if system_prompt is not None and system_prompt != "":
            messages.append({"role": "system", "content": system_prompt})

        # append messages from context (memory)
        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_prompt_items(model_id, mode, used_tokens, max_tokens)
            for item in items:
                # input
                if item.input is not None and item.input != "":
                    messages.append({"role": "system", "name": user_name, "content": item.input})

                # output
                if item.output is not None and item.output != "":
                    messages.append({"role": "system", "name": ai_name, "content": item.output})

        # append current prompt
        messages.append({"role": "user", "content": str(input_prompt)})

        # input tokens: update
        self.input_tokens += self.window.core.tokens.from_messages(messages, model_id)

        return messages

    def reset_tokens(self):
        """Reset input tokens counter"""
        self.input_tokens = 0

    def get_used_tokens(self) -> int:
        """
        Get input tokens counter

        :return: input tokens
        """
        return self.input_tokens
