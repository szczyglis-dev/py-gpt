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

"""Mistral chat transport adapter with endpoint and proxy support."""

from __future__ import annotations

from typing import Optional
from llama_index.llms.mistralai import MistralAI


class MistralAIWithProxy(MistralAI):
    def __init__(self, *args, proxy: Optional[str] = None, **kwargs):
        endpoint = kwargs.get("endpoint")
        super().__init__(*args, **kwargs)
        if not proxy:
            return

        import httpx
        from mistralai import Mistral
        timeout = getattr(self, "timeout", 120)

        try:
            sync_client = httpx.Client(proxy=proxy, timeout=timeout, follow_redirects=True)
            async_client = httpx.AsyncClient(proxy=proxy, timeout=timeout, follow_redirects=True)
        except TypeError:
            sync_client = httpx.Client(proxies=proxy, timeout=timeout, follow_redirects=True)
            async_client = httpx.AsyncClient(proxies=proxy, timeout=timeout, follow_redirects=True)

        sdk_kwargs = {
            "api_key": self.api_key,
            "client": sync_client,
            "async_client": async_client,
        }
        if endpoint:
            sdk_kwargs["server_url"] = endpoint

        self._client = Mistral(**sdk_kwargs)
