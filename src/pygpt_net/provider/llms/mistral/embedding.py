#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 12:00:00                  #
# ================================================== #

"""Mistral embedding transport adapter with endpoint and proxy support."""

from __future__ import annotations

import os
from typing import Optional
from llama_index.embeddings.mistralai import MistralAIEmbedding


class MistralAIEmbeddingWithProxy(MistralAIEmbedding):
    def __init__(
            self,
            *args,
            proxy: Optional[str] = None,
            api_key: Optional[str] = None,
            endpoint: Optional[str] = None,
            timeout: Optional[float] = None,
            **kwargs
    ):
        captured_key = api_key or os.environ.get("MISTRAL_API_KEY", "")
        super().__init__(*args, api_key=api_key, **kwargs)

        # The upstream embedding wrapper does not expose a custom
        # endpoint. Rebuild its SDK client when PyGPT has one so the
        # normal global provider endpoint is honored without requiring
        # an Advanced ENV entry.
        server_url = endpoint or os.environ.get("MISTRAL_ENDPOINT") or None
        from mistralai import Mistral
        sdk_kwargs = {"api_key": captured_key}
        if timeout is not None:
            sdk_kwargs["timeout_ms"] = int(timeout * 1000)
        if server_url:
            sdk_kwargs["server_url"] = server_url

        if proxy:
            import httpx
            http_timeout = timeout if timeout is not None else 60.0
            try:
                sync_client = httpx.Client(proxy=proxy, timeout=http_timeout, follow_redirects=True)
                async_client = httpx.AsyncClient(proxy=proxy, timeout=http_timeout, follow_redirects=True)
            except TypeError:
                sync_client = httpx.Client(proxies=proxy, timeout=http_timeout, follow_redirects=True)
                async_client = httpx.AsyncClient(proxies=proxy, timeout=http_timeout, follow_redirects=True)
            sdk_kwargs["client"] = sync_client
            sdk_kwargs["async_client"] = async_client

        self._client = Mistral(**sdk_kwargs)
        if hasattr(self, "_mistralai_client"):
            self._mistralai_client = self._client
