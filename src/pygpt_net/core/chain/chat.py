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

from langchain.schema import SystemMessage, HumanMessage, AIMessage


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
                        "chat",
                    )
                    # get LLM provider instance
                    llm = self.window.core.llm.llms[provider].chat(
                        self.window,
                        model,
                        stream,
                    )
                except Exception as e:
                    self.window.core.debug.log(e)
                    raise e
                    # if no LLM here then raise exception
        if llm is None:
            raise Exception("Invalid LLM")

        messages = self.build(
            prompt=prompt,
            system_prompt=system_prompt,
            ai_name=ai_name,
            user_name=user_name,
            model=model,
        )
        if stream:
            return llm.stream(messages)
        else:
            return llm.invoke(messages)

    def build(self, **kwargs) -> list:
        """
        Build chat messages list

        :param kwargs: keyword arguments
        :return: list of messages
        """
        # get kwargs
        prompt = kwargs.get("prompt", "")
        system_prompt = kwargs.get("system_prompt", "")
        user_name = kwargs.get("user_name", None)  # unused
        ai_name = kwargs.get("ai_name", None)  # unused
        model = kwargs.get("model", None)
        messages = []

        # tokens
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

        # append initial (system) message
        if system_prompt is not None and system_prompt != "":
            messages.append(SystemMessage(content=system_prompt))

        # append messages from context (memory)
        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_prompt_items(
                model.id,
                "langchain",
                used_tokens,
                max_tokens,
            )
            for item in items:
                # input
                if item.input is not None and item.input != "":
                    messages.append(HumanMessage(content=item.input))
                # output
                if item.output is not None and item.output != "":
                    messages.append(AIMessage(content=item.output))

        # append current prompt
        messages.append(HumanMessage(content=str(prompt)))

        # input tokens: update
        self.input_tokens += self.window.core.tokens.from_langchain_messages(
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

        :return: input tokens counter
        """
        return self.input_tokens


