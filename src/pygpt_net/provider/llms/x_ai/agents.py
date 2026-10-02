#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 12:00:00                  #
# ================================================== #

"""XAI agent adapter construction and Computer Use selection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict
from pygpt_net.item.model import ModelItem

if TYPE_CHECKING:
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from ..agents import ProviderAgents


class XAIAgents(ProviderAgents):
    # ========================================
    # Agent adapters
    # ========================================

    def create(
            self,
            window,
            model: ModelItem,
            stream: bool = False,
            allow_remote_tools: bool = True,
            force_computer_use: bool = False,
    ) -> LlamaBaseLLM:
        """Return xAI LLM for Agents v2.

        xAI removed Live Search ``search_parameters`` from Chat Completions.
        When provider-native Agent Tools are enabled, use xAI's
        OpenAI-compatible Responses API instead. Local FunctionAgent tools are
        merged by LlamaIndex with the server-side xAI tool descriptors.
        """
        if not allow_remote_tools:
            return self.provider.llama(
                window=window,
                model=model,
                stream=stream,
                remote_tools=False,
            )

        try:
            remote_cfg = window.core.api.xai.remote.build_for_responses(model=model) or {}
        except Exception as e:
            window.core.debug.log(e)
            remote_cfg = {}

        built_tools = remote_cfg.get("tools") or []
        if not built_tools:
            return self.provider.llama(
                window=window,
                model=model,
                stream=stream,
                remote_tools=False,
            )

        return self.responses(
            window=window,
            model=model,
            remote_cfg=remote_cfg,
        )

    def responses(
            self,
            window,
            model: ModelItem,
            remote_cfg: Dict,
    ) -> LlamaBaseLLM:
        """Build an xAI Responses/Agent Tools LlamaIndex adapter."""
        from .responses_agent import AgentXAIResponses

        args = self.provider.prepare_openai_compatible_args(window, model)

        # Grok 3 does not support the current server-side Agent Tools. Mirror
        # normal xAI Chat and Agents v2 by switching to the configured fallback.
        if str(args["model"] or "").lower().startswith("grok-3"):
            args["model"] = window.core.config.get("xai_tools_fallback_model") or "grok-4.5-latest"

        # OpenAILike/Chat Completions and OpenAIResponses use different names
        # for the output-token limit and different capability-only arguments.
        if "max_tokens" in args and "max_output_tokens" not in args:
            args["max_output_tokens"] = args.pop("max_tokens")
        args.pop("is_chat_model", None)
        args.pop("is_function_calling_model", None)
        args = self.provider.inject_llamaindex_http_clients(args, window.core.config)

        reasoning_effort = window.core.models.get_reasoning_effort(model)
        if reasoning_effort:
            additional_kwargs = dict(args.get("additional_kwargs") or {})
            additional_kwargs["reasoning"] = {"effort": reasoning_effort}
            args["additional_kwargs"] = additional_kwargs

        args["built_in_tools"] = list(remote_cfg.get("tools") or [])
        include = list(remote_cfg.get("include") or [])
        if include:
            current = args.get("include")
            if isinstance(current, list):
                include = [*current, *include]
            elif current:
                include = [current, *include]
            args["include"] = list(dict.fromkeys(include))

        ctx_size = int(getattr(model, "ctx", 0) or 0)
        if ctx_size > 0 and "context_window" not in args:
            args["context_window"] = ctx_size

        self.provider.log_llama_create(window, model, args, "AgentXAIResponses")
        return AgentXAIResponses(**args)
