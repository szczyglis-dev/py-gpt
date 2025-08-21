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

QUERY_ENGINE_TOOL_NAME = "get_context"
QUERY_ENGINE_TOOL_DESCRIPTION = "Get additional context for provided question. Use this whenever you need additional context to provide an answer."
QUERY_ENGINE_PARAM_DESCRIPTION = "query to retrieve additional context for the question"
QUERY_ENGINE_TOOL_SPEC = ("**"+QUERY_ENGINE_TOOL_NAME+"**: "
                     + QUERY_ENGINE_TOOL_DESCRIPTION +
                     "available params: {'query': {'type': 'string', 'description': 'query string'}}, required: [query]")

TOOL_EXPERT_CALL_NAME = "expert_call"
TOOL_EXPERT_CALL_DESCRIPTION = "Call the expert"
TOOL_EXPERT_CALL_PARAM_ID_DESCRIPTION = "Expert ID"
TOOL_EXPERT_CALL_PARAM_QUERY_DESCRIPTION = "Query to expert"