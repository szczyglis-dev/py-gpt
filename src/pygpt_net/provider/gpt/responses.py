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

import json
import time
from typing import Optional, Dict, Any, List

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_VISION,
    MODE_AUDIO,
    OPENAI_DISABLE_TOOLS,
    OPENAI_REMOTE_TOOL_DISABLE_CODE_INTERPRETER,
    OPENAI_REMOTE_TOOL_DISABLE_IMAGE,
    OPENAI_REMOTE_TOOL_DISABLE_WEB_SEARCH,
)
from pygpt_net.core.bridge.context import BridgeContext, MultimodalContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem

from pygpt_net.item.attachment import AttachmentItem


class Responses:
    def __init__(self, window=None):
        """
        Responses API wrapper

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0
        self.audio_prev_id = None
        self.audio_prev_expires_ts = None
        self.prev_response_id = None

    def send(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
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

        client = self.window.core.gpt.get_client(mode, model)

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

        # tools / functions
        tools = []
        if functions is not None and isinstance(functions, list):
            for function in functions:
                if str(function['name']).strip() == '' or function['name'] is None:
                    continue
                params = {}
                if function['params'] is not None and function['params'] != "":
                    params = json.loads(function['params'])  # unpack JSON from string
                tools.append({
                    "type": "function",
                    "name": function['name'],
                    "parameters": params,
                    "description": function['desc'],
                })

        # extra arguments, o3 only
        if model.extra and "reasoning_effort" in model.extra:
            response_kwargs['reasoning'] = {}
            response_kwargs['reasoning']['effort'] = model.extra["reasoning_effort"]

        if model.id in OPENAI_DISABLE_TOOLS:
            tools = []  # disable tools for specific models

        # extend tools with external tools
        if (not model.id.startswith("o1")
                and not model.id.startswith("o3")):  # o1, o3, o4 models do not support tools

            if not model.id in OPENAI_REMOTE_TOOL_DISABLE_WEB_SEARCH:
                if self.window.core.config.get("remote_tools.web_search", False):
                    tools.append({"type": "web_search_preview"})

            if not model.id in OPENAI_REMOTE_TOOL_DISABLE_CODE_INTERPRETER:
                if self.window.core.config.get("remote_tools.code_interpreter", False):
                    tools.append({
                        "type": "code_interpreter",
                        "container": {
                            "type": "auto"
                        }
                    })
            if not model.id in OPENAI_REMOTE_TOOL_DISABLE_IMAGE:
                if self.window.core.config.get("remote_tools.image", False):
                    tool = {"type": "image_generation"}
                    if stream:
                        tool["partial_images"] = 1  # required for streaming
                    tools.append(tool)

        # tool calls are not supported for o1-mini and o1-preview
        if (model.id is not None
                and model.id not in ["o1-mini", "o1-preview"]):
            if len(tools) > 0:
                response_kwargs['tools'] = tools

        # attach previous response ID if available
        if self.prev_response_id:
            response_kwargs['previous_response_id'] = self.prev_response_id

        response = client.responses.create(
            input=messages,
            model=model.id,
            stream=stream,
            **response_kwargs,
        )

        # store previous response ID
        if not stream and response:
            ctx.msg_id = response.id

        return response

    def build(
            self,
            prompt: str,
            system_prompt: str,
            model: ModelItem,
            history: Optional[List[CtxItem]] = None,
            attachments: Optional[Dict[str, AttachmentItem]] = None,
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
        self.prev_response_id = None  # reset
        is_tool_output = False  # reset

        # tokens config
        mode = MODE_CHAT
        tool_call_native_enabled = self.window.core.config.get('func_call.native', False)
        allowed_system = True
        if (model.id is not None
                and model.id in ["o1-mini", "o1-preview"]):
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

        # append system prompt
        if allowed_system:
            if system_prompt is not None and system_prompt != "":
                messages.append({"role": "developer", "content": system_prompt})

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
                        "content": item.final_input,
                    })

                # output
                if item.final_output is not None and item.final_output != "":
                    msg = {
                        "role": "assistant",
                        "content": item.final_output,
                    }
                    # append previous audio ID
                    if MODE_AUDIO in model.mode:
                        if item.audio_id:
                            # at first check expires_at - expired audio throws error in API
                            current_timestamp = time.time()
                            audio_timestamp = int(item.audio_expires_ts) if item.audio_expires_ts else 0
                            if audio_timestamp and audio_timestamp > current_timestamp:
                                msg["audio"] = {
                                    "id": item.audio_id
                                }
                        elif self.audio_prev_id:
                            current_timestamp = time.time()
                            audio_timestamp = int(self.audio_prev_expires_ts) if self.audio_prev_expires_ts else 0
                            if audio_timestamp and audio_timestamp > current_timestamp:
                                msg["audio"] = {
                                    "id": self.audio_prev_id
                                }
                    messages.append(msg)

                    # ---- tool output ----
                    is_tool_output = False  # reset tool output flag
                    is_last_item = item == items[-1] if items else False
                    if is_last_item and tool_call_native_enabled and item.extra and isinstance(item.extra, dict):
                        if "tool_calls" in item.extra and isinstance(item.extra["tool_calls"], list):
                            for tool_call in item.extra["tool_calls"]:
                                if "function" in tool_call:
                                    if "call_id" not in tool_call or "name" not in tool_call["function"]:
                                        continue
                                    if tool_call["call_id"] and tool_call["function"]["name"]:
                                        if "tool_output" in item.extra and isinstance(item.extra["tool_output"], list):
                                            for tool_output in item.extra["tool_output"]:
                                                if ("cmd" in tool_output
                                                        and tool_output["cmd"] == tool_call["function"]["name"]):
                                                    msg = {
                                                        "type": "function_call_output",
                                                        "call_id": tool_call["call_id"],
                                                        "output": str(tool_output),
                                                    }
                                                    is_tool_output = True
                                                    messages.append(msg)
                                                    break
                                                elif "result" in tool_output:
                                                    # if result is present, append it as function call output
                                                    msg = {
                                                        "type": "function_call_output",
                                                        "call_id": tool_call["call_id"],
                                                        "output": str(tool_output["result"]),
                                                    }
                                                    is_tool_output = True
                                                    messages.append(msg)
                                                    break

                # --- previous message ID ---
                if (item.msg_id
                        and ((item.cmds is None or len(item.cmds) == 0) or is_tool_output)):  # if no cmds before or tool output
                    self.prev_response_id = item.msg_id  # previous response ID to use in current input

        # use vision and audio if available in current model
        if not is_tool_output:  # append current prompt only if not tool output
            content = str(prompt)
            if model.is_image_input():
                content = self.window.core.gpt.vision.build_content(
                    content=content,
                    attachments=attachments,
                    responses_api=True,
                )
            if model.is_audio_input():
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
