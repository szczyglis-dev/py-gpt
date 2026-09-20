#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from __future__ import annotations

import re
from typing import Any, Iterable, Optional


def append_unique_urls(target: Optional[list], urls: Iterable[Any]) -> list:
    """Append unique non-empty URL strings while preserving provider order."""
    if not isinstance(target, list):
        target = []
    seen = set(target)
    for url in urls or []:
        if not isinstance(url, str):
            continue
        value = url.strip()
        if not value or value in seen:
            continue
        target.append(value)
        seen.add(value)
    return target


def drain_llm_urls(
        ctx,
        llm=None,
        *,
        response=None,
        provider: Optional[str] = None,
        on_error=None,
) -> list[str]:
    """Drain provider URL artifacts into ``ctx.urls``.

    There are two complementary sources:

    * provider adapters buffer URLs during Chat with Files / agent execution and
      expose them through ``pop_pygpt_urls``;
    * LlamaIndex workflow events expose the provider's raw response in
      ``AgentStream.raw`` / ``AgentOutput.raw``.  Reading that raw payload directly
      is important for streamed agents because the workflow may serialize/copy an
      LLM response before the final adapter instance is drained.

    Both paths merge into the same context list and are de-duplicated here.

    :return: URLs newly appended to the context
    """
    if ctx is None:
        return []

    urls: list[str] = []
    if llm is not None:
        pop_urls = getattr(llm, "pop_pygpt_urls", None)
        if callable(pop_urls):
            try:
                urls = append_unique_urls(urls, pop_urls() or [])
            except Exception as exc:
                if callable(on_error):
                    try:
                        on_error(exc)
                    except Exception:
                        pass

    if response is not None:
        try:
            urls = append_unique_urls(
                urls,
                extract_provider_urls(response, provider=provider),
            )
        except Exception as exc:
            if callable(on_error):
                try:
                    on_error(exc)
                except Exception:
                    pass

    if not urls:
        return []

    before = list(getattr(ctx, "urls", None) or [])
    before_set = set(before)
    merged = append_unique_urls(before, urls)
    ctx.urls = merged
    return [url for url in merged if url not in before_set]


def _get(value: Any, key: str, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    try:
        return getattr(value, key, default)
    except Exception:
        return default


def _to_plain(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list, tuple, set, str, int, float, bool)):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return model_dump(warnings=False)
        except TypeError:
            try:
                return model_dump()
            except Exception:
                pass
        except Exception:
            pass
    try:
        data = getattr(value, "__dict__", None)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return value


def _response_payloads(value: Any) -> list[Any]:
    """Return provider/raw metadata containers from a LlamaIndex response object."""
    out = []
    seen = set()

    def add(item):
        if item is None:
            return
        marker = id(item)
        if marker in seen:
            return
        seen.add(marker)
        out.append(item)

    add(value)
    raw = _get(value, "raw")
    add(raw)
    add(_get(raw, "response"))
    add(_get(value, "response"))
    add(_get(value, "additional_kwargs"))
    message = _get(value, "message")
    add(message)
    add(_get(message, "additional_kwargs"))
    return out


def extract_openai_urls(value: Any) -> list[str]:
    """Extract OpenAI Responses source/citation URLs from raw or LlamaIndex replies."""
    from pygpt_net.provider.api.openai.utils import (
        extract_response_urls,
        extract_url_from_annotation,
        get_annotation_type,
    )

    urls: list[str] = []
    for payload in _response_payloads(value):
        try:
            urls = append_unique_urls(urls, extract_response_urls(payload))
        except Exception:
            pass

        annotation = _get(payload, "annotation")
        if annotation is not None:
            try:
                if get_annotation_type(annotation) == "url_citation":
                    url = extract_url_from_annotation(annotation)
                    if url:
                        urls = append_unique_urls(urls, [url])
            except Exception:
                pass

        annotations = _get(payload, "annotations") or []
        try:
            for item in annotations:
                if get_annotation_type(item) != "url_citation":
                    continue
                url = extract_url_from_annotation(item)
                if url:
                    urls = append_unique_urls(urls, [url])
        except Exception:
            pass
    return urls


