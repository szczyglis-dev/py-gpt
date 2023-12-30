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

from langchain.schema import SystemMessage, HumanMessage, AIMessage

from .chat import Chat
from .completion import Completion
from pygpt_net.item.ctx import CtxItem


class Chain:
    def __init__(self, window=None):
        """
        Langchain Wrapper

        :param window: Window instance
        """
        self.window = window
        self.chat = Chat(window)
        self.completion = Completion(window)
        self.ai_name = None
        self.user_name = None
        self.system_prompt = None
        self.attachments = {}
        self.llms = {}

    def register(self, id, llm):
        """
        Register LLM

        :param id: LLM id
        :param llm: LLM object
        """
        self.llms[id] = llm

    def call(self, prompt, ctx, stream_mode=False):
        """
        Call LLM with Langchain

        :param prompt: input text
        :param ctx: context (CtxItem)
        :param stream_mode: stream mode
        :return: result
        :rtype: bool
        """
        model_config = self.window.core.models.get(self.window.core.config.get('model'))
        response = None
        used_tokens = 0
        mode = 'chat'

        # get available modes
        if 'mode' in model_config.langchain:
            if 'chat' in model_config.langchain['mode']:
                mode = 'chat'
            elif 'completion' in model_config.langchain['mode']:
                mode = 'completion'

        try:
            if mode == 'chat':
                response = self.chat.send(prompt, stream_mode, system_prompt=self.system_prompt,
                                          ai_name=self.ai_name,  user_name=self.user_name)
                used_tokens = self.chat.get_used_tokens()
            elif mode == 'completion':
                response = self.completion.send(prompt, stream_mode, system_prompt=self.system_prompt,
                                                ai_name=self.ai_name,  user_name=self.user_name)
                used_tokens = self.completion.get_used_tokens()

        except Exception as e:
            self.window.core.debug.log(e)
            raise e  # re-raise to window

        # if async mode (stream)
        if stream_mode:
            ctx.stream = response
            ctx.input_tokens = used_tokens  # get from input tokens calculation
            ctx.set_output("", self.ai_name)
            return True

        if response is None:
            return False

        # get output
        output = None
        if mode == 'chat':
            output = response.content
        elif mode == 'completion':
            output = response

        # store context (memory)
        ctx.set_output(output, self.ai_name)

        return True
