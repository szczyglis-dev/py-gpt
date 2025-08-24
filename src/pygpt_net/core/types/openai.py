#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 03:00:00                  #
# ================================================== #

OPENAI_COMPATIBLE_PROVIDERS = [
    "anthropic",
    "openai",
    "azure_openai",
    "google",
    "huggingface_router",
    "local_ai",
    "mistral_ai",
    "ollama",
    "perplexity",
    "deepseek_api",
    "x_ai",
]

OPENAI_DISABLE_TOOLS = [
    "o1-mini",
    "o1-preview"
    "o4-mini-deep-research",
    "o3-deep-research",
]
OPENAI_REMOTE_TOOL_DISABLE_IMAGE = [
    "gpt-3.5-turbo",
    "o4-mini",
    "o4-mini-deep-research",
    "o3-deep-research",
    "codex-mini-latest",
]
OPENAI_REMOTE_TOOL_DISABLE_CODE_INTERPRETER = [
    "gpt-3.5-turbo",
    "codex-mini-latest",
]
OPENAI_REMOTE_TOOL_DISABLE_WEB_SEARCH = [
    "gpt-3.5-turbo",
    "codex-mini-latest",
]
OPENAI_REMOTE_TOOL_DISABLE_COMPUTER_USE = [
    "gpt-3.5-turbo",
    "o4-mini",
    "o4-mini-deep-research",
    "o3-deep-research",
    "codex-mini-latest",
]
OPENAI_REMOTE_TOOL_DISABLE_FILE_SEARCH = [
    "gpt-3.5-turbo",
    "codex-mini-latest",
]
OPENAI_REMOTE_TOOL_DISABLE_MCP = [
    "gpt-3.5-turbo",
    "codex-mini-latest",
]