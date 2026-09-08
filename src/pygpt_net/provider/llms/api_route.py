#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.08 00:00:00                  #
# ================================================== #

import os
from typing import Dict, List

from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.llms.base import BaseLLM


API_ROUTE_DEFAULT_BASE_URL = "https://global.api-route.com/v1"


class APIRouteLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(APIRouteLLM, self).__init__(*args, **kwargs)
        self.id = "api_route"
        self.name = "API Route"
        self.type = [MODE_LLAMA_INDEX]

    def _apply_auth(self, args: Dict, window) -> Dict:
        if "api_key" not in args or args["api_key"] == "":
            args["api_key"] = os.environ.get("API_ROUTE_API_KEY") or window.core.config.get(
                "api_key_api_route", ""
            )
        if "api_base" not in args or args["api_base"] == "":
            args["api_base"] = os.environ.get("API_ROUTE_API_BASE") or window.core.config.get(
                "api_endpoint_api_route", ""
            ) or API_ROUTE_DEFAULT_BASE_URL
        return args

    def llama(self, window, model: ModelItem, stream: bool = False) -> LlamaBaseLLM:
        from llama_index.llms.openai_like import OpenAILike

        args = self.parse_args(model.llama_index, window)
        if "model" not in args:
            args["model"] = model.id
        args = self._apply_auth(args, window)
        if "is_chat_model" not in args:
            args["is_chat_model"] = True
        if "is_function_calling_model" not in args:
            args["is_function_calling_model"] = model.tool_calls
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        return OpenAILike(**args)

    def get_models(self, window) -> List[Dict]:
        items = []
        models_list = self.get_client(window).models.list()
        if models_list.data:
            for item in models_list.data:
                items.append({
                    "id": item.id,
                    "name": item.id,
                })
        return items
