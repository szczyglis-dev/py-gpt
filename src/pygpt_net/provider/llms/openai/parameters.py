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

"""Shared request parameter policy for chat and agent adapters."""

from __future__ import annotations

from pygpt_net.item.model import ModelItem


class OpenAIParameters:
    def __init__(self, provider):
        self.provider = provider

    # ========================================
    # Reasoning
    # ========================================

    def chat_reasoning(self, window, model: ModelItem, args: dict) -> None:
        effort = window.core.models.get_reasoning_effort(model)
        if effort:
            self._merge(args, reasoning_effort=effort)

    def responses_reasoning(self, window, model: ModelItem, args: dict) -> None:
        effort = window.core.models.get_reasoning_effort(model)
        if effort:
            self._merge(args, reasoning={"effort": effort})

    # ========================================
    # Remote tools
    # ========================================

    @staticmethod
    def sources(args: dict, tools: list) -> None:
        """Request the complete hosted Web Search source list when available."""
        web_types = {
            "web_search",
            "web_search_preview",
            "web_search_2025_08_26",
            "web_search_preview_2025_03_11",
        }
        if not any(
                isinstance(tool, dict) and tool.get("type") in web_types
                for tool in tools or []
        ):
            return
        include_value = args.get("include")
        if isinstance(include_value, list):
            include = list(include_value)
        elif include_value:
            include = [include_value]
        else:
            include = []
        source_field = "web_search_call.action.sources"
        if source_field not in include:
            include.append(source_field)
        args["include"] = include

    # ========================================
    # Private helpers
    # ========================================

    @staticmethod
    def _merge(args: dict, **values) -> None:
        """Merge provider request fields forwarded by LlamaIndex."""
        extra = dict(args.get("additional_kwargs") or {})
        extra.update({key: value for key, value in values.items() if value is not None})
        args["additional_kwargs"] = extra
