#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.21 07:00:00                  #
# ================================================== #

TOOL_EXPERT_CALL_NAME = "expert_call"
TOOL_EXPERT_CALL_DESCRIPTION = "Call the expert"
TOOL_EXPERT_CALL_PARAM_ID_DESCRIPTION = "Expert ID"
TOOL_EXPERT_CALL_PARAM_QUERY_DESCRIPTION = "Query to expert"

TOOL_QUERY_ENGINE_NAME = "get_context"
TOOL_QUERY_ENGINE_DESCRIPTION = "Get additional context for provided question. Use this whenever you need additional context to provide an answer."
TOOL_QUERY_ENGINE_PARAM_QUERY_DESCRIPTION = "query to retrieve additional context for the question"
TOOL_QUERY_ENGINE_SPEC = ("**" + TOOL_QUERY_ENGINE_NAME + "**: "
                          + TOOL_QUERY_ENGINE_DESCRIPTION +
                     "available params: {'query': {'type': 'string', 'description': 'query string'}}, required: [query]")