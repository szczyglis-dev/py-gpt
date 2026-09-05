#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from __future__ import annotations

import os
from typing import Any, Sequence

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.llms.google_genai import GoogleGenAI
from google.genai import types as gtypes

from pygpt_net.provider.api.google.utils import extract_google_urls


class AgentGoogleGenAI(GoogleGenAI):
    """Google GenAI adapter used by Agents v2.

    LlamaIndex preserves Gemini grounding metadata in ``ChatResponse.raw``, but
    provider-side search results do not pass through PyGPT's normal Google chat
    stream parser in Agents v2. This adapter captures grounding/citation URLs so
    the agent runtime can merge them into the visible ``CtxItem.urls``.
    """

    _pygpt_urls: list[str] = PrivateAttr(default_factory=list)
    _pygpt_remote_tools: list[Any] = PrivateAttr(default_factory=list)

    def __init__(self, *args, pygpt_remote_tools=None, **kwargs):
        # Remote provider tools are deliberately kept outside GoogleGenAI's
        # built_in_tool/generation_config. LlamaIndex otherwise prefers the
        # preconfigured tools and drops FunctionAgent's local function tools.
        # We merge both sets in _prepare_chat_with_tools instead.
        super().__init__(*args, **kwargs)
        configured = []
        try:
            configured = list((self._generation_config or {}).get("tools") or [])
            if configured:
                self._generation_config["tools"] = None
        except Exception:
            configured = []
        self._pygpt_remote_tools = [*configured, *(pygpt_remote_tools or [])]

    @staticmethod
    def _is_vertex_runtime() -> bool:
        value = str(os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "")).strip().lower()
        return value not in ("", "0", "false", "no", "off")

    @staticmethod
    def _with_server_side_tool_invocations(tool_config):
        """Enable Google built-in + function-tool context circulation.

        Gemini Developer API requires this flag whenever provider-side built-in
        tools (Google Search, URL Context, Maps, etc.) are combined with custom
        function declarations. LlamaIndex 0.14.23 creates ToolConfig for its
        FunctionAgent tools, but does not set this newer Google flag.
        """
        if tool_config is None:
            return gtypes.ToolConfig(include_server_side_tool_invocations=True)

        if isinstance(tool_config, dict):
            tool_config = dict(tool_config)
            tool_config["include_server_side_tool_invocations"] = True
            return tool_config

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
        return gtypes.ToolConfig(**data)

    def _prepare_chat_with_tools(self, *args, **kwargs):
        prepared = super()._prepare_chat_with_tools(*args, **kwargs)
        if not self._pygpt_remote_tools:
            return prepared

        local_tools = prepared.get("tools") or []
        if not isinstance(local_tools, list):
            local_tools = [local_tools]
        prepared["tools"] = [*self._pygpt_remote_tools, *local_tools]

        # Gemini Developer API requires explicit tool-context circulation when
        # server-side built-ins and FunctionAgent function calls coexist.
        # Do not send this Developer-API-only flag to Vertex AI.
        if not self._is_vertex_runtime():
            prepared["tool_config"] = self._with_server_side_tool_invocations(
                prepared.get("tool_config")
            )

        return prepared

    def _capture_urls(self, raw: Any) -> None:
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

    def _prepare_response(self, response: ChatResponse) -> ChatResponse:
        self._capture_urls(getattr(response, "raw", None))
        return response

    def pop_pygpt_urls(self) -> list[str]:
        urls = list(self._pygpt_urls)
        self._pygpt_urls.clear()
        return urls

    async def _achat(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ) -> ChatResponse:
        response = await super()._achat(messages, **kwargs)
        return self._prepare_response(response)

    async def _astream_chat(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ):
        stream = await super()._astream_chat(messages, **kwargs)

        async def gen():
            async for response in stream:
                yield self._prepare_response(response)

        return gen()
