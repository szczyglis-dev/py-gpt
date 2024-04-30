#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.30 04:00:00                  #
# ================================================== #

from openai import OpenAI

from pygpt_net.item.ctx import CtxItem

from .assistants import Assistants
from .chat import Chat
from .completion import Completion
from .image import Image
from .store import Store
from .summarizer import Summarizer
from .vision import Vision


class Gpt:
    def __init__(self, window=None):
        """
        OpenAI API wrapper core

        :param window: Window instance
        """
        self.window = window
        self.assistants = Assistants(window)
        self.chat = Chat(window)
        self.completion = Completion(window)
        self.image = Image(window)
        self.store = Store(window)
        self.summarizer = Summarizer(window)
        self.vision = Vision(window)

    def get_client(self) -> OpenAI:
        """
        Return OpenAI client

        :return: OpenAI client
        """
        args = {
            "api_key": self.window.core.config.get('api_key'),
            "organization": self.window.core.config.get('organization_key'),
        }
        if self.window.core.config.has('api_endpoint'):
            endpoint = self.window.core.config.get('api_endpoint')
            if endpoint:
                args["base_url"] = endpoint
        return OpenAI(**args)

    def call(self, **kwargs) -> bool:
        """
        Call OpenAI API

        :param kwargs: Keyword arguments
        :return: result
        """
        mode = kwargs.get("mode", None)
        prompt = kwargs.get("prompt", "")
        stream = kwargs.get("stream", False)
        model = kwargs.get("model", None)  # model instance
        system_prompt = kwargs.get("system_prompt", "")
        assistant_id = kwargs.get("assistant_id", "")
        tools_outputs = kwargs.get("tools_outputs", [])

        ctx = kwargs.get("ctx", CtxItem())
        ai_name = ctx.output_name
        thread_id = ctx.thread

        # prepare max tokens
        max_tokens = self.window.core.config.get('max_output_tokens')

        model_id = None
        if model is not None:
            model_id = model.id

        # check max output tokens
        if max_tokens > model.tokens:
            max_tokens = model.tokens

        # minimum 1 token is required
        if max_tokens < 1:
            max_tokens = 1

        response = None
        used_tokens = 0
        kwargs['max_tokens'] = max_tokens  # append max output tokens to kwargs

        file_ids = self.window.controller.files.uploaded_ids  # uploaded files IDs

        # get response
        if mode == "completion":
            response = self.completion.send(**kwargs)
            used_tokens = self.completion.get_used_tokens()

        elif mode == "chat":
            response = self.chat.send(**kwargs)
            used_tokens = self.chat.get_used_tokens()

        elif mode == "image":
            return self.image.generate(**kwargs)  # return here, async handled

        elif mode == "vision":
            response = self.vision.send(**kwargs)
            used_tokens = self.vision.get_used_tokens()
            images = self.vision.get_attachments()  # dict -> key: id, value: path
            urls = self.vision.get_urls()  # list

            # store sent images in ctx
            if len(images) > 0:
                ctx.images = self.window.core.filesystem.make_local_list(list(images.values()))
            if len(urls) > 0:
                ctx.images = urls
                ctx.urls = urls

        elif mode == "assistant":
            # check if assistant is already running and has tools outputs, then submit them, async handled
            if ctx.run_id is not None and len(tools_outputs) > 0:
                self.assistants.worker.tools_submit(
                    ctx,
                    model_id,
                    tools_outputs,  # list of tools outputs
                )
            else:
                # if not running, then send msg and create new assistant run, async handled
                self.assistants.worker.msg_send(
                    ctx,
                    thread_id,
                    assistant_id,
                    model_id,
                    file_ids,
                    prompt,
                    system_prompt,
                )
            return True  # if assistant mode then return here, will be handled async

        # if stream
        if stream:
            ctx.stream = response
            ctx.set_output("", ai_name)  # set empty output
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
            if response.choices[0]:
                if response.choices[0].message.content:
                    output = response.choices[0].message.content.strip()
                elif response.choices[0].message.tool_calls:
                    ctx.tool_calls = self.window.core.command.unpack_tool_calls(
                        response.choices[0].message.tool_calls
                    )

        ctx.set_output(output, ai_name)
        ctx.set_tokens(
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )
        return True

    def quick_call(self, **kwargs) -> str:
        """
        Quick call OpenAI API with custom prompt

        :param kwargs: keyword arguments
        :return: response content
        """
        prompt = kwargs.get("prompt", "")
        system_prompt = kwargs.get("system_prompt", None)
        max_tokens = kwargs.get("max_tokens", 500)
        temperature = kwargs.get("temperature", 0.0)
        model = kwargs.get("model", None)
        if model is None:
            model = self.window.core.models.from_defaults()

        client = self.get_client()
        messages = []
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = client.chat.completions.create(
                messages=messages,
                model=model.id,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )
            return response.choices[0].message.content
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error in GPT quick call: " + str(e))

    def stop(self):
        """Stop OpenAI API"""
        pass
