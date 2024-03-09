#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.09 18:00:00                  #
# ================================================== #

from pygpt_net.item.ctx import CtxItem


class Completion:
    def __init__(self, window=None):
        """
        Completion wrapper

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0

    def send(self, **kwargs):
        """
        Call OpenAI API for completion

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
        model_id = model.id

        # build prompt message
        message = self.build(
            prompt=prompt,
            system_prompt=system_prompt,
            ai_name=ai_name,
            user_name=user_name,
            model=model,
        )

        # check if max tokens not exceeded
        available_tokens = model.ctx - self.input_tokens
        if available_tokens < max_tokens:
            max_tokens = available_tokens

        # prepare stop word if user_name is set
        stop = ""
        if user_name is not None and user_name != '':
            stop = [user_name + ':']

        client = self.window.core.gpt.get_client()
        # fix for deprecated OpenAI davinci models
        if model_id.startswith('text-davinci'):
            model_id = 'gpt-3.5-turbo-instruct'

        response = client.completions.create(
            prompt=message,
            model=model_id,
            max_tokens=int(max_tokens),
            temperature=self.window.core.config.get('temperature'),
            top_p=self.window.core.config.get('top_p'),
            frequency_penalty=self.window.core.config.get('frequency_penalty'),
            presence_penalty=self.window.core.config.get('presence_penalty'),
            stop=stop,
            stream=stream,
        )
        return response

    def build(self, **kwargs) -> str:
        """
        Build completion string

        :param kwargs: keyword arguments
        :return: message string (parsed with context)
        """
        prompt = kwargs.get("prompt", "")
        system_prompt = kwargs.get("system_prompt", None)
        user_name = kwargs.get("user_name", None)
        ai_name = kwargs.get("ai_name", None)
        model = kwargs.get("model", None)
        message = ""

        # tokens config
        used_tokens = self.window.core.tokens.from_user(
            prompt,
            system_prompt,
        )
        max_tokens = self.window.core.config.get('max_total_tokens')

        # fit to max model ctx tokens
        if max_tokens > model.ctx:
            max_tokens = model.ctx

        # input tokens: reset
        self.reset_tokens()

        if system_prompt is not None and system_prompt != "":
            message += system_prompt

        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_prompt_items(
                model.id,
                "completion",
                used_tokens,
                max_tokens,
            )
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
            message += "\n" + user_name + ": " + str(prompt)
            message += "\n" + ai_name + ":"
        else:
            message += "\n" + str(prompt)

        # input tokens: update
        self.input_tokens += self.window.core.tokens.from_text(
            message,
            model.id,
        )
        return message

    def reset_tokens(self):
        """Reset input tokens counter"""
        self.input_tokens = 0

    def get_used_tokens(self) -> int:
        """
        Get input tokens counter

        :return: input tokens
        """
        return self.input_tokens
