#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : RheagalFire                          #
# Updated Date: 2026.04.24 00:00:00                  #
# ================================================== #

from __future__ import annotations
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.llms.base import BaseLLM




__all__ = ["LiteLLMProvider", "LiteLLMIndex"]

class LiteLLMProvider(BaseLLM):
    """PyGPT LLM provider that routes to 100+ providers via LiteLLM."""

    def __init__(self, *args, **kwargs):
        super(LiteLLMProvider, self).__init__(*args, **kwargs)
        self.id = "litellm"
        self.name = "LiteLLM"
        self.type = [MODE_LLAMA_INDEX]

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        from .litellm_index import LiteLLMIndex

        args = self.prepare_openai_compatible_args(window, model)
        model_name = args.pop("model", model.id)
        temperature = float(args.pop("temperature", 0.7))
        max_tokens = int(args.pop("max_tokens", 1024))
        api_key = args.pop("api_key", "")
        api_base = args.pop("api_base", "")
        reasoning_effort = window.core.models.get_reasoning_effort(model)
        constructor_args = {
            "model_name": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "api_key": api_key or None,
            "api_base": api_base or None,
            "reasoning_effort": reasoning_effort,
        }
        self.log_llama_create(window, model, constructor_args, "LiteLLMIndex")
        return LiteLLMIndex(**constructor_args)

def __getattr__(name):
    # Backward-compatible lazy export; the LlamaIndex adapter is loaded only
    # when callers explicitly request it.
    if name == "LiteLLMIndex":
        from .litellm_index import LiteLLMIndex
        return LiteLLMIndex
    raise AttributeError(name)

