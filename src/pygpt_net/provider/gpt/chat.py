#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.01 17:00:00                  #
# ================================================== #

import json
import re

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


class Chat:
    def __init__(self, window=None):
        """
        Chat wrapper

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0

    def send(self, context: BridgeContext, extra: dict = None):
        """
        Call OpenAI API for chat

        :param context: Bridge context
        :param extra: Extra arguments
        :return: response or stream chunks
        """
        prompt = context.prompt
        stream = context.stream
        max_tokens = int(context.max_tokens or 0)
        system_prompt = context.system_prompt
        model = context.model
        functions = context.external_functions
        attachments = context.attachments

        ctx = context.ctx
        if ctx is None:
            ctx = CtxItem()  # create empty context
        user_name = ctx.input_name  # from ctx
        ai_name = ctx.output_name  # from ctx

        client = self.window.core.gpt.get_client()

        # build chat messages
        messages = self.build(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            history=context.history,
            attachments=attachments,
            ai_name=ai_name,
            user_name=user_name,
        )
        msg_tokens = self.window.core.tokens.from_messages(
            messages,
            model.id,
        )
        # check if max tokens not exceeded
        if max_tokens > 0:
            if msg_tokens + int(max_tokens) > model.ctx:
                max_tokens = model.ctx - msg_tokens - 1
                if max_tokens < 0:
                    max_tokens = 0

        # extra API kwargs
        response_kwargs = {}

        # tools / functions
        tools = []
        if functions is not None and isinstance(functions, list):
            for function in functions:
                if str(function['name']).strip() == '' or function['name'] is None:
                    continue
                params = {}
                if function['params'] is not None and function['params'] != "":
                    params = json.loads(function['params'])  # unpack JSON from string
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": function['name'],
                            "parameters": params,
                            "description": function['desc'],
                        }
                    }
                )
        if len(tools) > 0:
            response_kwargs['tools'] = tools
        if max_tokens > 0:
            response_kwargs['max_tokens'] = max_tokens

        response = client.chat.completions.create(
            messages=messages,
            model=model.id,
            temperature=self.window.core.config.get('temperature'),
            top_p=self.window.core.config.get('top_p'),
            frequency_penalty=self.window.core.config.get('frequency_penalty'),
            presence_penalty=self.window.core.config.get('presence_penalty'),
            stream=stream,
            **response_kwargs
        )
        return response

    def build(
            self,
            prompt: str,
            system_prompt: str,
            model: ModelItem,
            history: list = None,
            attachments: dict = None,
            ai_name: str = None,
            user_name: str = None
    ) -> list:
        """
        Build list of chat messages

        :param prompt: user prompt
        :param system_prompt: system prompt
        :param history: history
        :param model: model item
        :param attachments: attachments
        :param ai_name: AI name
        :param user_name: username
        :return: messages list
        """
        messages = []

        # tokens config
        mode = "chat"
        used_tokens = self.window.core.tokens.from_user(
            prompt,
            system_prompt,
        )  # threshold and extra included
        max_ctx_tokens = self.window.core.config.get('max_total_tokens')  # max context window

        # fit to max model tokens
        if max_ctx_tokens > model.ctx:
            max_ctx_tokens = model.ctx

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
            items = self.window.core.ctx.get_history(
                history,
                model.id,
                mode,
                used_tokens,
                max_ctx_tokens,
            )
            for item in items:
                # input
                if item.input is not None and item.input != "":
                    messages.append({"role": "system", "name": self.sanitize_name(user_name), "content": item.input})

                # output
                if item.output is not None and item.output != "":
                    messages.append({"role": "system", "name": self.sanitize_name(ai_name), "content": item.output})

        # use vision if available in current model
        content = str(prompt)
        if "vision" in model.mode:
            content = self.window.core.gpt.vision.build_content(prompt, attachments)

        # append current prompt
        messages.append({"role": "user", "content": content})

        # input tokens: update
        self.input_tokens += self.window.core.tokens.from_messages(
            messages,
            model.id,
        )
        return messages

    def sanitize_name(self, name: str) -> str:
        """
        Sanitize name

        :param name: name
        :return: sanitized name
        """
        if name is None:
            return ""
        # allowed characters: a-z, A-Z, 0-9, _, and -
        name = name.strip().lower()
        sanitized_name = re.sub(r'[^a-z0-9_-]', '_', name)
        return sanitized_name[:64]  # limit to 64 characters

    def reset_tokens(self):
        """Reset input tokens counter"""
        self.input_tokens = 0

    def get_used_tokens(self) -> int:
        """
        Get input tokens counter

        :return: input tokens
        """
        return self.input_tokens
