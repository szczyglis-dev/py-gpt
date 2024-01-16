#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.16 04:00:00                  #
# ================================================== #

import json

from openai import OpenAI

from .assistants import Assistants
from .chat import Chat
from .completion import Completion
from .summarizer import Summarizer
from .vision import Vision
from pygpt_net.item.ctx import CtxItem
from ..dispatcher import Event


class Gpt:
    def __init__(self, window=None):
        """
        GPT wrapper core

        :param window: Window instance
        """
        self.window = window
        self.assistants = Assistants(window)
        self.chat = Chat(window)
        self.completion = Completion(window)
        self.summarizer = Summarizer(window)
        self.vision = Vision(window)
        self.ai_name = None
        self.user_name = None
        self.system_prompt = None
        self.attachments = {}
        self.thread_id = None  # assistant thread id
        self.assistant_id = None  # assistant id

    def get_client(self):
        """
        Return OpenAI client

        :return: OpenAI client
        :rtype: OpenAI
        """
        return OpenAI(
            api_key=self.window.core.config.get('api_key'),
            organization=self.window.core.config.get('organization_key'),
        )

    def get_model(self, mode: str, allow_change: bool = True) -> str:
        """
        Get model ID

        :param mode: Mode
        :param allow_change: Allow change model
        :return: Model ID
        """
        model = str(self.window.core.config.get('model'))
        model_id = self.window.core.models.get_id(model)
        if allow_change:
            event = Event('model.before', {
                'mode': mode,
                'model': model_id,  # ID is provided to event, NOT the key in items! TODO: pass as object
            })
            self.window.core.dispatcher.dispatch(event)
            model_id = event.data['model']
        return model_id

    def call(self, prompt: str, ctx: CtxItem = None, stream_mode: bool = False) -> bool:
        """
        Call OpenAI API

        :param prompt: text input (user prompt)
        :param ctx: context item (CtxItem)
        :param stream_mode: stream mode, default: False
        :return: result
        """
        # prepare max tokens
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')
        model_id = self.window.core.models.get_id(model)
        model_tokens = self.window.core.models.get_tokens(model_id)
        max_tokens = self.window.core.config.get('max_output_tokens')

        # check max output tokens
        if max_tokens > model_tokens:
            max_tokens = model_tokens

        # minimum 1 token is required
        if max_tokens < 1:
            max_tokens = 1

        response = None
        used_tokens = 0

        # event: mode.before
        event = Event('mode.before', {
            'value': mode,
            'prompt': prompt,
        })
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)
        mode = event.data['value']

        # get response
        if mode == "completion":
            response = self.completion.send(prompt, max_tokens, stream_mode, system_prompt=self.system_prompt,
                                            ai_name=self.ai_name, user_name=self.user_name)
            used_tokens = self.completion.get_used_tokens()
        elif mode == "chat":
            response = self.chat.send(prompt, max_tokens, stream_mode, system_prompt=self.system_prompt,
                                      ai_name=self.ai_name, user_name=self.user_name)
            used_tokens = self.chat.get_used_tokens()
        elif mode == "vision":
            response = self.vision.send(prompt, max_tokens, stream_mode, system_prompt=self.system_prompt,
                                        attachments=self.attachments)
            used_tokens = self.vision.get_used_tokens()
            images = self.vision.get_attachments()
            urls = self.vision.get_urls()

            # store sent images in ctx
            if len(images) > 0:
                ctx.images = list(images.values())
            if len(urls) > 0:
                ctx.images = urls
                ctx.urls = urls

        elif mode == "assistant":
            response = self.assistants.msg_send(self.thread_id, prompt)
            if response is not None:
                ctx.msg_id = response.id
                run = self.assistants.run_create(self.thread_id, self.assistant_id, self.system_prompt)
                if run is not None:
                    ctx.run_id = run.id
            return True  # if assistant then return here

        # if async mode (stream)
        if stream_mode:
            ctx.stream = response
            ctx.set_output("", self.ai_name)  # set empty output
            ctx.input_tokens = used_tokens  # get from input tokens calculation
            return True

        if response is None:
            return False

        # check for errors
        if "error" in response:
            print("Error in GPT response: " + str(response["error"]))
            return False

        # get output text from response
        output = ""
        if mode == "completion":
            output = response.choices[0].text.strip()
        elif mode == "chat" or mode == "vision":
            output = response.choices[0].message.content.strip()

        ctx.set_output(output, self.ai_name)
        ctx.set_tokens(response.usage.prompt_tokens, response.usage.completion_tokens)

        return True

    def quick_call(self, prompt: str, sys_prompt: str, append_context: bool = False,
                   max_tokens: int = 500, model: str = "gpt-3.5-turbo-1106", temp: float = 0.0) -> str:
        """
        Quick call OpenAI API with custom prompt

        :param prompt: user input (prompt)
        :param sys_prompt: system input (prompt)
        :param append_context: append context (memory)
        :param max_tokens: max output tokens
        :param model: model name
        :param temp: temperature
        :return: response content
        """
        client = self.get_client()

        if append_context:
            messages = self.chat.build(prompt, sys_prompt)
        else:
            messages = []
            messages.append({"role": "system", "content": sys_prompt})
            messages.append({"role": "user", "content": prompt})
        try:
            response = client.chat.completions.create(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temp,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                stop=None,
            )
            return response.choices[0].message.content
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error in GPT custom call: " + str(e))

    def stop(self):
        """Stop OpenAI API"""
        pass
