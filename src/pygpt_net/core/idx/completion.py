#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 12:48:00                  #
# ================================================== #

from typing import Any, Dict, List, Optional

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.types import MODE_COMPLETION
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


class Completion:
    """Plain-text completion routed through the configured LlamaIndex provider."""

    def __init__(self, window=None):
        self.window = window
        self.input_tokens = 0

    def call(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Execute a LlamaIndex completion without converting PyGPT mode to chat."""
        model = context.model
        if model is None or not isinstance(model, ModelItem):
            raise Exception("Model config not provided")

        ctx = context.ctx
        if ctx is None:
            ctx = CtxItem()

        prompt = self.build(
            prompt=context.prompt,
            system_prompt=context.system_prompt,
            model=model,
            history=context.history,
            ai_name=ctx.output_name,
            user_name=ctx.input_name,
        )

        llm = self.window.core.idx.llm.get_completion(
            model=model,
            stream=context.stream,
        )
        if llm is None:
            raise Exception("Invalid LlamaIndex completion provider")

        if context.stream:
            response = llm.stream_complete(prompt)
            ctx.stream = response
            ctx.input_tokens = self.input_tokens
            ctx.set_output("", ctx.output_name)
            return True

        response = llm.complete(prompt)
        if response is None:
            return False

        output = getattr(response, "text", None)
        if output is None:
            output = str(response)
        else:
            output = str(output)

        ctx.input_tokens = self.input_tokens
        ctx.output_tokens = self.window.core.tokens.from_text(output, model.id)
        ctx.set_output(output, ctx.output_name)
        return True

    def build(
            self,
            prompt: str,
            system_prompt: str,
            model: ModelItem,
            history: Optional[List[CtxItem]] = None,
            ai_name: Optional[str] = None,
            user_name: Optional[str] = None,
    ) -> str:
        """Build the same plain-text conversation prompt used by native completion."""
        message = ""
        used_tokens = self.window.core.tokens.from_user(prompt, system_prompt)
        max_ctx_tokens = self.window.core.config.get("max_total_tokens")

        if model.ctx > 0 and (max_ctx_tokens <= 0 or max_ctx_tokens > model.ctx):
            max_ctx_tokens = model.ctx

        self.input_tokens = 0

        if system_prompt:
            message += str(system_prompt)

        if self.window.core.config.get("use_context"):
            items = self.window.core.ctx.get_history(
                history,
                model.id,
                MODE_COMPLETION,
                used_tokens,
                max_ctx_tokens,
            )
            for item in items:
                has_names = bool(item.input_name and item.output_name)
                if item.final_input:
                    if has_names:
                        message += f"\n{item.input_name}: {item.final_input}"
                    else:
                        message += f"\n{item.final_input}"
                if item.final_output:
                    if has_names:
                        message += f"\n{item.output_name}: {item.final_output}"
                    else:
                        message += f"\n{item.final_output}"

        if user_name and ai_name:
            message += f"\n{user_name}: {prompt}"
            message += f"\n{ai_name}:"
        else:
            message += f"\n{prompt}"

        self.input_tokens = self.window.core.tokens.from_text(message, model.id)
        return message
