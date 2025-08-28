#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.19 07:00:00                  #
# ================================================== #

from openai import OpenAI

from pygpt_net.core.types import (
    MODE_ASSISTANT,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_IMAGE,
    MODE_VISION,
    MODE_RESEARCH,
    MODE_COMPUTER,
)
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.model import ModelItem

from .audio import Audio
from .assistants import Assistants
from .chat import Chat
from .completion import Completion
from .computer import Computer
from .container import Container
from .image import Image
from .remote_tools import RemoteTools
from .responses import Responses
from .store import Store
from .summarizer import Summarizer
from .tools import Tools
from .vision import Vision


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
        self.container = Container(window)
        self.computer = Computer(window)
        self.image = Image(window)
        self.remote_tools = RemoteTools(window)
        self.responses = Responses(window)
        self.store = Store(window)
        self.summarizer = Summarizer(window)
        self.tools = Tools(window)
        self.vision = Vision(window)
        self.client = None
        self.locked = False
        self.last_client_args = None  # last client args used, for debug purposes

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
        # update client args by mode and model
        args = self.window.core.models.prepare_client_args(mode, model)
        if self.client is None or self.last_client_args != args:
            if self.client is not None:
                try:
                    self.client.close()  # close previous client if exists
                except Exception as e:
                    self.window.core.debug.log(e)
                    print("Error closing previous GPT client:", e)
            self.client = OpenAI(**args)
        self.last_client_args = args
        return self.client

    def call(self, context: BridgeContext, extra: dict = None) -> bool:
        """
        Call OpenAI API

        :param context: Bridge context
        :param extra: Extra arguments
        :return: result
        """
        mode = context.mode
        parent_mode = context.parent_mode  # real mode (global)
        prompt = context.prompt
        stream = context.stream
        model = context.model  # model instance (item, not id)
        system_prompt = context.system_prompt
        assistant_id = context.assistant_id
        tools_outputs = context.tools_outputs
        max_tokens = context.max_tokens  # max output tokens
        is_expert_call = context.is_expert_call
        preset = context.preset  # PresetItem, used for expert calls

        ctx = context.ctx
        ai_name = ctx.output_name
        thread_id = ctx.thread  # from ctx

        # --- Responses API ----
        use_responses_api = self.responses.is_enabled(model, mode, parent_mode, is_expert_call, preset)
        ctx.use_responses_api = use_responses_api  # set in context

        # get model id
        model_id = None
        if model is not None:
            model_id = model.id
            if max_tokens > model.tokens:  # check max output tokens
                max_tokens = model.tokens

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
            MODE_RESEARCH,
            MODE_COMPUTER,
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

        # ------- streaming response -------

        if stream:
            ctx.stream = response  # generator
            ctx.set_output("", ai_name)  # set empty output
            ctx.input_tokens = used_tokens  # get from input tokens calculation
            return True  # <-- end here, will be handled in chat stream controller

        # ------- non-streaming response -------

        if response is None:
            return False

        # check for errors
        if "error" in response:
            print("Error in GPT response: " + str(response["error"]))
            return False

        ctx.ai_name = ai_name

        # post-unpack response data, like: output text, tool calls, images, file citations, etc.
        if not use_responses_api:
            self.chat.unpack_response(mode, response, ctx)
        else:
            self.responses.unpack_response(mode, response, ctx)

        return True

    def quick_call(self, context: BridgeContext, extra: dict = None) -> str:
        """
        Quick call OpenAI API with custom prompt

        :param context: Bridge context
        :param extra: Extra arguments
        :return: response content
        """
        # if normal request call then redirect
        if context.request:
            context.stream = False
            context.mode = "chat"  # fake mode for redirect
            self.locked = True
            self.call(context, extra)
            self.locked = False
            return context.ctx.output

        self.locked = True
        ctx = context.ctx
        mode = context.mode
        prompt = context.prompt
        system_prompt = context.system_prompt
        max_tokens = context.max_tokens
        temperature = context.temperature
        functions = context.external_functions
        history = context.history
        model = context.model
        if model is None:
            model = self.window.core.models.from_defaults()

        client = self.get_client(mode, model)
        messages = []
        messages.append({"role": "system", "content": system_prompt})

        if history:
            for item in history:
                messages.append({
                    "role": "user",
                    "content": str(item.final_input)
                })
                messages.append({
                    "role": "assistant",
                    "content": str(item.final_output)
                })
        messages.append({"role": "user", "content": prompt})
        additional_kwargs = {}
        # if max_tokens > 0:
            # additional_kwargs["max_tokens"] = max_tokens

        # tools / functions
        tools = self.window.core.gpt.tools.prepare(model, functions)
        if len(tools) > 0 and "disable_tools" not in extra:
            additional_kwargs["tools"] = tools
        
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
            # extract tool calls
            if ctx and response.choices[0].message.tool_calls:
                ctx.tool_calls = self.window.core.command.unpack_tool_calls(
                    response.choices[0].message.tool_calls,
                )
            return response.choices[0].message.content
        except Exception as e:
            self.window.core.debug.log(e)
            print("Error in GPT quick call: " + str(e))
        finally:
            self.locked = False

    def stop(self):
        """On global event stop"""
        pass

    def close(self):
        """Close OpenAI client"""
        if self.locked:
            return
        if self.client is not None:
            try:
                pass
                # self.client.close()
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error closing GPT client:", e)
