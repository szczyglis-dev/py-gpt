#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 21:45:00                  #
# ================================================== #

TOOL_EXPERT_CALL_NAME = "expert_call"
TOOL_EXPERT_CALL_DESCRIPTION = (
    "Run a named Expert as an isolated agent with its own persistent conversation memory, "
    "enabled tools and optional RAG index. Provide a complete task instruction. An optional "
    "system_prompt can temporarily specialize the agent; when supplied, the Expert preset prompt "
    "is preserved as an additional user system instruction."
)
TOOL_EXPERT_CALL_PARAM_ID_DESCRIPTION = "Expert ID from the allowed experts list"
TOOL_EXPERT_CALL_PARAM_INSTRUCTION_DESCRIPTION = "Required, self-contained task instruction for the expert agent"
TOOL_EXPERT_CALL_PARAM_SYSTEM_PROMPT_DESCRIPTION = (
    "Optional temporary system prompt for this expert call. If omitted, the Expert preset system "
    "prompt is used unchanged."
)
# Backward-compatible symbol for older integrations/tests. New calls use `instruction`.
TOOL_EXPERT_CALL_PARAM_QUERY_DESCRIPTION = TOOL_EXPERT_CALL_PARAM_INSTRUCTION_DESCRIPTION

TOOL_QUERY_ENGINE_NAME = "get_context"
TOOL_QUERY_ENGINE_DESCRIPTION = "Get additional context for provided question. Use this whenever you need additional context to provide an answer."
TOOL_QUERY_ENGINE_PARAM_QUERY_DESCRIPTION = "query to retrieve additional context for the question"
TOOL_QUERY_ENGINE_SPEC = ("**" + TOOL_QUERY_ENGINE_NAME + "**: "
                          + TOOL_QUERY_ENGINE_DESCRIPTION +
                     "available params: {'query': {'type': 'string', 'description': 'query string'}}, required: [query]")