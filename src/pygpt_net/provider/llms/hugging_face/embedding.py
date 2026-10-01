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

from typing import Optional, Dict, Any, Union

from llama_index.embeddings.huggingface_api import (
    HuggingFaceInferenceAPIEmbedding as _HFEmbed,
)

class HuggingFaceInferenceAPIEmbeddingWithProxy(_HFEmbed):
    def __init__(
        self,
        *,
        proxy: Optional[Union[str, Dict[str, str]]] = None,
        trust_env: Optional[bool] = None,
        **kwargs: Any,
    ) -> None:
        """
        proxy: e.g. "http://user:pass@host:3128" albo {"http": "...", "https": "..."}
        trust_env: AsyncInferenceClient; if True, then use the system's proxy settings
        """

        if "api_key" in kwargs and "token" not in kwargs:
            kwargs["token"] = kwargs.pop("api_key")
        if "model" in kwargs and "model_name" not in kwargs:
            kwargs["model_name"] = kwargs.pop("model")

        super().__init__(**kwargs)

        # if no proxy and no trust_env, then do nothing
        if proxy is None and trust_env is None:
            return

        # dict proxies for huggingface_hub.*
        hf_proxies: Optional[Union[str, Dict[str, str]]] = None
        if proxy is not None:
            hf_proxies = {"http": proxy, "https": proxy} if isinstance(proxy, str) else proxy

        base_kwargs: Dict[str, Any] = {}

        for src, dst in [
            ("model_name", "model"),
            ("token", "token"),
            ("timeout", "timeout"),
            ("headers", "headers"),
            ("cookies", "cookies"),
            ("base_url", "base_url"),
        ]:
            if hasattr(self, src):
                val = getattr(self, src)
                if val is not None and val != "":
                    base_kwargs[dst] = val

        from huggingface_hub import InferenceClient, AsyncInferenceClient

        sync_kwargs = dict(base_kwargs)
        async_kwargs = dict(base_kwargs)

        if hf_proxies is not None:
            sync_kwargs["proxies"] = hf_proxies
            async_kwargs["proxies"] = hf_proxies
        if trust_env is not None:
            async_kwargs["trust_env"] = trust_env  # default False w AsyncInferenceClient

        sync_client = InferenceClient(**sync_kwargs)
        async_client = AsyncInferenceClient(**async_kwargs)

        for name, client in (
            ("_sync_client", sync_client),
            ("_client", sync_client),
        ):
            if hasattr(self, name):
                setattr(self, name, client)

        for name, client in (
            ("_async_client", async_client),
            ("_aclient", async_client),
        ):
            if hasattr(self, name):
                setattr(self, name, client)