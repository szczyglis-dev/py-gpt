#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 12:48:00                  #
# ================================================== #

from typing import Any

from llama_index.core.base.llms.types import (
    CompletionResponse,
    CompletionResponseAsyncGen,
    CompletionResponseGen,
)
from llama_index.core.llms.callbacks import llm_completion_callback

from pygpt_net.provider.llms.ollama_custom import Ollama


def _plain_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return dict(value)
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump(exclude_none=True)
    try:
        return dict(value)
    except Exception:
        return {}


class OllamaCompletion(Ollama):
    """Ollama LlamaIndex adapter using native ``/api/generate`` completion."""

    @llm_completion_callback()
    def complete(
            self,
            prompt: str,
            formatted: bool = False,
            **kwargs: Any,
    ) -> CompletionResponse:
        format_value = kwargs.pop("format", "json" if self.json_mode else None)
        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            stream=False,
            format=format_value,
            options=self._model_kwargs,
            keep_alive=self.keep_alive,
            **kwargs,
        )
        raw = _plain_dict(response)
        token_counts = self._get_response_token_counts(raw)
        if token_counts:
            raw["usage"] = token_counts
        return CompletionResponse(
            text=str(raw.get("response") or ""),
            raw=raw,
        )

    @llm_completion_callback()
    def stream_complete(
            self,
            prompt: str,
            formatted: bool = False,
            **kwargs: Any,
    ) -> CompletionResponseGen:
        format_value = kwargs.pop("format", "json" if self.json_mode else None)

        def gen() -> CompletionResponseGen:
            response_txt = ""
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                stream=True,
                format=format_value,
                options=self._model_kwargs,
                keep_alive=self.keep_alive,
                **kwargs,
            )
            for chunk in response:
                raw = _plain_dict(chunk)
                delta = str(raw.get("response") or "")
                response_txt += delta
                token_counts = self._get_response_token_counts(raw)
                if token_counts:
                    raw["usage"] = token_counts
                yield CompletionResponse(
                    text=response_txt,
                    delta=delta,
                    raw=raw,
                )

        return gen()

    @llm_completion_callback()
    async def acomplete(
            self,
            prompt: str,
            formatted: bool = False,
            **kwargs: Any,
    ) -> CompletionResponse:
        format_value = kwargs.pop("format", "json" if self.json_mode else None)
        response = await self.async_client.generate(
            model=self.model,
            prompt=prompt,
            stream=False,
            format=format_value,
            options=self._model_kwargs,
            keep_alive=self.keep_alive,
            **kwargs,
        )
        raw = _plain_dict(response)
        token_counts = self._get_response_token_counts(raw)
        if token_counts:
            raw["usage"] = token_counts
        return CompletionResponse(
            text=str(raw.get("response") or ""),
            raw=raw,
        )

    @llm_completion_callback()
    async def astream_complete(
            self,
            prompt: str,
            formatted: bool = False,
            **kwargs: Any,
    ) -> CompletionResponseAsyncGen:
        format_value = kwargs.pop("format", "json" if self.json_mode else None)

        async def gen() -> CompletionResponseAsyncGen:
            response_txt = ""
            response = await self.async_client.generate(
                model=self.model,
                prompt=prompt,
                stream=True,
                format=format_value,
                options=self._model_kwargs,
                keep_alive=self.keep_alive,
                **kwargs,
            )
            async for chunk in response:
                raw = _plain_dict(chunk)
                delta = str(raw.get("response") or "")
                response_txt += delta
                token_counts = self._get_response_token_counts(raw)
                if token_counts:
                    raw["usage"] = token_counts
                yield CompletionResponse(
                    text=response_txt,
                    delta=delta,
                    raw=raw,
                )

        return gen()
