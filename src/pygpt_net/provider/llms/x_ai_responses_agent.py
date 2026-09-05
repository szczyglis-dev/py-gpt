#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from __future__ import annotations

import re
from typing import Any

from llama_index.core.base.llms.types import LLMMetadata

from pygpt_net.provider.llms.openai_responses_agent import AgentOpenAIResponses


class AgentXAIResponses(AgentOpenAIResponses):
    """xAI Responses/Agent Tools adapter for Agents v2.

    xAI's Agent Tools API is OpenAI Responses compatible, so we reuse the
    LlamaIndex Responses implementation with xAI credentials/base URL.  The
    adapter additionally captures xAI's top-level ``citations`` list and URL
    annotations/sources, and advertises function-calling capability for Grok
    model names that are unknown to LlamaIndex's OpenAI model registry.
    """

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=self.context_window or 200000,
            num_output=self.max_output_tokens or -1,
            is_chat_model=True,
            is_function_calling_model=True,
            model_name=self.model,
        )

    @property
    def _tokenizer(self):
        """xAI model names are not part of tiktoken's OpenAI model registry."""
        return None

    @staticmethod
    def _walk_urls(value: Any) -> list[str]:
        """Extract web/X URLs from arbitrary xAI Responses payloads."""
        urls: list[str] = []
        seen = set()

        def add(item):
            if not isinstance(item, str):
                return
            candidate = item.strip()
            if not candidate.startswith(("http://", "https://")):
                return
            if candidate in seen:
                return
            seen.add(candidate)
            urls.append(candidate)

        def walk(obj, key: str = ""):
            if obj is None:
                return
            if isinstance(obj, str):
                if key in {"url", "uri", "citation", "source_url"}:
                    add(obj)
                elif key in {"citations", "sources"}:
                    for match in re.findall(r"https?://[^\s\]\)\}\>,\"']+", obj):
                        add(match)
                return
            if isinstance(obj, dict):
                for k, v in obj.items():
                    lk = str(k).lower()
                    if lk in {"url", "uri", "source_url"}:
                        add(v)
                    elif lk == "citations" and isinstance(v, list):
                        for item in v:
                            if isinstance(item, str):
                                add(item)
                            else:
                                walk(item, lk)
                    else:
                        walk(v, lk)
                return
            if isinstance(obj, (list, tuple, set)):
                for item in obj:
                    if isinstance(item, str) and key in {"citations", "sources"}:
                        add(item)
                    else:
                        walk(item, key)
                return

            # SDK/Pydantic objects. Prefer safe plain-data conversion so extras
            # such as xAI's top-level citations are retained when available.
            dumped = AgentOpenAIResponses._safe_dump(obj)
            if dumped is not obj:
                walk(dumped, key)
                return

            for attr in ("citations", "url", "uri", "response", "annotation", "output"):
                try:
                    child = getattr(obj, attr, None)
                except Exception:
                    child = None
                if child is not None:
                    walk(child, attr)

        walk(value)
        return urls

    def _capture_raw_urls(self, raw: Any) -> None:
        # Keep OpenAI-compatible url_citation/source extraction first.
        super()._capture_raw_urls(raw)
        try:
            self._append_urls(self._walk_urls(raw))
            response = getattr(raw, "response", None)
            if response is not None:
                self._append_urls(self._walk_urls(response))
        except Exception:
            pass
