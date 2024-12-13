#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 00:00:00                  #
# ================================================== #

import json
import time
from typing import Optional

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_VISION,
    MODE_AUDIO,
)
from pygpt_net.core.bridge.context import BridgeContext, MultimodalContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem

from .utils import sanitize_name

class Chat:
    def __init__(self, window=None):
        """
        Chat wrapper

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0

    def send(
            self,
            context: BridgeContext,
            extra: Optional[dict] = None
    ):
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
        mode = context.mode
        model = context.model
        functions = context.external_functions
        attachments = context.attachments
        multimodal_ctx = context.multimodal_ctx

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
            multimodal_ctx=multimodal_ctx,
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

        # tools / functions >>>>>>>>>> TMP DISABLED FOR AUDIO <<<<<<<<<<
        tools = []
        if mode not in [MODE_AUDIO]:
            if functions is not None and isinstance(functions, list):
                for function in functions:
                    if str(function['name']).strip() == '' or function['name'] is None:
                        continue
                    params = {}
                    if function['params'] is not None and function['params'] != "":
                        params = json.loads(function['params'])  # unpack JSON from string
                    tools.append({
                        "type": "function",
                        "function": {
                            "name": function['name'],
                            "parameters": params,
                            "description": function['desc'],
                        }
                    })

        # fix: o1 compatibility
        if model.id is not None and not model.id.startswith("o1"):
            response_kwargs['presence_penalty'] = self.window.core.config.get('presence_penalty')
            response_kwargs['frequency_penalty'] = self.window.core.config.get('frequency_penalty')
            response_kwargs['temperature'] = self.window.core.config.get('temperature')
            response_kwargs['top_p'] = self.window.core.config.get('top_p')
            if len(tools) > 0:
                response_kwargs['tools'] = tools

        if max_tokens > 0:
            if not model.id.startswith("o1"):
                response_kwargs['max_tokens'] = max_tokens
            else:
                response_kwargs['max_completion_tokens'] = max_tokens

        if model.id is not None and model.id.startswith("o1"):
            stream = False

        # audio mode
        if mode in [MODE_AUDIO]:
            stream = False
            voice_id = "alloy"
            tmp_voice = self.window.core.plugins.get_option("audio_output", "openai_voice")
            if tmp_voice:
                voice_id = tmp_voice
            response_kwargs["modalities"] = ["text", "audio"]
            response_kwargs["audio"] = {
                "voice": voice_id,
                "format": "wav"
            }

        response = client.chat.completions.create(
            messages=messages,
            model=model.id,
            stream=stream,
            **response_kwargs,
        )
        return response

    def build(
            self,
            prompt: str,
            system_prompt: str,
            model: ModelItem,
            history: Optional[list] = None,
            attachments: Optional[dict] = None,
            ai_name: Optional[str] = None,
            user_name: Optional[str] = None,
            multimodal_ctx: Optional[MultimodalContext] = None,
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
        :param multimodal_ctx: Multimodal context
        :return: messages list
        """
        messages = []

        # tokens config
        mode = MODE_CHAT
        allowed_system = True
        if model.id is not None and model.id.startswith("o1"):
            allowed_system = False

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
        if allowed_system:
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
                if item.final_input is not None and item.final_input != "":
                    messages.append({
                        "role": "user",
                        "name": sanitize_name(user_name),
                        "content": item.final_input,
                    })

                # output
                if item.final_output is not None and item.final_output != "":
                    msg = {
                        "role": "assistant",
                        "name": sanitize_name(ai_name),
                        "content": item.final_output,
                    }
                    # append previous audio ID
                    if MODE_AUDIO in model.mode and item.audio_id:
                        # at first check expires_at - expired audio throws error in API
                        current_timestamp = time.time()
                        audio_timestamp = int(item.audio_expires_ts) if item.audio_expires_ts else 0
                        if audio_timestamp and audio_timestamp > current_timestamp:
                            msg["audio"] = {
                                "id": item.audio_id
                            }
                    messages.append(msg)

        # use vision and audio if available in current model
        content = str(prompt)
        if MODE_VISION in model.mode:
            content = self.window.core.gpt.vision.build_content(
                content=content,
                attachments=attachments,
            )
        if MODE_AUDIO in model.mode:
            content = self.window.core.gpt.audio.build_content(
                content=content,
                multimodal_ctx=multimodal_ctx,
            )

        # append current prompt
        messages.append({
            "role": "user",
            "content": content,
        })

        # input tokens: update
        self.input_tokens += self.window.core.tokens.from_messages(
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

        :return: input tokens
        """
        return self.input_tokens
