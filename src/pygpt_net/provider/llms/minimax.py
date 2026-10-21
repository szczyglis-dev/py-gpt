#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# ================================================== #

from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class MiniMaxLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "minimax"
        self.name = "MiniMax"
        self.type = [MODE_LLAMA_INDEX]

    def setup(self) -> dict:
        return {
            "openai_compatible": True,
            "settings": {
                "api_key": {
                    "type": "str",
                    "default": "",
                    "secret": True,
                    "urls": {"API Keys": "https://platform.minimax.io"},
                },
                "api_base": {
                    "type": "str",
                    "default": "https://api.minimax.io/v1",
                },
            },
        }

    def llama(self, window, model: ModelItem, stream: bool = False):
        """Use the same provider and per-model settings as direct Chat."""
        from llama_index.llms.openai_like import OpenAILike

        args = self.prepare_openai_compatible_args(window, model)
        args.setdefault("is_chat_model", True)
        args.setdefault("is_function_calling_model", bool(model.tool_calls))
        args.setdefault("context_window", model.ctx)
        reasoning_effort = window.core.models.get_reasoning_effort(model)
        if reasoning_effort:
            additional_kwargs = dict(args.get("additional_kwargs") or {})
            additional_kwargs["reasoning_effort"] = reasoning_effort
            args["additional_kwargs"] = additional_kwargs
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        self.log_llama_create(window, model, args, "OpenAILike")
        return OpenAILike(**args)

    def get_models(self, window) -> list[dict]:
        """Offer current text models without changing saved/custom models."""
        return [
            {
                "id": model_id,
                "name": model_id,
                "ctx": 1000000,
                "tokens": 524288 if model_id == "MiniMax-M3.1-Flash" else 0,
                "input": ["text", "image", "video"],
                "tool_calls": True,
                "reasoning_effort": model_id == "MiniMax-M3.1-Flash",
            }
            for model_id in ("MiniMax-M3.1-Flash", "MiniMax-M3")
        ]
