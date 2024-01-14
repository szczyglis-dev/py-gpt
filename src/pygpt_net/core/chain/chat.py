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

from langchain.schema import SystemMessage, HumanMessage, AIMessage


class Chat:
    def __init__(self, window=None):
        """
        Langchain Wrapper

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0

    def send(self, input_prompt: str, stream_mode: bool = False, system_prompt: str = None, ai_name: str = None,
             user_name: str = None):
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
        model = self.window.core.models.get(self.window.core.config.get('model'))
        if 'provider' in model.langchain:
            provider = model.langchain['provider']
            if provider in self.window.core.llm.llms:
                try:
                    # init
                    self.window.core.llm.llms[provider].init(
                        self.window, model, "langchain", "chat")
                    # get LLM provider instance
                    llm = self.window.core.llm.llms[provider].chat(
                        self.window, model, stream_mode)
                except Exception as e:
                    self.window.core.debug.log(e)

        # if no LLM here then raise exception
        if llm is None:
            raise Exception("Invalid LLM")

        messages = self.build(input_prompt, system_prompt=system_prompt, ai_name=ai_name, user_name=user_name)
        if stream_mode:
            return llm.stream(messages)
        else:
            return llm.invoke(messages)

    def build(self, input_prompt: str, system_prompt: str = None, ai_name: str = None, user_name: str = None) -> list:
        """
        Build chat messages list

        :param input_prompt: prompt
        :param system_prompt: system prompt (optional)
        :param ai_name: AI name (optional)
        :param user_name: username (optional)
        :return: list of messages
        """
        messages = []

        # tokens config
        model = self.window.core.config.get('model')
        model_id = self.window.core.models.get_id(model)

        # input tokens: reset
        self.reset_tokens()

        # append initial (system) message
        if system_prompt is not None and system_prompt != "":
            messages.append(SystemMessage(content=system_prompt))

        # append messages from context (memory)
        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_all_items()
            for item in items:
                # input
                if item.input is not None and item.input != "":
                    messages.append(HumanMessage(content=item.input))
                # output
                if item.output is not None and item.output != "":
                    messages.append(AIMessage(content=item.output))

        # append current prompt
        messages.append(HumanMessage(content=str(input_prompt)))

        # input tokens: update
        self.input_tokens += self.window.core.tokens.from_langchain_messages(messages, model_id)

        return messages

    def reset_tokens(self):
        """Reset input tokens counter"""
        self.input_tokens = 0

    def get_used_tokens(self) -> int:
        """Get input tokens counter"""
        return self.input_tokens


