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

from typing import Any, List, Dict, Optional, Sequence

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms import (
    CompletionResponse,
    CompletionResponseGen,
    CustomLLM,
    LLMMetadata,
)
from llama_index.core.llms.callbacks import llm_completion_callback
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.llms.base import BaseLLM


class LiteLLMIndex(CustomLLM):
    """LlamaIndex CustomLLM that routes to 100+ providers via litellm.completion()."""

    model_name: str = "openai/gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 1024
    api_key: Optional[str] = None
    api_base: Optional[str] = None

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            model_name=self.model_name,
            num_output=self.max_tokens,
        )

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        import litellm

        completion_kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            # drop_params silently drops provider-unsupported kwargs
            # to prevent cross-provider errors
            "drop_params": True,
        }
        if self.api_key:
            completion_kwargs["api_key"] = self.api_key
        if self.api_base:
            completion_kwargs["api_base"] = self.api_base

        response = litellm.completion(**completion_kwargs)
        text = response.choices[0].message.content or ""
        return CompletionResponse(text=text, raw=response.model_dump())

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        import litellm

        completion_kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True,
            "drop_params": True,
        }
        if self.api_key:
            completion_kwargs["api_key"] = self.api_key
        if self.api_base:
            completion_kwargs["api_base"] = self.api_base

        def gen() -> CompletionResponseGen:
            text = ""
            stream = litellm.completion(**completion_kwargs)
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", "") or ""
                text += content
                yield CompletionResponse(
                    delta=content, text=text, raw=chunk.model_dump()
                )

        return gen()


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
        args = self.parse_args(model.llama_index, window)
        model_name = args.pop("model", model.id)
        temperature = float(args.pop("temperature", 0.7))
        max_tokens = int(args.pop("max_tokens", 1024))
        api_key = args.pop("api_key", "")
        api_base = args.pop("api_base", "")
        return LiteLLMIndex(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key or None,
            api_base=api_base or None,
        )
