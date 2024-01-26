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
        Chat with LLM

        :param kwargs: keyword arguments
        :return: LLM response
        """
        # get kwargs
        prompt = kwargs.get("prompt", "")
        system_prompt = kwargs.get("system_prompt", "")
        stream = kwargs.get("stream", False)
        user_name = kwargs.get("user_name", None)
        ai_name = kwargs.get("ai_name", None)
        model = kwargs.get("model", None)

        llm = None
        if 'provider' in model.langchain:
            provider = model.langchain['provider']
            if provider in self.window.core.llm.llms:
                try:
                    # init
                    self.window.core.llm.llms[provider].init(
                        self.window,
                        model,
                        "langchain",
                        "completion",
                    )
                    # get LLM provider instance
                    llm = self.window.core.llm.llms[provider].completion(
                        self.window,
                        model,
                        stream,
                    )
                except Exception as e:
                    self.window.core.debug.log(e)
                    raise e
        if llm is None:
            raise Exception("Invalid LLM")

        message = self.build(
            prompt=prompt,
            system_prompt=system_prompt,
            ai_name=ai_name,
            user_name=user_name,
            model=model,
        )
        if stream:
            return llm.stream(message)
        else:
            return llm.invoke(message)

    def build(self, **kwargs) -> str:
        """
        Build completion string

        :param kwargs: keyword arguments
        :return: message string (parsed with context)
        """
        # get kwargs
        prompt = kwargs.get("prompt", "")
        system_prompt = kwargs.get("system_prompt", "")
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
                "langchain",
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

        :return: input tokens counter
        """
        return self.input_tokens
