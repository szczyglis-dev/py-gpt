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

import asyncio
from typing import Any, List, Optional

import xai_sdk
from llama_index.core.embeddings import BaseEmbedding


class XAIEmbedding(BaseEmbedding):
    """
    LlamaIndex xAI Embedding SDK wrapper.
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        api_host: str = "api.x.ai",
        **kwargs: Any,
    ) -> None:
        super().__init__(model_name=model_name, **kwargs)
        self._api_key = api_key
        self._api_host = api_host
        self._client = xai_sdk.Client(api_key=api_key, api_host=api_host)

    def _run_async(self, coro):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, loop).result()
        else:
            return asyncio.run(coro)

    async def _aembed_many(self, texts: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        async for (values, _shape) in self._client.embedder.embed(
            texts=texts, model_name=self.model_name
        ):
            embeddings.append(list(values))
        return embeddings

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._run_async(self._aembed_many([query]))[0]

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return (await self._aembed_many([query]))[0]

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._run_async(self._aembed_many([text]))[0]

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return (await self._aembed_many([text]))[0]

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return self._run_async(self._aembed_many(texts))

    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return await self._aembed_many(texts)