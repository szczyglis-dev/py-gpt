#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.05 20:00:00                  #
# ================================================== #

from typing import Any, Optional


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

def capture_google_usage(state, um_obj: Any):
    """
    Extract usage for Google python-genai; prefer total - prompt to include reasoning.

    :param state: Chat state
    :param um_obj: Usage metadata object/dict
    """
    if not um_obj:
        return
    state.usage_vendor = "google"
    prompt = (
        as_int(safe_get(um_obj, "prompt_token_count")) or
        as_int(safe_get(um_obj, "prompt_tokens")) or
        as_int(safe_get(um_obj, "input_tokens"))
    )
    total = (
        as_int(safe_get(um_obj, "total_token_count")) or
        as_int(safe_get(um_obj, "total_tokens"))
    )
    candidates = (
        as_int(safe_get(um_obj, "candidates_token_count")) or
        as_int(safe_get(um_obj, "output_tokens"))
    )
    reasoning = (
        as_int(safe_get(um_obj, "candidates_reasoning_token_count")) or
        as_int(safe_get(um_obj, "reasoning_tokens")) or 0
    )
    if total is not None and prompt is not None:
        out_total = max(0, total - prompt)
    else:
        out_total = candidates
    state.usage_payload = {"in": prompt, "out": out_total, "reasoning": reasoning or 0, "total": total}


def collect_google_citations(ctx, state, chunk: Any):
    """
    Collect web citations (URLs) from Google GenAI stream.

    :param ctx: Chat context
    :param state: Chat state
    :param chunk: Incoming streaming chunk
    """
    try:
        cands = getattr(chunk, "candidates", None) or []
    except Exception:
        cands = []

    if not isinstance(state.citations, list):
        state.citations = []

    def _add_url(url: Optional[str]):
        if not url or not isinstance(url, str):
            return
        url = url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            return
        if ctx.urls is None:
            ctx.urls = []
        if url not in state.citations:
            state.citations.append(url)
        if url not in ctx.urls:
            ctx.urls.append(url)

    for cand in cands:
        gm = safe_get(cand, "grounding_metadata") or safe_get(cand, "groundingMetadata")
        if gm:
            atts = safe_get(gm, "grounding_attributions") or safe_get(gm, "groundingAttributions") or []
            try:
                for att in atts or []:
                    for path in (
                        "web.uri",
                        "web.url",
                        "source.web.uri",
                        "source.web.url",
                        "source.uri",
                        "source.url",
                        "uri",
                        "url",
                    ):
                        _add_url(safe_get(att, path))
            except Exception:
                pass
            for path in (
                "search_entry_point.uri",
                "search_entry_point.url",
                "searchEntryPoint.uri",
                "searchEntryPoint.url",
                "search_entry_point.rendered_content_uri",
                "searchEntryPoint.rendered_content_uri",
            ):
                _add_url(safe_get(gm, path))

        cm = safe_get(cand, "citation_metadata") or safe_get(cand, "citationMetadata")
        if cm:
            cit_arrays = (
                safe_get(cm, "citation_sources") or
                safe_get(cm, "citationSources") or
                safe_get(cm, "citations") or []
            )
            try:
                for cit in cit_arrays or []:
                    for path in ("uri", "url", "source.uri", "source.url", "web.uri", "web.url"):
                        _add_url(safe_get(cit, path))
            except Exception:
                pass

        try:
            parts = safe_get(cand, "content.parts") or []
            for p in parts:
                pcm = safe_get(p, "citation_metadata") or safe_get(p, "citationMetadata")
                if pcm:
                    arr = (
                        safe_get(pcm, "citation_sources") or
                        safe_get(pcm, "citationSources") or
                        safe_get(pcm, "citations") or []
                    )
                    for cit in arr or []:
                        for path in ("uri", "url", "source.uri", "source.url", "web.uri", "web.url"):
                            _add_url(safe_get(cit, path))
                gpa = safe_get(p, "grounding_attributions") or safe_get(p, "groundingAttributions") or []
                for att in gpa or []:
                    for path in ("web.uri", "web.url", "source.web.uri", "source.web.url", "uri", "url"):
                        _add_url(safe_get(att, path))
        except Exception:
            pass

    if state.citations and (ctx.urls is None or not ctx.urls):
        ctx.urls = list(state.citations)