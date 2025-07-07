#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

from typing import Optional, Dict, Any

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_COMPLETION,
)

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem

from .chat import Chat
from .completion import Completion


class Chain:
    def __init__(self, window=None):
        """
        Langchain wrapper core

        :param window: Window instance
        """
        self.window = window
        self.chat = Chat(window)
        self.completion = Completion(window)

    def call(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Call LLM using Langchain

        :param context: Bridge context
        :param extra: Extra arguments
        """
        prompt = context.prompt
        system_prompt = context.system_prompt
        stream = context.stream
        model = context.model
        ctx = context.ctx

        if ctx is None:
            ctx = CtxItem()  # create empty context

        user_name = ctx.input_name  # from ctx
        ai_name = ctx.output_name  # from ctx
        response = None
        used_tokens = 0
        sub_mode = MODE_CHAT

        # get available sub-modes
        if 'mode' in model.langchain:
            if MODE_CHAT in model.langchain['mode']:
                sub_mode = MODE_CHAT
            elif MODE_COMPLETION in model.langchain['mode']:
                sub_mode = MODE_COMPLETION

        try:
            if sub_mode == MODE_CHAT:
                response = self.chat.send(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=model,
                    history=context.history,
                    stream=stream,
                    ai_name=ai_name,
                    user_name=user_name,
                )
                used_tokens = self.chat.get_used_tokens()
            elif sub_mode == MODE_COMPLETION:
                response = self.completion.send(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    model=model,
                    history=context.history,
                    stream=stream,
                    ai_name=ai_name,
                    user_name=user_name,
                )
                used_tokens = self.completion.get_used_tokens()

        except Exception as e:
            self.window.core.debug.log(e)
            raise e  # re-raise to window

        # if stream mode, store stream
        if stream:
            ctx.stream = response
            ctx.input_tokens = used_tokens  # get from input tokens calculation
            ctx.set_output("", ai_name)
            return True

        if response is None:
            return False

        # get output
        output = None
        if sub_mode == MODE_CHAT:
            output = response.content
        elif sub_mode == MODE_COMPLETION:
            output = response

        # store context
        ctx.set_output(output, ai_name)
        return True
