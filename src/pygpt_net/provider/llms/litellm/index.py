#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : RheagalFire                          #
# Updated Date: 2026.09.29 13:00:00                  #
# ================================================== #

"""Thin PyGPT metadata adapter for LlamaIndex's native LiteLLM LLM.

All request handling (chat/completion, streaming, multimodal message blocks,
function/tool calls and async methods) is provided by
``llama_index.llms.litellm.LiteLLM``. This subclass only keeps PyGPT's model
metadata authoritative for context size and the user-configurable tool-calling
flag, which is important for custom/unknown LiteLLM model IDs.
"""

from typing import Optional

from llama_index.core.base.llms.types import LLMMetadata
from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.llms.litellm import LiteLLM
from llama_index.llms.litellm.utils import (
    is_function_calling_model,
    openai_modelname_to_contextsize,
)


class LiteLLMIndex(LiteLLM):
    """Native LlamaIndex LiteLLM with PyGPT model metadata overrides."""

    _pygpt_context_window: Optional[int] = PrivateAttr(default=None)
    _pygpt_tool_calls: Optional[bool] = PrivateAttr(default=None)

    def __init__(
            self,
            *args,
            pygpt_context_window: Optional[int] = None,
            pygpt_tool_calls: Optional[bool] = None,
            **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._pygpt_context_window = pygpt_context_window
        self._pygpt_tool_calls = pygpt_tool_calls

    @property
    def metadata(self) -> LLMMetadata:
        """Return native LiteLLM metadata with explicit PyGPT overrides.

        Avoid asking LiteLLM to rediscover function-calling support when PyGPT
        already has an explicit model capability flag. This also keeps custom
        model IDs usable when they are absent from LiteLLM's bundled catalog.
        """
        context_window = self._pygpt_context_window
        if not context_window:
            context_window = openai_modelname_to_contextsize(self._get_model_name())

        tool_calls = self._pygpt_tool_calls
        if tool_calls is None:
            try:
                tool_calls = is_function_calling_model(
                    self._get_model_name(),
                    self._custom_llm_provider,
                )
            except Exception:
                tool_calls = False

        return LLMMetadata(
            context_window=context_window,
            num_output=self.max_tokens or -1,
            is_chat_model=True,
            is_function_calling_model=bool(tool_calls),
            model_name=self.model,
        )


__all__ = ["LiteLLMIndex"]
