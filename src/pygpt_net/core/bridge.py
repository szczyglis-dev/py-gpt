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

class Bridge:
    def __init__(self, window=None):
        """
        Mode and models bridge

        :param window: Window instance
        """
        self.window = window

    def call(self, **kwargs) -> bool:
        """
        Make call to provider

        :param kwargs: keyword arguments
        """
        allowed_model_change = ["vision"]

        # get kwargs
        ctx = kwargs.get("ctx", None)
        prompt = kwargs.get("prompt", None)
        mode = kwargs.get("mode", None)
        model = kwargs.get("model", None)  # model instance

        # inline: mode switch
        kwargs['parent_mode'] = mode  # store current (parent) mode
        mode = self.window.controller.mode.switch_inline(mode, ctx, prompt)
        kwargs['mode'] = mode

        # inline: model switch
        if mode in allowed_model_change:
            model = self.window.controller.model.switch_inline(mode, model)
            kwargs['model'] = model

        # Langchain
        if mode == "langchain":
            return self.window.core.chain.call(**kwargs)

        # Llama-index
        elif mode == "llama_index":
            return self.window.core.idx.chat.call(**kwargs)

        # OpenAI API, chat, completion, vision, image, etc.
        else:
            return self.window.core.gpt.call(**kwargs)

    def quick_call(self, **kwargs) -> str:
        """
        Make quick call to provider and get response content

        :param kwargs: keyword arguments
        :return: response content
        """
        return self.window.core.gpt.quick_call(**kwargs)
