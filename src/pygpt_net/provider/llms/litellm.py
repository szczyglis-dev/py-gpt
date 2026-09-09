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
    ChatMessage,
    ChatResponse,
    ChatResponseGen,
    CompletionResponse,
    CompletionResponseGen,
    CustomLLM,
    LLMMetadata,
)
from llama_index.core.llms.callbacks import llm_chat_callback, llm_completion_callback
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

    def _build_kwargs(self, messages: List[Dict[str, str]], stream: bool = False) -> Dict[str, Any]:
        """Build the shared litellm.completion kwargs from current settings."""
        completion_kwargs: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            # drop_params silently drops provider-unsupported kwargs
            # to prevent cross-provider errors
            "drop_params": True,
        }
        if stream:
            completion_kwargs["stream"] = True
        if self.api_key:
            completion_kwargs["api_key"] = self.api_key
        if self.api_base:
            completion_kwargs["api_base"] = self.api_base
        return completion_kwargs

    @staticmethod
    def _coerce_role(role: Any) -> str:
        """Normalize a message role (str or enum) to a string."""
        if isinstance(role, str):
            return role
        value = getattr(role, "value", None)
        return value if isinstance(value, str) else "user"

    @staticmethod
    def _get_messages(prompt: str, kwargs: Any) -> List[Dict[str, str]]:
        """Build litellm messages, preferring provided chat history."""
        messages = kwargs.get("messages") or kwargs.get("chat_messages")
        if messages:
            out = []
            for m in messages:
                if isinstance(m, ChatMessage):
                    out.append({
                        "role": LiteLLMIndex._coerce_role(m.role),
                        "content": m.content,
                    })
                elif isinstance(m, dict):
                    out.append({
                        "role": LiteLLMIndex._coerce_role(m.get("role", "user")),
                        "content": m.get("content", ""),
                    })
                else:
                    content = getattr(m, "content", str(m))
                    role = getattr(m, "role", None)
                    out.append({
                        "role": LiteLLMIndex._coerce_role(role),
                        "content": content,
                    })
            return out
        return [{"role": "user", "content": prompt}]

    @staticmethod
    def _chat_messages_to_litellm(
        messages: Sequence[ChatMessage],
    ) -> List[Dict[str, str]]:
        return [
            {
                "role": LiteLLMIndex._coerce_role(msg.role),
                "content": msg.content,
            }
            for msg in messages
        ]

    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        import litellm

        completion_kwargs = self._build_kwargs(self._get_messages(prompt, kwargs))

        response = litellm.completion(**completion_kwargs)
        text = response.choices[0].message.content or ""
        return CompletionResponse(text=text, raw=response.model_dump())

    @llm_completion_callback()
    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        import litellm

        completion_kwargs = self._build_kwargs(
            self._get_messages(prompt, kwargs), stream=True
        )

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

    @llm_chat_callback()
    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        import litellm

        completion_kwargs = self._build_kwargs(
            self._chat_messages_to_litellm(messages)
        )

        response = litellm.completion(**completion_kwargs)
        content = response.choices[0].message.content or ""
        return ChatResponse(
            message=ChatMessage(role="assistant", content=content),
            raw=response.model_dump(),
        )

    @llm_chat_callback()
    def stream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        import litellm

        completion_kwargs = self._build_kwargs(
            self._chat_messages_to_litellm(messages), stream=True
        )

        def gen() -> ChatResponseGen:
            stream = litellm.completion(**completion_kwargs)
            text = ""
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", "") or ""
                text += content
                yield ChatResponse(
                    message=ChatMessage(role="assistant", content=text),
                    delta=content,
                    raw=chunk.model_dump(),
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
