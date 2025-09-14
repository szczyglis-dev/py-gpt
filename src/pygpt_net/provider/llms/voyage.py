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

from typing import Optional, List
import voyageai
from llama_index.embeddings.voyageai import VoyageEmbedding
from .utils import ProxyEnv

class VoyageEmbeddingWithProxy(VoyageEmbedding):
    def __init__(
        self,
        *args,
        proxy: Optional[str] = None,
        voyage_api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        **kwargs
    ):
        super().__init__(*args, voyage_api_key=voyage_api_key, **kwargs)
        self._proxy = proxy

        if timeout is not None or max_retries is not None:
            self._client = voyageai.Client(
                api_key=voyage_api_key,
                timeout=timeout,
                max_retries=max_retries,
            )
            self._aclient = voyageai.AsyncClient(
                api_key=voyage_api_key,
                timeout=timeout,
                max_retries=max_retries,
            )

    # sync batch
    def get_text_embedding_batch(self, texts: List[str], show_progress: bool = False, **kwargs):
        with ProxyEnv(self._proxy):
            return super().get_text_embedding_batch(texts, show_progress=show_progress, **kwargs)

    # async batch
    async def aget_text_embedding_batch(self, texts: List[str], show_progress: bool = False):
        with ProxyEnv(self._proxy):
            return await super().aget_text_embedding_batch(texts, show_progress=show_progress)