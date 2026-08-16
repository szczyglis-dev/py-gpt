#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.16 13:09:00                  #
# ================================================== #

import re
from typing import Optional, Any

def sanitize_name(name: str) -> str:
    """
    Sanitize name

    :param name: name
    :return: sanitized name
    """
    if name is None:
        return ""
    # allowed characters: a-z, A-Z, 0-9, _, and -
    name = name.strip().lower()
    sanitized_name = re.sub(r'[^a-z0-9_-]', '_', name)
    return sanitized_name[:64]  # limit to 64 characters


def capture_openai_usage(state, u_obj: Any):
    """
    Extract usage for OpenAI/xAI-compatible chunks.

    :param state: Chat state
    :param u_obj: Usage object/dict
    """
    if not u_obj:
        return
    state.usage_vendor = "openai"
    in_tok = as_int(safe_get(u_obj, "input_tokens")) or as_int(safe_get(u_obj, "prompt_tokens"))
    out_tok = as_int(safe_get(u_obj, "output_tokens")) or as_int(safe_get(u_obj, "completion_tokens"))
    total = as_int(safe_get(u_obj, "total_tokens"))
    reasoning = (
        as_int(safe_get(u_obj, "output_tokens_details.reasoning_tokens")) or
        as_int(safe_get(u_obj, "completion_tokens_details.reasoning_tokens")) or
        as_int(safe_get(u_obj, "reasoning_tokens")) or
        0
    )
    out_with_reason = (out_tok or 0) + (reasoning or 0)
    state.usage_payload = {"in": in_tok, "out": out_with_reason, "reasoning": reasoning or 0, "total": total}

def safe_get(obj: Any, path: str) -> Any:
    """
    Dot-path getter for dicts and objects.

    :param obj: Source object or dict
    :param path: Dot-separated path, e.g. 'a.b.0.c'
    :return: Value at path or None
    """
    cur = obj
    for seg in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(seg)
        else:
            if seg.isdigit() and isinstance(cur, (list, tuple)):
                idx = int(seg)
                if 0 <= idx < len(cur):
                    cur = cur[idx]
                else:
                    return None
            else:
                cur = getattr(cur, seg, None)
    return cur


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


def to_dict_safe(obj: Any) -> Optional[dict]:
    """
    Convert an SDK typed model or a plain mapping to dict safely.

    :param obj: Object to convert
    :return: Dict or None
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    try:
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
    except Exception:
        pass
    try:
        if hasattr(obj, "dict"):
            return obj.dict()
    except Exception:
        pass
    try:
        return dict(obj)
    except Exception:
        pass
    try:
        value = getattr(obj, "__dict__", None)
        return value if isinstance(value, dict) else None
    except Exception:
        return None


def get_annotation_type(annotation: Any) -> Optional[str]:
    """
    Return annotation type for both SDK objects and dicts.

    :param annotation: Annotation object
    :return: Annotation type or None
    """
    value = safe_get(annotation, "type")
    if isinstance(value, str) and value:
        return value
    data = to_dict_safe(annotation)
    if isinstance(data, dict):
        value = data.get("type")
        if isinstance(value, str) and value:
            return value
    return None


def extract_url_from_annotation(annotation: Any) -> Optional[str]:
    """
    Extract URL from an OpenAI url_citation annotation across SDK shapes.

    :param annotation: Annotation object
    :return: URL or None
    """
    for path in (
        "url",
        "url_citation.url",
        "url_citation.href",
        "href",
        "source_url",
    ):
        value = safe_get(annotation, path)
        if isinstance(value, str) and value:
            return value

    data = to_dict_safe(annotation)
    if isinstance(data, dict):
        for path in ("url", "url_citation.url", "url_citation.href", "href", "source_url"):
            value = safe_get(data, path)
            if isinstance(value, str) and value:
                return value
    return None


def append_unique_urls(target: Optional[list], urls) -> list:
    """
    Append non-empty URL strings to a list while preserving order and uniqueness.

    :param target: Existing URL list
    :param urls: Iterable of URL strings
    :return: URL list
    """
    if not isinstance(target, list):
        target = []
    seen = set(target)
    for url in urls or []:
        if not isinstance(url, str):
            continue
        url = url.strip()
        if not url or url in seen:
            continue
        target.append(url)
        seen.add(url)
    return target


def extract_response_urls(response: Any) -> list[str]:
    """
    Extract URLs used/cited by OpenAI Responses API.

    Sources are collected from two complementary locations:
      * output message url_citation annotations (inline citations),
      * web_search_call.action.sources (complete consulted source list when requested
        with include=["web_search_call.action.sources"]).

    The action URL itself is also collected for open_page/find_in_page web-search
    actions. This function accepts both SDK typed models and plain dict fixtures.

    :param response: OpenAI Response object or dict
    :return: Unique URL list in response order
    """
    urls = []
    outputs = safe_get(response, "output") or []

    for item in outputs:
        item_type = safe_get(item, "type")

        # Complete source list from hosted web search.
        if item_type == "web_search_call":
            action = safe_get(item, "action")
            action_url = safe_get(action, "url")
            if isinstance(action_url, str) and action_url:
                urls = append_unique_urls(urls, [action_url])

            sources = safe_get(action, "sources") or []
            source_urls = []
            for source in sources:
                source_url = safe_get(source, "url")
                if isinstance(source_url, str) and source_url:
                    source_urls.append(source_url)
            urls = append_unique_urls(urls, source_urls)

        # Inline citations are still important: they work without `include` and
        # are a fallback for SDK/API variants where sources are unavailable.
        content_items = safe_get(item, "content") or []
        for content in content_items:
            annotations = safe_get(content, "annotations") or []
            for annotation in annotations:
                if get_annotation_type(annotation) != "url_citation":
                    continue
                url = extract_url_from_annotation(annotation)
                if url:
                    urls = append_unique_urls(urls, [url])

    return urls

