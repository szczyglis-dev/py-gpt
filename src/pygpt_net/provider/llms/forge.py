#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.03.08 00:00:00                  #
# ================================================== #
import os
from typing import Dict, List, Optional

from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem

FORGE_DEFAULT_BASE_URL = "https://api.forge.tensorblock.co/v1"
class ForgeLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(ForgeLLM, self).__init__(*args, **kwargs)
        self.id = "forge"
        self.name = "Forge"
        self.type = [MODE_LLAMA_INDEX, "embeddings"]

    def _apply_auth(self, args: Dict, window) -> Dict:
        if "api_key" not in args or args["api_key"] == "":
            args["api_key"] = os.environ.get("FORGE_API_KEY") or window.core.config.get("api_key_forge", "")
        if "api_base" not in args or args["api_base"] == "":
            args["api_base"] = os.environ.get("FORGE_API_BASE") or window.core.config.get(
                "api_endpoint_forge", ""
            ) or FORGE_DEFAULT_BASE_URL
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

    def get_embeddings_model(self, window, config: Optional[List[Dict]] = None) -> BaseEmbedding:
        from llama_index.embeddings.openai_like import OpenAILikeEmbedding
        args = {}
        if config is not None:
            args = self.parse_args({"args": config}, window)
        args = self._apply_auth(args, window)
        if "model" in args and "model_name" not in args:
            args["model_name"] = args.pop("model")
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        return OpenAILikeEmbedding(**args)

    def get_models(self, window) -> List[Dict]:
        items = []
        client = self.get_client(window)
        models_list = client.models.list()
        if models_list.data:
            for item in models_list.data:
                items.append({
                    "id": item.id,
                    "name": item.id,
                })
        return items
