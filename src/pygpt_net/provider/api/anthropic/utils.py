#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.09 16:40:00                  #
# ================================================== #

from typing import Any, Iterable, List, Optional, Set


def as_int(val: Any) -> Optional[int]:
    """
    Coerce to int if possible, else None.

    :param val: Input value
    :return: int or None
    """
    if val is None:
        return None
    try:
        return int(val)
    except Exception:
        try:
            return int(float(val))
        except Exception:
            return None


def get_field(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from an Anthropic SDK model or a plain dict."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    try:
        return getattr(obj, key, default)
    except Exception:
        return default


def _is_http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip()
    return value.startswith("http://") or value.startswith("https://")


def _append_url(out: List[str], seen: Set[str], value: Any) -> None:
    if not _is_http_url(value):
        return
    value = value.strip()
    if value not in seen:
        seen.add(value)
        out.append(value)


def extract_source_urls(value: Any, allowed_types: Iterable[str]) -> List[str]:
    """
    Recursively extract source URLs from Anthropic typed SDK objects or dicts.

    The Messages SDK returns Pydantic models for web search/fetch results and
    citation blocks, so callers must not assume result items are plain dicts.
    """
    allowed = set(allowed_types)
    out: List[str] = []
    seen: Set[str] = set()
    visited: Set[int] = set()

    def walk(obj: Any) -> None:
        if obj is None or isinstance(obj, (str, bytes, int, float, bool)):
            return

        oid = id(obj)
        if oid in visited:
            return
        visited.add(oid)

        if isinstance(obj, dict):
            obj_type = str(obj.get("type", "") or "")
            if obj_type in allowed:
                _append_url(out, seen, obj.get("url"))
                # search_result_location uses `source` instead of `url`.
                if obj_type == "search_result_location":
                    _append_url(out, seen, obj.get("source"))
            for child in obj.values():
                walk(child)
            return

        if isinstance(obj, (list, tuple, set)):
            for child in obj:
                walk(child)
            return

        obj_type = str(get_field(obj, "type", "") or "")
        if obj_type in allowed:
            _append_url(out, seen, get_field(obj, "url"))
            if obj_type == "search_result_location":
                _append_url(out, seen, get_field(obj, "source"))

        # Anthropic response objects are typed models. Walk only the fields
        # that can contain result/citation blocks to avoid traversing arbitrary
        # SDK internals.
        for field in ("content", "citations", "citation"):
            child = get_field(obj, field, None)
            if child is not None:
                walk(child)

    walk(value)
    return out


def extract_web_search_urls(value: Any) -> List[str]:
    """Extract all returned Web Search result URLs and cited Web Search URLs."""
    return extract_source_urls(
        value,
        {
            "web_search_result",
            "web_search_result_location",
        },
    )


def extract_web_fetch_urls(value: Any) -> List[str]:
    """Extract fetched page URLs from Anthropic Web Fetch result blocks."""
    return extract_source_urls(value, {"web_fetch_result"})


def append_ctx_urls(ctx: Any, urls: Iterable[str]) -> None:
    """Append unique URLs to ctx.urls while preserving provider order."""
    urls = list(urls or [])
    if not urls:
        return
    if getattr(ctx, "urls", None) is None:
        ctx.urls = []
    for url in urls:
        if not _is_http_url(url):
            continue
        clean = url.strip()
        if clean not in ctx.urls:
            ctx.urls.append(clean)

