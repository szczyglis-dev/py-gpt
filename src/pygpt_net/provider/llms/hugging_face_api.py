#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.26 19:00:00                  #
# ================================================== #

import os
from typing import Optional, List, Dict

from pygpt_net.core.types import (
    MODE_LLAMA_INDEX,
)
from llama_index.core.llms.llm import BaseLLM as LlamaBaseLLM
from llama_index.core.base.embeddings.base import BaseEmbedding

from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.item.model import ModelItem


class HuggingFaceApiLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(HuggingFaceApiLLM, self).__init__(*args, **kwargs)
        self.id = "huggingface_api"
        self.name = "HuggingFace API"
        self.type = [MODE_LLAMA_INDEX, "embeddings"]

    def llama(
            self,
            window,
            model: ModelItem,
            stream: bool = False
    ) -> LlamaBaseLLM:
        """
        Return LLM provider instance for llama (Hugging Face Inference API) z obsługą proxy.
        """
        from llama_index.llms.huggingface_api import HuggingFaceInferenceAPI as LIHF

        class HuggingFaceInferenceAPIWithProxy(LIHF):
            def __init__(self, *, proxy=None, trust_env=None, **kwargs):
                """
                proxy: str or dict compatible with huggingface_hub (e.g. "http://user:pass@host:3128"
                       lub {"http": "...", "https": "..."})
                trust_env: forAsyncInferenceClient (default False) - whether to trust environment variables
                """
                # alias: api_key -> token
                if "api_key" in kwargs and "token" not in kwargs:
                    kwargs["token"] = kwargs.pop("api_key")

                super().__init__(**kwargs)

                if proxy is None and trust_env is None:
                    return

                if isinstance(proxy, str):
                    hf_proxies = {"http": proxy, "https": proxy}
                else:
                    hf_proxies = proxy

                base_kwargs = {}
                if hasattr(self, "_get_inference_client_kwargs"):
                    try:
                        base_kwargs = self._get_inference_client_kwargs()  # type: ignore
                    except Exception:
                        base_kwargs = {}

                # fallback
                if not base_kwargs:
                    for src in ["model", "token", "timeout", "headers", "cookies", "base_url", "task"]:
                        if hasattr(self, src):
                            val = getattr(self, src)
                            if val not in (None, ""):
                                base_kwargs[src] = val

                from huggingface_hub import InferenceClient, AsyncInferenceClient

                sync_kwargs = dict(base_kwargs)
                async_kwargs = dict(base_kwargs)
                if hf_proxies is not None:
                    sync_kwargs["proxies"] = hf_proxies
                    async_kwargs["proxies"] = hf_proxies
                if trust_env is not None:
                    async_kwargs["trust_env"] = trust_env  # default False

                sync_client = InferenceClient(**sync_kwargs)
                async_client = AsyncInferenceClient(**async_kwargs)

                for name, client in (("_client", sync_client), ("_sync_client", sync_client), ("client", sync_client)):
                    if hasattr(self, name):
                        setattr(self, name, client)
                for name, client in (("_aclient", async_client), ("_async_client", async_client)):
                    if hasattr(self, name):
                        setattr(self, name, client)

        cfg = window.core.config
        args = self.parse_args(model.llama_index, window)

        # model
        if "model" not in args:
            args["model"] = model.id

        # token / api_key
        if "token" not in args:
            if "api_key" in args and args["api_key"]:
                args["token"] = args.pop("api_key")
            else:
                args["token"] = cfg.get("api_key_hugging_face", "")

        # Inference Endpoint / router
        base_url = cfg.get("api_endpoint_hugging_face", "").strip()
        if base_url and "base_url" not in args:
            args["base_url"] = base_url

        # proxy + trust_env (async)
        proxy = cfg.get("api_proxy") or cfg.get("api_native_hf.proxy")
        trust_env = cfg.get("api_native_hf.trust_env", False)

        return HuggingFaceInferenceAPIWithProxy(proxy=proxy, trust_env=trust_env, **args)

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
        if "token" not in args:
            if "api_key" in args:
                args["token"] = args.pop("api_key")
            else:
                args["token"] = window.core.config.get("api_key_hugging_face", "")

        # model_name alias
        if "model" in args and "model_name" not in args:
            args["model_name"] = args.pop("model")

        # Inference Endpoint / router
        base_url = window.core.config.get("api_endpoint_hugging_face", "").strip()
        if base_url and "base_url" not in args:
            args["base_url"] = base_url

        # proxy + trust_env (async)
        proxy = window.core.config.get("api_proxy") or window.core.config.get("api_native_hf.proxy")
        trust_env = window.core.config.get("api_native_hf.trust_env", False)

        return HFEmbed(proxy=proxy, trust_env=trust_env, **args)

    def init_embeddings(
            self,
            window,
            env: Optional[List[Dict]] = None
    ):
        """
        Initialize embeddings provider

        :param window: window instance
        :param env: ENV configuration list
        """
        super(HuggingFaceApiLLM, self).init_embeddings(window, env)

        # === FIX FOR LOCAL EMBEDDINGS ===
        # if there is no OpenAI api key then set fake key to prevent empty key Llama-index error
        if ('OPENAI_API_KEY' not in os.environ
                and (window.core.config.get('api_key') is None or window.core.config.get('api_key') == "")):
            os.environ['OPENAI_API_KEY'] = "_"
