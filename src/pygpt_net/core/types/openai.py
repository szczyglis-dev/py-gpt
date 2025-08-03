#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.03 14:00:00                  #
# ================================================== #

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