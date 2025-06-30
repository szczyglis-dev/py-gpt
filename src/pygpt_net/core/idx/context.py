#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 20:00:00                  #
# ================================================== #
import json
from typing import Optional, List

from llama_index.core.llms import ChatMessage, MessageRole

from pygpt_net.item.ctx import CtxItem


class Context:
    def __init__(self, window=None):
        """
        Context core

        :param window: Window instance
        """
        self.window = window

    def get_messages(
            self,
            input_prompt: str,
            system_prompt: str,
            history: Optional[List[CtxItem]] = None,
            multimodal: bool = False,
            prev_message = None,
            allow_native_tool_calls: bool = False
    ):
        """
        Get messages from db

        :param input_prompt: input prompt
        :param system_prompt: system prompt
        :param history: history
        :param multimodal: multimodal flag
        :param prev_message: previous message
        :param allow_native_tool_calls: allow native tool calls
        :return: Messages
        """
        messages = []

        # tokens config
        model = self.window.core.config.get('model')
        model_id = self.window.core.models.get_id(model)
        mode = self.window.core.config.get('mode')

        used_tokens = self.window.core.tokens.from_user(input_prompt, system_prompt)  # threshold and extra included
        max_tokens = self.window.core.config.get('max_total_tokens')
        model_ctx = self.window.core.models.get_num_ctx(model_id)

        # fit to max model tokens
        if max_tokens > model_ctx:
            max_tokens = model_ctx

        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_history(
                history,
                model_id,
                mode,
                used_tokens,
                max_tokens,
            )
            for item in items:
                # input
                if item.final_input is not None and item.final_input != "":
                    messages.append(ChatMessage(
                        role=MessageRole.USER,
                        content=item.final_input
                    ))
                # output
                if item.final_output is not None and item.final_output != "":
                    msg = ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=item.final_output
                    )
                    messages.append(msg)

                # ---- if tool output ----
                is_last_item = item == items[-1] if items else False
                if (is_last_item
                        and prev_message
                        and allow_native_tool_calls
                        and item.extra
                        and isinstance(item.extra, dict)):
                    if "tool_calls" in item.extra and isinstance(item.extra["tool_calls"], list):
                        for tool_call in item.extra["tool_calls"]:
                            if "function" in tool_call:
                                if "id" not in tool_call or "name" not in tool_call["function"]:
                                    continue
                                if tool_call["id"] and tool_call["function"]["name"]:
                                    if "tool_output" in item.extra and isinstance(item.extra["tool_output"], list):
                                        for tool_output in item.extra["tool_output"]:
                                            if ("cmd" in tool_output
                                                    and tool_output["cmd"] == tool_call["function"]["name"]):
                                                last_msg = messages[-1] if messages else None
                                                if last_msg and last_msg.role == "assistant":
                                                    if prev_message:
                                                        last_msg = prev_message  # prev message with tool calls
                                                        messages[-1] = last_msg

                                                msg = ChatMessage(
                                                    role=MessageRole.TOOL,
                                                    content=str(tool_output),
                                                    additional_kwargs={"tool_call_id": tool_call["id"]}
                                                )
                                                messages.append(msg)
                                                break
                                            elif "result" in tool_output:
                                                # if result is present, append it as function call output
                                                last_msg = messages[-1] if messages else None
                                                if last_msg and last_msg.role == "assistant":
                                                    if prev_message:
                                                        last_msg = prev_message  # prev message with tool calls
                                                        messages[-1] = last_msg

                                                msg = ChatMessage(
                                                    role=MessageRole.TOOL,
                                                    content=str(tool_output["result"]),
                                                    additional_kwargs={"tool_call_id": tool_call["id"]}
                                                )
                                                messages.append(msg)
                                                break


        return messages

    def add_user(self, query: str) -> ChatMessage:
        """
        Add user message

        :param query: input query
        """
        return ChatMessage(
            role=MessageRole.USER,
            content=query,
        )

    def add_system(self, prompt: str) -> ChatMessage:
        """
        Add system message to db

        :param prompt: system prompt
        """
        return ChatMessage(
            role=MessageRole.SYSTEM,
            content=prompt,
        )
