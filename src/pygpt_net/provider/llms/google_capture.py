#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from __future__ import annotations

import asyncio
import os
from typing import Any, Sequence

from google.genai import types
from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.llms.google_genai.utils import (
    adelete_uploaded_files,
    chat_from_gemini_response,
    delete_uploaded_files,
    prepare_chat_params,
)

from pygpt_net.provider.api.google.utils import extract_google_urls


# Google Search grounding currently returns opaque redirect URLs such as
# vertexaisearch.cloud.google.com/grounding-api-redirect/..., rather than the
# canonical source URLs expected by PyGPT's URL list. Keep capture disabled
# until canonical provider sources are available/normalized.
GOOGLE_CAPTURE_SOURCE_URLS = False


class PyGPTGoogleGenAI(GoogleGenAI):
    """GoogleGenAI with provider-artifact capture for PyGPT.

    LlamaIndex 0.14.x converts Google SDK chunks into ``ChatResponse`` objects.
    A final Gemini streaming chunk may contain grounding metadata but no text
    parts, and LlamaIndex intentionally does not yield such a chunk.  Capture
    Google Search/citation metadata at the SDK boundary so both Chat with Files
    and Agents v2 can persist source URLs reliably.
    """

    _pygpt_urls: list[str] = PrivateAttr(default_factory=list)
    _pygpt_remote_tools: list[Any] = PrivateAttr(default_factory=list)

    def __init__(self, *args, pygpt_remote_tools=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._pygpt_remote_tools = list(pygpt_remote_tools or [])

    @staticmethod
    def _is_vertex_runtime() -> bool:
        value = str(os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "")).strip().lower()
        return value not in ("", "0", "false", "no", "off")

    @staticmethod
    def _with_server_side_tool_invocations(tool_config):
        if tool_config is None:
            return types.ToolConfig(include_server_side_tool_invocations=True)
        if isinstance(tool_config, dict):
            data = dict(tool_config)
            data["include_server_side_tool_invocations"] = True
            return data
        try:
            tool_config.include_server_side_tool_invocations = True
            return tool_config
        except Exception:
            pass
        try:
            data = tool_config.model_dump(exclude_none=True)
        except Exception:
            data = {}
        data["include_server_side_tool_invocations"] = True
        return types.ToolConfig(**data)

    def _prepare_chat_with_tools(self, *args, **kwargs):
        """Merge Gemini built-ins with LlamaIndex function declarations.

        GoogleGenAI 0.14.23 stores configured built-ins in generation_config.
        During ``chat_with_tools`` that preconfigured list wins over the
        function declarations supplied by LlamaIndex.  Override only this
        request so both sets reach Gemini, while plain chat still keeps its
        normal provider-side tools.
        """
        prepared = super()._prepare_chat_with_tools(*args, **kwargs)
        if not self._pygpt_remote_tools:
            return prepared

        local_tools = prepared.get("tools") or []
        if not isinstance(local_tools, list):
            local_tools = [local_tools]
        prepared["tools"] = [*self._pygpt_remote_tools, *local_tools]

        # Clear the instance-level generation_config.tools for this request.
        # prepare_chat_params() otherwise prefers it and silently drops the
        # function declarations from prepared["tools"].
        override = prepared.get("generation_config") or {}
        if not isinstance(override, dict):
            try:
                override = override.model_dump(exclude_none=True)
            except Exception:
                override = {}
        else:
            override = dict(override)
        override["tools"] = None
        prepared["generation_config"] = override

        # Built-in + custom function calling requires tool-context circulation
        # in the Gemini Developer API. Do not add this Developer-API-only flag
        # for Vertex AI.
        if local_tools and not self._is_vertex_runtime():
            prepared["tool_config"] = self._with_server_side_tool_invocations(
                prepared.get("tool_config")
            )
        return prepared

    def _capture_urls(self, raw: Any) -> None:
        if not GOOGLE_CAPTURE_SOURCE_URLS:
            return
        try:
            urls = extract_google_urls(raw)
        except Exception:
            return
        if not urls:
            return
        seen = set(self._pygpt_urls)
        for url in urls:
            value = str(url or "").strip()
            if not value or value in seen:
                continue
            self._pygpt_urls.append(value)
            seen.add(value)

    def pop_pygpt_urls(self) -> list[str]:
        urls = list(self._pygpt_urls)
        self._pygpt_urls.clear()
        return urls

    def _chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        response = super()._chat(messages, **kwargs)
        self._capture_urls(getattr(response, "raw", None))
        return response

    async def _achat(
        self,
        messages: Sequence[ChatMessage],
        **kwargs: Any,
    ) -> ChatResponse:
        response = await super()._achat(messages, **kwargs)
        self._capture_urls(getattr(response, "raw", None))
        return response

    def _stream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any):
        """Mirror GoogleGenAI._stream_chat while capturing every SDK chunk."""
        generation_config = {
            **(self._generation_config or {}),
            **kwargs.pop("generation_config", {}),
        }
        params = {**kwargs, "generation_config": generation_config}
        next_msg, chat_kwargs, file_api_names = asyncio.run(
            prepare_chat_params(
                self.model,
                messages,
                self.file_mode,
                self._client,
                **params,
            )
        )
        chat = self._client.chats.create(**chat_kwargs)
        response = chat.send_message_stream(
            next_msg.parts if isinstance(next_msg, types.Content) else next_msg
        )

        def gen():
            try:
                content = []
                thought_signatures = []
                for raw_chunk in response:
                    # Capture before LlamaIndex filters chunks without content.parts.
                    self._capture_urls(raw_chunk)
                    candidates = getattr(raw_chunk, "candidates", None) or []
                    if not candidates:
                        continue
                    top_candidate = candidates[0]
                    response_content = getattr(top_candidate, "content", None)
                    parts = getattr(response_content, "parts", None) if response_content else None
                    if not parts:
                        continue
                    content_delta = "".join(
                        part.text
                        for part in parts
                        if getattr(part, "text", None) and not getattr(part, "thought", False)
                    )
                    llama_resp = chat_from_gemini_response(
                        raw_chunk,
                        existing_content=content,
                        thought_signatures=thought_signatures,
                    )
                    llama_resp.delta = llama_resp.delta or content_delta or ""
                    yield llama_resp
            finally:
                if self.file_mode in ("fileapi", "hybrid"):
                    delete_uploaded_files(file_api_names, self._client)

        return gen()

    async def _astream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any):
        """Mirror GoogleGenAI._astream_chat while capturing every SDK chunk."""
        generation_config = {
            **(self._generation_config or {}),
            **kwargs.pop("generation_config", {}),
        }
        params = {**kwargs, "generation_config": generation_config}
        next_msg, chat_kwargs, file_api_names = await prepare_chat_params(
            self.model,
            messages,
            self.file_mode,
            self._client,
            **params,
        )
        chat = self._client.aio.chats.create(**chat_kwargs)

        async def gen():
            try:
                content = []
                thought_signatures = []
                async for raw_chunk in await chat.send_message_stream(
                    next_msg.parts if isinstance(next_msg, types.Content) else next_msg
                ):
                    # Capture before LlamaIndex filters chunks without content.parts.
                    self._capture_urls(raw_chunk)
                    candidates = getattr(raw_chunk, "candidates", None) or []
                    if not candidates:
                        continue
                    top_candidate = candidates[0]
                    response_content = getattr(top_candidate, "content", None)
                    parts = getattr(response_content, "parts", None) if response_content else None
                    if not parts:
                        continue
                    content_delta = "".join(
                        part.text
                        for part in parts
                        if getattr(part, "text", None) and not getattr(part, "thought", False)
                    )
                    llama_resp = chat_from_gemini_response(
                        raw_chunk,
                        existing_content=content,
                        thought_signatures=thought_signatures,
                    )
                    llama_resp.delta = llama_resp.delta or content_delta or ""
                    yield llama_resp
            finally:
                if self.file_mode in ("fileapi", "hybrid"):
                    await adelete_uploaded_files(file_api_names, self._client)

        return gen()
