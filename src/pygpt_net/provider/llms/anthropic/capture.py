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

"""AnthropicWithProxy transport adapter, independent of provider selection."""

from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.llms.anthropic import Anthropic
from pygpt_net.provider.llms.artifacts import append_unique_urls, extract_anthropic_urls


class AnthropicWithProxy(Anthropic):
    _pygpt_urls: list[str] = PrivateAttr(default_factory=list)

    def __init__(self, *args, proxy: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        if proxy:
            # sync
            from anthropic import DefaultHttpxClient
            self._client = self._client.with_options(
                http_client=DefaultHttpxClient(proxy=proxy)
            )

            # async
            import httpx
            try:
                async_http = httpx.AsyncClient(proxy=proxy)  # httpx >= 0.28
            except TypeError:
                async_http = httpx.AsyncClient(proxies=proxy)  # httpx <= 0.27
            self._aclient = self._aclient.with_options(http_client=async_http)

    def _capture_pygpt_urls(self, response) -> None:
        try:
            append_unique_urls(
                self._pygpt_urls,
                extract_anthropic_urls(response),
            )
        except Exception:
            pass

    def pop_pygpt_urls(self) -> list[str]:
        urls = list(self._pygpt_urls)
        self._pygpt_urls.clear()
        return urls

    def chat(self, messages, **kwargs):
        response = super().chat(messages, **kwargs)
        self._capture_pygpt_urls(response)
        return response

    def stream_chat(self, messages, **kwargs):
        stream = super().stream_chat(messages, **kwargs)

        def gen():
            for response in stream:
                self._capture_pygpt_urls(response)
                yield response

        return gen()

    async def achat(self, messages, **kwargs):
        response = await super().achat(messages, **kwargs)
        self._capture_pygpt_urls(response)
        return response

    async def astream_chat(self, messages, **kwargs):
        stream = await super().astream_chat(messages, **kwargs)

        async def gen():
            async for response in stream:
                self._capture_pygpt_urls(response)
                yield response

        return gen()