def _extract_declared_source_urls(value: Any) -> list[str]:
    """Extract URLs only from fields explicitly representing citations/sources.

    This intentionally does not crawl arbitrary text/object URLs. It is used as a
    compatibility fallback for xAI top-level ``citations`` and provider wrappers
    that expose citation metadata through LlamaIndex ``additional_kwargs``.
    """
    urls: list[str] = []
    seen = set()
    visited = set()
    source_fields = {
        "citation", "citations", "source", "sources", "annotations", "annotation",
        "citation_metadata", "citationmetadata", "grounding_metadata", "groundingmetadata",
        "web_search_call", "websearchcall", "action",
    }
    url_fields = {"url", "uri", "source_url", "sourceurl"}

    def add(candidate):
        if not isinstance(candidate, str):
            return
        candidate = candidate.strip()
        if not candidate.startswith(("http://", "https://")) or candidate in seen:
            return
        seen.add(candidate)
        urls.append(candidate)

    def add_from_text(text):
        if not isinstance(text, str):
            return
        for match in re.findall(r"https?://[^\s\]\)\}\>,\"']+", text):
            add(match)

    def walk(obj: Any, *, in_source: bool = False, key: str = "", depth: int = 0):
        if obj is None or depth > 12:
            return
        if isinstance(obj, str):
            if in_source and key in url_fields:
                add(obj)
            elif key in {"citation", "citations", "source", "sources"}:
                add_from_text(obj)
            return
        if isinstance(obj, (int, float, bool)):
            return

        marker = id(obj)
        if marker in visited:
            return
        visited.add(marker)

        if isinstance(obj, dict):
            for raw_key, child in obj.items():
                child_key = str(raw_key or "").lower()
                child_source = in_source or child_key in source_fields
                if child_source and child_key in url_fields:
                    if isinstance(child, str):
                        add(child)
                    else:
                        walk(child, in_source=True, key=child_key, depth=depth + 1)
                    continue
                walk(child, in_source=child_source, key=child_key, depth=depth + 1)
            return

        if isinstance(obj, (list, tuple, set)):
            for child in obj:
                if isinstance(child, str) and key in {"citation", "citations", "source", "sources"}:
                    add(child)
                else:
                    walk(child, in_source=in_source, key=key, depth=depth + 1)
            return

        plain = _to_plain(obj)
        if plain is not obj:
            walk(plain, in_source=in_source, key=key, depth=depth + 1)
            return

        # Last-resort typed response fields only; do not inspect arbitrary SDK state.
        for field in (
            "citations", "citation", "sources", "source", "annotations", "annotation",
            "action", "output", "content", "response",
        ):
            child = _get(obj, field)
            if child is not None:
                walk(
                    child,
                    in_source=in_source or field in source_fields,
                    key=field,
                    depth=depth + 1,
                )

    for payload in _response_payloads(value):
        walk(payload)
    return urls


def extract_anthropic_urls(value: Any) -> list[str]:
    """Extract Anthropic Web Search/Web Fetch URLs from raw or LlamaIndex replies."""
    from pygpt_net.provider.api.anthropic.utils import (
        extract_web_fetch_urls,
        extract_web_search_urls,
    )

    urls: list[str] = []
    for payload in _response_payloads(value):
        try:
            urls = append_unique_urls(urls, extract_web_search_urls(payload))
        except Exception:
            pass
        try:
            urls = append_unique_urls(urls, extract_web_fetch_urls(payload))
        except Exception:
            pass
    return append_unique_urls(urls, _extract_declared_source_urls(value))


def extract_xai_urls(value: Any) -> list[str]:
    """Extract xAI Responses citations plus OpenAI-compatible URL annotations."""
    urls = extract_openai_urls(value)
    return append_unique_urls(urls, _extract_declared_source_urls(value))


def extract_provider_urls(value: Any, provider: Optional[str] = None) -> list[str]:
    """Extract provider-native citation/source URLs from a raw workflow response.

    This intentionally supports only providers for which PyGPT already has
    canonical source extraction. Google Search grounding remains handled by its
    adapter because it can return opaque redirect URLs that should not be persisted
    as normal citations.
    """
    name = str(provider or "").strip().lower().replace("-", "_")
    if not name:
        return []
    compact = name.replace("_", "")
    if "anthropic" in compact or "claude" in compact:
        return extract_anthropic_urls(value)
    if "xai" in compact:
        return extract_xai_urls(value)
    if "openai" in compact:
        return extract_openai_urls(value)
    return []
