#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM

from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class OpenLLMLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(OpenLLMLLM, self).__init__(*args, **kwargs)
        self.id = "openllm"
        self.name = "OpenLLM"
        self.type = [MODE_LLAMA_INDEX]

    def setup(self) -> dict:
        from .config import setup
        return setup()

    def get_config(self, key: str, default: Any = BaseLLM._MISSING) -> Any:
        """
        Read a provider value, sending a placeholder key when none is set.

        The key is optional for the local daemon, but the OpenAI SDK refuses an
        empty one. The placeholder is only used for requests, never saved.
        """
        from .config import OPENLLM_KEYLESS_PLACEHOLDER
        value = super(OpenLLMLLM, self).get_config(key, default)
        if key == "api_key" and not value:
            return OPENLLM_KEYLESS_PLACEHOLDER
        return value

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LlamaIndex chat provider

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        from llama_index.llms.openai_like import OpenAILike
        args = self.prepare_openai_compatible_args(window, model)
        if "is_chat_model" not in args:
            args["is_chat_model"] = True
        if "is_function_calling_model" not in args:
            args["is_function_calling_model"] = model.tool_calls
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        self.log_llama_create(window, model, args, "OpenAILike")
        return OpenAILike(**args)

    def get_models(
            self,
            window,
    ) -> List[Dict]:
        """
        Return chat models exposed by OpenLLM ``/models``.

        The model list also contains embedding, image, audio and video models,
        so only entries that declare the ``chat`` capability are returned.
        Context window, output limit, vision and tool support are read from
        the model card when OpenLLM provides them.

        :param window: window instance
        :return: list of models
        """
        items: List[Dict] = []
        try:
            client = self.get_client(window)
            models_list = client.models.list()
            for item in models_list.data or []:
                card = getattr(item, "model_extra", None) or {}
                capabilities = card.get("capabilities")
                if isinstance(capabilities, list) and "chat" not in capabilities:
                    continue
                entry = {"id": item.id, "name": item.id}
                if isinstance(capabilities, list):
                    entry["input"] = ["text", "image"] if "vision" in capabilities else ["text"]
                    entry["tool_calls"] = "tools" in capabilities
                if card.get("context_window"):
                    entry["ctx"] = card.get("context_window")
                if card.get("max_output_tokens"):
                    entry["tokens"] = card.get("max_output_tokens")
                items.append(entry)
        except Exception as e:
            window.core.debug.log(e)
        return items
