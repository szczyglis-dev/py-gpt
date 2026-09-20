#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.15 01:00:00                  #
# ================================================== #

from typing import Optional, List, Dict, Union

from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.multi_modal_llms import MultiModalLLM as LlamaMultiModalLLM
from llama_index.core.base.embeddings.base import BaseEmbedding

from pygpt_net.core.types import (
    MODE_CHAT,
    MODE_LLAMA_INDEX,
)
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class HuggingFaceRouterLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(HuggingFaceRouterLLM, self).__init__(*args, **kwargs)
        self.id = "huggingface_router"
        self.name = "HuggingFace Router"
        self.type = [MODE_CHAT, MODE_LLAMA_INDEX, "embeddings"]

    def completion(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ):
        """
        Return LLM provider instance for completion

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        pass

    def chat(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ):
        """
        Return LLM provider instance for chat

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        pass

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        from llama_index.llms.openai_like import OpenAILike
        args = self.prepare_openai_compatible_args(window, model)
        reasoning_effort = window.core.models.get_reasoning_effort(model)
        if reasoning_effort:
            additional_kwargs = dict(args.get("additional_kwargs") or {})
            additional_kwargs["reasoning_effort"] = reasoning_effort
            args["additional_kwargs"] = additional_kwargs
        args = self.inject_llamaindex_http_clients(args, window.core.config)
        self.log_llama_create(window, model, args, "OpenAILike")
        return OpenAILike(**args)

    def llama_multimodal(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaMultiModalLLM:
        """
        Return multimodal LLM provider instance for llama

        :param window: window instance
        :param model: model instance
        :param stream: stream mode
        :return: LLM provider instance
        """
        pass

    def get_embeddings_model(
            self,
            window,
            config: Optional[List[Dict]] = None
    ) -> BaseEmbedding:
        from .hugging_face_embedding import (
            HuggingFaceInferenceAPIEmbeddingWithProxy as HFEmbed,
        )

        args: Dict = {}
        if config is not None:
            args = self.parse_args({"args": config}, window)

        # token / api_key
        if not args.get("token"):
            if args.get("api_key"):
                args["token"] = args.pop("api_key")
            else:
                args["token"] = (
                    self.get_env_override(
                        window,
                        window.core.config.get("llama.idx.embeddings.env", []) or [],
                        ["HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "OPENAI_API_KEY"],
                    )
                    or window.core.config.get("api_key_hugging_face", "")
                )

        # model_name alias
        if "model" in args and "model_name" not in args:
            args["model_name"] = args.pop("model")

        # Inference Endpoint / router
        base_url = (
            self.get_env_override(
                window,
                window.core.config.get("llama.idx.embeddings.env", []) or [],
                ["HF_INFERENCE_ENDPOINT", "OPENAI_API_BASE"],
            )
            or window.core.config.get("api_endpoint_hugging_face", "")
            or ""
        ).strip()
        if base_url and not args.get("base_url"):
            args["base_url"] = base_url

        # proxy + trust_env (async)
        proxy = window.core.config.get("api_proxy") or window.core.config.get("api_native_hf.proxy")
        if not window.core.config.get("api_proxy.enabled", False):
            proxy = ""
        trust_env = window.core.config.get("api_native_hf.trust_env", False)
        args.setdefault("timeout", self.get_embeddings_timeout(window.core.config))

        return HFEmbed(proxy=proxy, trust_env=trust_env, **args)
