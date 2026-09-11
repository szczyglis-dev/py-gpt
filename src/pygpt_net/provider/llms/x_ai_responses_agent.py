#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from __future__ import annotations

from typing import Any

from llama_index.core.base.llms.types import LLMMetadata

from pygpt_net.provider.llms.openai_responses_agent import AgentOpenAIResponses
from pygpt_net.provider.llms.artifacts import extract_xai_urls


class AgentXAIResponses(AgentOpenAIResponses):
    """Shared xAI Responses/Agent Tools adapter for LlamaIndex workflows.

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

    def _capture_raw_urls(self, raw: Any) -> None:
        try:
            self._append_urls(extract_xai_urls(raw))
        except Exception:
            pass
