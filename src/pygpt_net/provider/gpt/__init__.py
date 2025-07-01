#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.01 01:00:00                  #
# ================================================== #
import base64

from httpx_socks import SyncProxyTransport

from openai import OpenAI, DefaultHttpxClient

from pygpt_net.core.types import (
    MODE_ASSISTANT,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_IMAGE,
    MODE_VISION,
    MODE_RESEARCH,
)
from pygpt_net.core.bridge.context import BridgeContext

from .audio import Audio
from .assistants import Assistants
from .chat import Chat
from .completion import Completion
from .image import Image
from .responses import Responses
from .store import Store
from .summarizer import Summarizer
from .vision import Vision
from pygpt_net.item.model import ModelItem


class Gpt:
    def __init__(self, window=None):
        """
        OpenAI API wrapper core

        :param window: Window instance
        """
        self.window = window
        self.assistants = Assistants(window)
        self.audio = Audio(window)
        self.chat = Chat(window)
        self.completion = Completion(window)
        self.image = Image(window)
        self.responses = Responses(window)
        self.store = Store(window)
        self.summarizer = Summarizer(window)
        self.vision = Vision(window)

    def get_client(
            self,
            mode: str = MODE_CHAT,
            model: ModelItem = None
    ) -> OpenAI:
        """
        Return OpenAI client

        :param mode: Mode
        :param model: Model
        :return: OpenAI client
        """
        args = {
            "api_key": self.window.core.config.get('api_key'),
            "organization": self.window.core.config.get('organization_key'),
        }
        # api endpoint
        if self.window.core.config.has('api_endpoint'):
            endpoint = self.window.core.config.get('api_endpoint')
            if endpoint:
                args["base_url"] = endpoint
        # proxy
        if self.window.core.config.has('api_proxy'):
            proxy = self.window.core.config.get('api_proxy')
            if proxy:
                transport = SyncProxyTransport.from_url(proxy)
                args["http_client"] = DefaultHttpxClient(
                    transport=transport,
                )

        # update client args by mode and model
        args = self.window.core.models.prepare_client_args(args, mode, model)
        return OpenAI(**args)

    def call(self, context: BridgeContext, extra: dict = None) -> bool:
        """
        Call OpenAI API

        :param context: Bridge context
        :param extra: Extra arguments
        :return: result
        """
        mode = context.mode
        prompt = context.prompt
        stream = context.stream
        model = context.model  # model instance (item, not id)
        system_prompt = context.system_prompt
        assistant_id = context.assistant_id
        tools_outputs = context.tools_outputs
        max_tokens = context.max_tokens  # max output tokens

        ctx = context.ctx
        ai_name = ctx.output_name
        thread_id = ctx.thread  # from ctx

        # --- Responses API ---- /beta/
        use_responses_api = False

        # get model id
        model_id = None
        if model is not None:
            model_id = model.id
            if max_tokens > model.tokens:  # check max output tokens
                max_tokens = model.tokens

            if model.is_gpt():
                if (mode in [MODE_CHAT, MODE_RESEARCH]
                        and self.window.core.config.get('api_use_responses', False)):
                    use_responses_api = True  # use responses API for chat mode, only OpenAI models

        ctx.use_responses_api = use_responses_api  # set in context

        response = None
        used_tokens = 0
        context.max_tokens = max_tokens  # update max output tokens
        file_ids = context.file_ids  # uploaded files IDs (assistant mode only)

        # completion
        if mode == MODE_COMPLETION:
            response = self.completion.send(
                context=context,
                extra=extra,
            )
            used_tokens = self.completion.get_used_tokens()

        # chat, audio (OpenAI) | research (Perplexity)
        elif mode in [
            MODE_CHAT,
            MODE_AUDIO,
            MODE_RESEARCH
        ]:
            # responses API
            if use_responses_api:
                response = self.responses.send(
                    context=context,
                    extra=extra,
                )
                used_tokens = self.responses.get_used_tokens()
            else:
                # chat completion API
                response = self.chat.send(
                    context=context,
                    extra=extra,
                )
                if hasattr(response, "citations"):
                    if response.citations:
                        ctx.urls = response.citations
                used_tokens = self.chat.get_used_tokens()

            self.vision.append_images(ctx)  # append images to ctx if provided

        # image
        elif mode == MODE_IMAGE:
            return self.image.generate(
                context=context,
                extra=extra,
            )  # return here, async handled

        # vision
        elif mode == MODE_VISION:
            response = self.vision.send(
                context=context,
                extra=extra,
            )
            used_tokens = self.vision.get_used_tokens()
            self.vision.append_images(ctx)  # append images to ctx if provided

        # assistants
        elif mode == MODE_ASSISTANT:
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
            ctx.stream = response  # generator
            ctx.set_output("", ai_name)  # set empty output
            ctx.input_tokens = used_tokens  # get from input tokens calculation
            return True

        if response is None:
            return False

        # check for errors
        if "error" in response:
            print("Error in GPT response: " + str(response["error"]))
            return False

        # get output text from response (not-stream mode)
        output = ""
        if mode == MODE_COMPLETION:
            output = response.choices[0].text.strip()
        elif mode in [
            MODE_CHAT, 
            MODE_VISION, 
            MODE_RESEARCH
        ]:
            if use_responses_api:
                if response.output_text:
                    output = response.output_text.strip()
                if response.output:
                    ctx.tool_calls = self.window.core.command.unpack_tool_calls_responses(
                        response.output,
                    )
            else:
                if response.choices[0]:
                    print(response.choices[0].message)
                    if response.choices[0].message.content:
                        output = response.choices[0].message.content.strip()
                    elif response.choices[0].message.tool_calls:
                        ctx.tool_calls = self.window.core.command.unpack_tool_calls(
                            response.choices[0].message.tool_calls,
                        )
        # audio
        elif mode in [MODE_AUDIO]:
            if response.choices[0]:
                if response.choices[0].message and response.choices[0].message.audio:
                    ctx.audio_output = response.choices[0].message.audio.data
                    ctx.audio_id = response.choices[0].message.audio.id
                    ctx.audio_expires_ts = response.choices[0].message.audio.expires_at
                    ctx.is_audio = True
                    output = response.choices[0].message.audio.transcript  # from transcript
                    self.chat.audio_prev_expires_ts = ctx.audio_expires_ts
                    self.chat.audio_prev_id = ctx.audio_id
                elif response.choices[0].message and not response.choices[0].message.audio:
                    output = response.choices[0].message.content
                    ctx.audio_id = self.chat.audio_prev_id
                    ctx.audio_expires_ts = self.chat.audio_prev_expires_ts
                if response.choices[0].message.tool_calls:
                    ctx.tool_calls = self.window.core.command.unpack_tool_calls(
                        response.choices[0].message.tool_calls,
                    )

        ctx.set_output(output, ai_name)

        if not use_responses_api:
            ctx.set_tokens(
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            )
        else:
            ctx.set_tokens(
                response.usage.input_tokens,
                response.usage.output_tokens,
            )
            if mode == MODE_CHAT:
                # if image generation call in responses API
                image_data = [
                    output.result
                    for output in response.output
                    if output.type == "image_generation_call"
                ]
                if image_data:
                    img_path = self.window.core.image.gen_unique_path(ctx)
                    image_base64 = image_data[0]
                    with open(img_path, "wb") as f:
                        f.write(base64.b64decode(image_base64))
                    ctx.images = [img_path]
        return True

    def quick_call(self, context: BridgeContext, extra: dict = None) -> str:
        """
        Quick call OpenAI API with custom prompt

        :param context: Bridge context
        :param extra: Extra arguments
        :return: response content
        """
        mode = context.mode
        prompt = context.prompt
        system_prompt = context.system_prompt
        max_tokens = context.max_tokens
        temperature = context.temperature
        model = context.model
        if model is None:
            model = self.window.core.models.from_defaults()

        client = self.get_client(mode, model)
        messages = []
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        additional_kwargs = {}
        if max_tokens > 0:
            additional_kwargs["max_tokens"] = max_tokens
        
        try:
            response = client.chat.completions.create(
                messages=messages,
                model=model.id,
                temperature=temperature,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                **additional_kwargs,
            )
            return response.choices[0].message.content
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error in GPT quick call: " + str(e))

    def stop(self):
        """Stop OpenAI API"""
        pass
