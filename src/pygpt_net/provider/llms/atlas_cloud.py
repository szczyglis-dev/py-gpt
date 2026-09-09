#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #
import os
from typing import Dict, List

from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.llms.base import BaseLLM


ATLAS_CLOUD_DEFAULT_BASE_URL = "https://api.atlascloud.ai/v1"


class AtlasCloudLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(AtlasCloudLLM, self).__init__(*args, **kwargs)
        self.id = "atlas_cloud"
        self.name = "Atlas Cloud"
        self.type = [MODE_LLAMA_INDEX]

    def _apply_auth(self, args: Dict, window) -> Dict:
        if not args.get("api_key"):
            args["api_key"] = os.environ.get("ATLASCLOUD_API_KEY") or window.core.config.get(
                "api_key_atlas_cloud", ""
            )
        if not args.get("api_base"):
            args["api_base"] = os.environ.get("ATLASCLOUD_API_BASE") or window.core.config.get(
                "api_endpoint_atlas_cloud", ""
            ) or ATLAS_CLOUD_DEFAULT_BASE_URL
        return args

    def llama(self, window, model: ModelItem, stream: bool = False) -> LlamaBaseLLM:
        from llama_index.llms.openai_like import OpenAILike

        args = self.parse_args(model.llama_index, window)
        args.setdefault("model", model.id)
        args = self._apply_auth(args, window)
        args.setdefault("is_chat_model", True)
        args.setdefault("is_function_calling_model", model.tool_calls)
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        return OpenAILike(**args)

    def get_models(self, window) -> List[Dict]:
        client = self.get_client(window)
        models_list = client.models.list()
        return [
            {"id": item.id, "name": item.id}
            for item in (models_list.data or [])
        ]
