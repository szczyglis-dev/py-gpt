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
        as_int(safe_get(um_obj, "thoughts_token_count")) or
        as_int(safe_get(um_obj, "candidates_reasoning_token_count")) or
        as_int(safe_get(um_obj, "reasoning_tokens")) or 0
    )
    if total is not None and prompt is not None:
        out_total = max(0, total - prompt)
    else:
        out_total = candidates
    state.usage_payload = {"in": prompt, "out": out_total, "reasoning": reasoning or 0, "total": total}


def extract_google_urls(payload: Any) -> list[str]:
    """
    Extract grounding/citation URLs from Google GenAI response data.

    Supports both ``google.genai`` response objects and the plain ``raw`` dict
    produced by LlamaIndex ``GoogleGenAI``. Modern Google Search grounding
    primarily exposes sources in ``grounding_metadata.grounding_chunks``.

    :param payload: Google response/candidate/raw dict
    :return: Unique http(s) URLs
    """
    urls: list[str] = []
    seen = set()

    def add(value):
        if not isinstance(value, str):
            return
        value = value.strip()
        if not (value.startswith("http://") or value.startswith("https://")):
            return
        if value in seen:
            return
        seen.add(value)
        urls.append(value)

    def scan_grounding(gm):
        if not gm:
            return

        # Current Gemini grounding format.
        chunks = safe_get(gm, "grounding_chunks") or safe_get(gm, "groundingChunks") or []
        try:
            for chunk in chunks or []:
                for path in (
                    "web.uri", "web.url",
                    "image.source_uri", "image.sourceUri",
                    "retrieved_context.uri", "retrieved_context.url",
                    "retrievedContext.uri", "retrievedContext.url",
                    "source.web.uri", "source.web.url",
                    "source.uri", "source.url",
                    "uri", "url",
                ):
                    add(safe_get(chunk, path))
        except Exception:
            pass

        # Older/alternate grounding attribution shapes.
        atts = safe_get(gm, "grounding_attributions") or safe_get(gm, "groundingAttributions") or []
        try:
            for att in atts or []:
                for path in (
                    "web.uri", "web.url",
                    "source.web.uri", "source.web.url",
                    "source.uri", "source.url",
                    "uri", "url",
                ):
                    add(safe_get(att, path))
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
            add(safe_get(gm, path))

    def scan_candidate(cand):
        if cand is None:
            return
        scan_grounding(safe_get(cand, "grounding_metadata") or safe_get(cand, "groundingMetadata"))

        cm = safe_get(cand, "citation_metadata") or safe_get(cand, "citationMetadata")
        if cm:
            arr = (
                safe_get(cm, "citation_sources") or
                safe_get(cm, "citationSources") or
                safe_get(cm, "citations") or []
            )
            try:
                for cit in arr or []:
                    for path in ("uri", "url", "source.uri", "source.url", "web.uri", "web.url"):
                        add(safe_get(cit, path))
            except Exception:
                pass

        try:
            parts = safe_get(cand, "content.parts") or []
            for part in parts:
                scan_grounding(safe_get(part, "grounding_metadata") or safe_get(part, "groundingMetadata"))
                pcm = safe_get(part, "citation_metadata") or safe_get(part, "citationMetadata")
                if pcm:
                    arr = (
                        safe_get(pcm, "citation_sources") or
                        safe_get(pcm, "citationSources") or
                        safe_get(pcm, "citations") or []
                    )
                    for cit in arr or []:
                        for path in ("uri", "url", "source.uri", "source.url", "web.uri", "web.url"):
                            add(safe_get(cit, path))
        except Exception:
            pass

    # Newer Gemini Interactions-style text annotations expose direct URL
    # citations instead of legacy groundingChunks. Keep this generic so the
    # same extractor works when the Google backend evolves.
    def scan_annotations(node):
        annotations = safe_get(node, "annotations") or []
        try:
            for annotation in annotations or []:
                if str(safe_get(annotation, "type") or "") in ("url_citation", "urlCitation", "url"):
                    add(safe_get(annotation, "url") or safe_get(annotation, "uri"))
        except Exception:
            pass

    output = safe_get(payload, "output") or []
    try:
        for item in output or []:
            scan_annotations(item)
            content = safe_get(item, "content") or []
            for part in content or []:
                scan_annotations(part)
    except Exception:
        pass
    scan_annotations(payload)

    # Full GenerateContentResponse.
    candidates = safe_get(payload, "candidates") or []
    if candidates:
        for cand in candidates:
            scan_candidate(cand)
    else:
        # LlamaIndex raw is usually top_candidate.model_dump(), not a full
        # GenerateContentResponse, so treat the payload itself as a candidate.
        scan_candidate(payload)

    return urls


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

    # Central extractor handles current groundingChunks plus newer annotation
    # formats. Keep the legacy scans below as compatibility fallback.
    try:
        for url in extract_google_urls(chunk):
            _add_url(url)
    except Exception:
        pass

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

    # Cover modern grounding_chunks and keep this helper aligned with the
    # Agents v2 Google adapter.
    for url in extract_google_urls(chunk):
        _add_url(url)

    if state.citations and (ctx.urls is None or not ctx.urls):
        ctx.urls = list(state.citations)
