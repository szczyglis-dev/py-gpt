#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from __future__ import annotations

import warnings
from typing import Any, Sequence

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.llms.openai import OpenAIResponses


class AgentOpenAIResponses(OpenAIResponses):
    """OpenAI Responses adapter used by Agents v2.

    LlamaIndex's AgentWorkflow serializes every streaming ``ChatResponse.raw``
    with ``model_dump()`` before publishing an AgentStream event. Recent OpenAI
    Responses web-search payloads may contain source variants that are newer
    than the generated Pydantic union used by the installed SDK/integration.
    Pydantic can still represent those objects, but emits a long
    ``PydanticSerializationUnexpectedValue`` warning while dumping them.

    Agents v2 does not need a typed Pydantic object in ``raw`` after the OpenAI
    integration has parsed the response, so normalize it to a plain dict first.
    At the same time, collect web-search URLs so PyGPT can attach them to the
    visible CtxItem exactly like normal Chat/Responses does.
    """

    _pygpt_urls: list[str] = PrivateAttr(default_factory=list)

    @staticmethod
    def _safe_dump(value: Any) -> Any:
        """Convert a Pydantic/SDK object to plain data without serializer noise."""
        if value is None or isinstance(value, (dict, list, str, int, float, bool)):
            return value

        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            try:
                # Pydantic v2 supports disabling serializer warnings explicitly.
                return model_dump(warnings=False)
            except TypeError:
                # Compatibility fallback for older Pydantic signatures.
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        return model_dump()
                except Exception:
                    pass
            except Exception:
                pass

        try:
            return dict(value)
        except Exception:
            pass
        try:
            data = getattr(value, "__dict__", None)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return value

    def _append_urls(self, urls) -> None:
        seen = set(self._pygpt_urls)
        for url in urls or []:
            if not isinstance(url, str):
                continue
            value = url.strip()
            if not value or value in seen:
                continue
            self._pygpt_urls.append(value)
            seen.add(value)

    def _capture_raw_urls(self, raw: Any) -> None:
        """Capture URLs from a Responses API event or final Response object."""
        if raw is None:
            return
        try:
            # Lazy import avoids coupling provider registration/import order to
            # the full OpenAI API package.
            from pygpt_net.provider.api.openai.utils import (
                extract_response_urls,
                extract_url_from_annotation,
                get_annotation_type,
            )

            response = getattr(raw, "response", None)
            if response is not None:
                self._append_urls(extract_response_urls(response))
            else:
                self._append_urls(extract_response_urls(raw))

            # Streaming Responses exposes citation annotations before the final
            # ResponseCompletedEvent. Keep them as an additional fallback.
            annotation = getattr(raw, "annotation", None)
            if annotation is not None and get_annotation_type(annotation) == "url_citation":
                url = extract_url_from_annotation(annotation)
                if url:
                    self._append_urls([url])
        except Exception:
            # URL capture is metadata-only and must never break agent execution.
            pass

    def _prepare_response(self, response: ChatResponse) -> ChatResponse:
        raw = getattr(response, "raw", None)
        self._capture_raw_urls(raw)

        try:
            from pygpt_net.provider.api.openai.utils import (
                extract_url_from_annotation,
                get_annotation_type,
            )

            for annotation in (response.additional_kwargs or {}).get("annotations", []) or []:
                if get_annotation_type(annotation) != "url_citation":
                    continue
                url = extract_url_from_annotation(annotation)
                if url:
                    self._append_urls([url])
        except Exception:
            pass

        # Crucial: AgentWorkflow will otherwise call raw.model_dump() itself and
        # trigger Pydantic serializer warnings for hosted web-search payloads.
        response.raw = self._safe_dump(raw)
        return response

    def pop_pygpt_urls(self) -> list[str]:
        """Return and clear URLs collected since the previous drain."""
        urls = list(self._pygpt_urls)
        self._pygpt_urls.clear()
        return urls

    async def _achat(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ) -> ChatResponse:
        response = await super()._achat(messages, **kwargs)
        return self._prepare_response(response)

    async def _astream_chat(
            self,
            messages: Sequence[ChatMessage],
            **kwargs: Any,
    ):
        stream = await super()._astream_chat(messages, **kwargs)

        async def gen():
            async for response in stream:
                yield self._prepare_response(response)

        return gen()
