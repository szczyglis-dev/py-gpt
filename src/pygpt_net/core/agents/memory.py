#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.05 16:00:00                  #
# ================================================== #

from typing import List, Dict, Tuple

from llama_index.core.llms import ChatMessage, MessageRole
from pygpt_net.core.bridge.context import BridgeContext


class Memory:

    def __init__(self, window=None):
        """
        Agent memory

        :param window: Window instance
        """
        self.window = window

    def prepare(
            self,
            context: BridgeContext
    ) -> List[ChatMessage]:
        """
        Prepare history for agent

        :param context: BridgeContext
        :return: list with history items
        """
        messages = []

        input_prompt = context.ctx.final_input
        history = context.history
        mode = context.mode
        model = context.model
        model_id = model.id

        # tokens config
        used_tokens = self.window.core.tokens.from_user(input_prompt, "")  # threshold and extra included
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
            # extract only input and output messages, skip step messages
            for item in items:
                if item.extra is not None and type(item.extra) == dict:
                    # agent input
                    if item.extra.get("agent_input", False):
                        if item.final_input is not None and item.final_input != "":
                            messages.append(ChatMessage(
                                role=MessageRole.USER,
                                content=item.final_input
                            ))
                    # agent output
                    if item.extra.get("agent_output", False):
                        if item.final_output is not None and item.final_output != "":
                            messages.append(ChatMessage(
                                role=MessageRole.ASSISTANT,
                                content=item.final_output
                            ))

        return messages

    def prepare_openai(
            self,
            context: BridgeContext
    ) -> Tuple[List[Dict], str]:
        """
        Prepare history for agent

        :param context: BridgeContext
        :return: list with history items
        :param msg_type: memory type, default is TYPE_LLAMA_INDEX
        """
        messages = []

        input_prompt = context.ctx.final_input
        history = context.history
        mode = context.mode
        model = context.model
        model_id = model.id
        previous_response_id = None

        # tokens config
        used_tokens = self.window.core.tokens.from_user(input_prompt, "")  # threshold and extra included
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
            # extract only input and output messages, skip step messages
            for item in items:
                # count if last item
                is_last_item = item is items[-1] if items else False
                if item.extra is not None and type(item.extra) == dict:
                    # agent input
                    if item.extra.get("agent_input", False):
                        if item.final_input is not None and item.final_input != "":
                            messages.append({
                                "role": "user",
                                "content": item.final_input,
                            })
                    # agent output
                    if item.extra.get("agent_output", False):
                        if item.final_output is not None and item.final_output != "":
                            messages.append({
                                "role": "assistant",
                                "content": item.final_output,
                            })

                # Continue the server-side response chain from the last history
                # item, unless project-context changes require a fresh chain.
                # project_context_reset is set when previously delivered shared
                # sources become unavailable or change; reusing the old response
                # ID would retain their old content in the server-side context.
                # Block that ID only while the current turn has no msg_id yet.
                # Once the current turn receives its own response ID, subsequent
                # agent calls may continue the new chain even though the reset
                # flag remains set for this turn. Without a reset, use the last
                # item's ID normally; an item without an ID cannot start a chain.
                if (is_last_item and item.msg_id is not None
                        and not ((getattr(context.ctx, "extra", None) or {}).get("project_context_reset")
                                 and not getattr(context.ctx, "msg_id", None))):
                    previous_response_id = item.msg_id

        return messages, previous_response_id
