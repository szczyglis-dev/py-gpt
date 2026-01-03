#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.03 17:00:00                  #
# ================================================== #

from enum import Enum

class ChunkType(str, Enum):
    """
    Enum for chunk type classification.
    """
    API_CHAT = "api_chat"  # OpenAI Chat Completions / or compatible
    API_CHAT_RESPONSES = "api_chat_responses"  # OpenAI Responses
    API_COMPLETION = "api_completion"  # OpenAI Completions
    LANGCHAIN_CHAT = "langchain_chat"  # LangChain chat (deprecated)
    LLAMA_CHAT = "llama_chat"  # LlamaIndex chat
    GOOGLE = "google"  # Google SDK
    GOOGLE_INTERACTIONS_API = "api_google_interactions"  # Google SDK, deep research - interactions API
    ANTHROPIC = "anthropic"  # Anthropic SDK
    XAI_SDK = "xai_sdk"  # xAI SDK
    RAW = "raw"  # Raw string fallback