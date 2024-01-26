#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.26 18:00:00                  #
# ================================================== #

from pygpt_net.item.ctx import CtxItem


class Chat:
    def __init__(self, window=None):
        """
        Chat wrapper

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0

    def send(self, **kwargs):
        """
        Call OpenAI API for chat

        :param kwargs: keyword arguments
        :return: response or stream chunks
        """
        # get kwargs
        ctx = kwargs.get("ctx", CtxItem())
        prompt = kwargs.get("prompt", "")
        stream = kwargs.get("stream", False)
        max_tokens = kwargs.get("max_tokens", 200)
        system_prompt = kwargs.get("system_prompt", "")
        user_name = ctx.input_name  # from ctx
        ai_name = ctx.output_name  # from ctx
        model = kwargs.get("model", None)
        client = self.window.core.gpt.get_client()

        # build chat messages
        messages = self.build(
            prompt=prompt,
            system_prompt=system_prompt,
            ai_name=ai_name,
            user_name=user_name,
            model=model,
        )
        msg_tokens = self.window.core.tokens.from_messages(
            messages,
            model.id,
        )
        # check if max tokens not exceeded
        if msg_tokens + int(max_tokens) > model.ctx:
            max_tokens = model.ctx - msg_tokens - 1
            if max_tokens < 1:
                max_tokens = 1

        response = client.chat.completions.create(
            messages=messages,
            model=model.id,
            max_tokens=int(max_tokens),
            temperature=self.window.core.config.get('temperature'),
            top_p=self.window.core.config.get('top_p'),
            frequency_penalty=self.window.core.config.get('frequency_penalty'),
            presence_penalty=self.window.core.config.get('presence_penalty'),
            stream=stream,
        )
        return response

    def build(self, **kwargs) -> list:
        """
        Build list of chat messages

        :param kwargs: keyword arguments
        :return: messages list
        """
        prompt = kwargs.get("prompt", "")
        system_prompt = kwargs.get("system_prompt", None)
        user_name = kwargs.get("user_name", None)
        ai_name = kwargs.get("ai_name", None)
        model = kwargs.get("model", None)
        messages = []

        # tokens config
        mode = self.window.core.config.get('mode')
        used_tokens = self.window.core.tokens.from_user(
            prompt,
            system_prompt,
        )  # threshold and extra included
        max_tokens = self.window.core.config.get('max_total_tokens')

        # fit to max model tokens
        if max_tokens > model.ctx:
            max_tokens = model.ctx

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
            items = self.window.core.ctx.get_prompt_items(
                model.id,
                mode,
                used_tokens,
                max_tokens,
            )
            for item in items:
                # input
                if item.input is not None and item.input != "":
                    messages.append({"role": "system", "name": user_name, "content": item.input})

                # output
                if item.output is not None and item.output != "":
                    messages.append({"role": "system", "name": ai_name, "content": item.output})

        # append current prompt
        messages.append({"role": "user", "content": str(prompt)})

        # input tokens: update
        self.input_tokens += self.window.core.tokens.from_messages(
            messages,
            model.id,
        )
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
