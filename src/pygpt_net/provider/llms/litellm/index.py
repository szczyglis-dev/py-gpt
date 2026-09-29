#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : RheagalFire                          #
# Updated Date: 2026.09.29 12:45:00                  #
# ================================================== #

from typing import Any, Dict, List, Optional, Sequence

from llama_index.core.llms import (
    ChatMessage,
    ImageBlock,
    TextBlock,
    ChatResponse,
    ChatResponseGen,
    CompletionResponse,
    CompletionResponseGen,
    CustomLLM,
    LLMMetadata,
)
from llama_index.core.llms.callbacks import llm_chat_callback, llm_completion_callback
from llama_index.core.constants import DEFAULT_CONTEXT_WINDOW

class LiteLLMIndex(CustomLLM):
    """LlamaIndex CustomLLM that routes to 100+ providers via litellm.completion()."""

    model_name: str = "openai/gpt-4o-mini"
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    reasoning_effort: Optional[str] = None
    completion_kwargs: Dict[str, Any] = {}

    @property
    def metadata(self) -> LLMMetadata:
        context_window = self.context_window
        if not context_window:
            # Prefer LiteLLM's model catalog when PyGPT has no context size.
            try:
                import litellm
                info = (getattr(litellm, "model_cost", {}) or {}).get(self.model_name, {})
                context_window = int(info.get("max_input_tokens") or info.get("max_tokens") or 0)
            except (TypeError, ValueError, AttributeError, ImportError):
                pass
        return LLMMetadata(
            model_name=self.model_name,
            num_output=self.max_tokens or -1,
            context_window=context_window or DEFAULT_CONTEXT_WINDOW,
        )

    def _build_kwargs(self, messages: List[Dict[str, Any]], stream: bool = False) -> Dict[str, Any]:
        """Build the shared litellm.completion kwargs from current settings."""
        completion_kwargs: Dict[str, Any] = {
            **self.completion_kwargs,
            "model": self.model_name,
            "messages": messages,
            # drop_params silently drops provider-unsupported kwargs
            # to prevent cross-provider errors
            "drop_params": True,
        }
        if self.temperature is not None:
            completion_kwargs["temperature"] = self.temperature
        if self.max_tokens is not None:
            completion_kwargs["max_tokens"] = self.max_tokens
        if stream:
            completion_kwargs["stream"] = True
        if self.api_key:
            completion_kwargs["api_key"] = self.api_key
        if self.api_base:
            completion_kwargs["api_base"] = self.api_base
        if self.reasoning_effort:
            completion_kwargs["reasoning_effort"] = self.reasoning_effort
        return completion_kwargs

    @staticmethod
    def _coerce_role(role: Any) -> str:
        """Normalize a message role (str or enum) to a string."""
        if isinstance(role, str):
            return role
        value = getattr(role, "value", None)
        return value if isinstance(value, str) else "user"

    @staticmethod
    def _content_to_litellm(message: ChatMessage) -> Any:
        """Convert LlamaIndex blocks to LiteLLM/OpenAI message content.

        LiteLLM accepts the OpenAI multimodal chat shape and translates it for
        the selected backend.  Keep plain text as a string for maximum
        compatibility, but preserve ImageBlock values whenever PyGPT has
        explicitly enabled image input for the current model.
        """
        blocks = list(getattr(message, "blocks", None) or [])
        if not blocks:
            return message.content or ""

        content = []
        has_image = False
        for block in blocks:
            if isinstance(block, TextBlock):
                content.append({"type": "text", "text": block.text or ""})
                continue
            if isinstance(block, ImageBlock):
                has_image = True
                if block.url:
                    url = str(block.url)
                else:
                    image_b64 = block.resolve_image(as_base64=True).read().decode("utf-8")
                    mime = getattr(block, "image_mimetype", None) or "image/png"
                    url = f"data:{mime};base64,{image_b64}"
                image_url = {"url": url}
                detail = getattr(block, "detail", None)
                if detail:
                    image_url["detail"] = detail
                content.append({"type": "image_url", "image_url": image_url})
                continue

            # LiteLLM chat completion is used here for text + image input.
            # Preserve the previous behavior for any unsupported LlamaIndex
            # block instead of serializing a provider-specific structure.
            text = getattr(block, "text", None)
            if text is not None:
                content.append({"type": "text", "text": str(text)})

        if not has_image:
            return "".join(
                item.get("text", "")
                for item in content
                if item.get("type") == "text"
            )
        return content

    @staticmethod
    def _message_to_litellm(message: ChatMessage) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "role": LiteLLMIndex._coerce_role(message.role),
            "content": LiteLLMIndex._content_to_litellm(message),
        }
        additional_kwargs = getattr(message, "additional_kwargs", None) or {}
        tool_call_id = additional_kwargs.get("tool_call_id")
        if tool_call_id:
            out["tool_call_id"] = tool_call_id
        return out

    @staticmethod
    def _get_messages(prompt: str, kwargs: Any) -> List[Dict[str, Any]]:
        """Build LiteLLM messages, preferring provided chat history."""
        messages = kwargs.get("messages") or kwargs.get("chat_messages")
        if messages:
            out = []
            for m in messages:
                if isinstance(m, ChatMessage):
                    out.append(LiteLLMIndex._message_to_litellm(m))
                elif isinstance(m, dict):
                    out.append({
                        **m,
                        "role": LiteLLMIndex._coerce_role(m.get("role", "user")),
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
    ) -> List[Dict[str, Any]]:
        return [LiteLLMIndex._message_to_litellm(msg) for msg in messages]

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
