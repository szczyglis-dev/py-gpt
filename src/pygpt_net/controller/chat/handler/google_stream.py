#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.03 02:10:00                  #
# ================================================== #

import base64
import json
from typing import Optional, Any

from .utils import capture_google_usage, collect_google_citations


def process_google_chunk(ctx, core, state, chunk) -> Optional[str]:
    """
    Google python-genai streaming chunk.

    Supports:
    - Responses API streaming (generate_content)
    - Interactions API streaming (including Deep Research agent and generic interactions)

    :param ctx: Chat context
    :param core: Core controller
    :param state: Chat state
    :param chunk: Incoming streaming chunk
    :return: Extracted text delta or None
    """
    response_parts: list[str] = []

    if state.google_stream_ref is None:
        state.google_stream_ref = state.generator

    try:
        um = getattr(chunk, "usage_metadata", None)
        if um:
            capture_google_usage(state, um)
    except Exception:
        pass

    try:
        t = getattr(chunk, "text", None)
        if t:
            response_parts.append(t)
    except Exception:
        pass

    fc_list = []
    try:
        fc_list = getattr(chunk, "function_calls", None) or []
    except Exception:
        fc_list = []

    new_calls = []

    def _to_plain_dict(obj: Any):
        """Best-effort conversion of SDK objects to plain dict/list."""
        try:
            if hasattr(obj, "to_json_dict"):
                return obj.to_json_dict()
            if hasattr(obj, "model_dump"):
                return obj.model_dump()
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
        except Exception:
            pass
        if isinstance(obj, dict):
            return {k: _to_plain_dict(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_to_plain_dict(x) for x in obj]
        return obj

    def _get(obj: Any, name: str, default: Any = None) -> Any:
        """Safe getattr or dict get."""
        try:
            if hasattr(obj, name):
                return getattr(obj, name)
        except Exception:
            pass
        if isinstance(obj, dict):
            return obj.get(name, default)
        return default

    def _ensure_list_attr(obj: Any, name: str):
        """Ensure list attribute exists."""
        if not hasattr(obj, name) or not isinstance(getattr(obj, name), list):
            try:
                setattr(obj, name, [])
            except Exception:
                pass

    # Collect function calls from Responses API style stream
    if fc_list:
        for fc in fc_list:
            name = getattr(fc, "name", "") or ""
            args_obj = getattr(fc, "args", {}) or {}
            args_dict = _to_plain_dict(args_obj) or {}
            new_calls.append({
                "id": getattr(fc, "id", "") or "",
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(args_dict, ensure_ascii=False),
                }
            })
    else:
        try:
            cands = getattr(chunk, "candidates", None) or []
            for cand in cands:
                content = getattr(cand, "content", None)
                parts = getattr(content, "parts", None) or []
                for p in parts:
                    fn = getattr(p, "function_call", None)
                    if not fn:
                        continue
                    name = getattr(fn, "name", "") or ""
                    args_obj = getattr(fn, "args", {}) or {}
                    args_dict = _to_plain_dict(args_obj) or {}
                    new_calls.append({
                        "id": getattr(fn, "id", "") or "",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(args_dict, ensure_ascii=False),
                        }
                    })
        except Exception:
            pass

    # Interactions API / Deep Research: collect streaming deltas and metadata
    # Handles event_type, event_id, interaction.start/complete/status_update, and content.delta variants
    try:
        event_type = _get(chunk, "event_type", None)
        if event_type:
            # Track last event id for reconnection
            event_id = _get(chunk, "event_id", None)
            if event_id:
                try:
                    state.google_last_event_id = event_id
                except Exception:
                    pass
                try:
                    if not hasattr(ctx, "extra") or ctx.extra is None:
                        ctx.extra = {}
                    ctx.extra["google_last_event_id"] = event_id
                except Exception:
                    pass

            # Interaction lifecycle events
            if event_type == "interaction.start":
                interaction = _get(chunk, "interaction", None)
                interaction_id = _get(interaction, "id", None)
                if interaction_id:
                    try:
                        state.google_interaction_id = interaction_id
                    except Exception:
                        pass
                    try:
                        if not hasattr(ctx, "extra") or ctx.extra is None:
                            ctx.extra = {}
                        ctx.extra["google_interaction_id"] = interaction_id
                    except Exception:
                        pass

            elif event_type == "interaction.status_update":
                status = _get(chunk, "status", None)
                if status:
                    try:
                        state.google_interaction_status = status
                    except Exception:
                        pass
                    try:
                        if not hasattr(ctx, "extra") or ctx.extra is None:
                            ctx.extra = {}
                        ctx.extra["google_interaction_status"] = status
                    except Exception:
                        pass

            elif event_type == "interaction.complete":
                # Capture usage from the final interaction if available
                interaction = _get(chunk, "interaction", None)
                usage = _get(interaction, "usage", None)
                if usage:
                    try:
                        capture_google_usage(state, usage)
                    except Exception:
                        pass

            elif event_type == "error":
                err = _get(chunk, "error", {}) or {}
                try:
                    if not hasattr(ctx, "extra") or ctx.extra is None:
                        ctx.extra = {}
                    ctx.extra["google_interactions_error"] = _to_plain_dict(err)
                except Exception:
                    pass

            # Content deltas
            if event_type == "content.delta":
                delta = _get(chunk, "delta", {}) or {}
                delta_type = (_get(delta, "type", "") or "").lower()

                # Text delta
                if delta_type == "text":
                    txt = _get(delta, "text", None)
                    if txt:
                        response_parts.append(txt)

                # Thought summaries (Deep Research thinking summaries)
                elif delta_type in ("thought", "thought_summary"):
                    content_obj = _get(delta, "content", None)
                    thought_txt = None
                    if content_obj is not None:
                        # TextContent path
                        thought_txt = _get(content_obj, "text", None)
                    if thought_txt is None:
                        # Some SDKs expose 'thought' or 'content.text' differently
                        thought_txt = _get(delta, "thought", None)
                    if thought_txt:
                        _ensure_list_attr(state, "google_thought_summaries")
                        try:
                            state.google_thought_summaries.append(thought_txt)
                        except Exception:
                            pass
                        try:
                            if not hasattr(ctx, "extra") or ctx.extra is None:
                                ctx.extra = {}
                            if "google_thought_summaries" not in ctx.extra or not isinstance(ctx.extra["google_thought_summaries"], list):
                                ctx.extra["google_thought_summaries"] = []
                            ctx.extra["google_thought_summaries"].append(thought_txt)
                        except Exception:
                            pass

                # Function call delta (Interactions API tool/function calling)
                elif delta_type == "function_call":
                    fname = _get(delta, "name", "") or ""
                    fargs_obj = _get(delta, "arguments", {}) or {}
                    call_id = _get(delta, "id", "") or ""
                    fargs_dict = _to_plain_dict(fargs_obj) or {}
                    new_calls.append({
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": fname,
                            "arguments": json.dumps(fargs_dict, ensure_ascii=False),
                        }
                    })

                # Function result delta (optional store)
                elif delta_type == "function_result":
                    # Can be used to log tool results; not altering UI text
                    _ensure_list_attr(state, "google_function_results")
                    try:
                        state.google_function_results.append(_to_plain_dict(delta))
                    except Exception:
                        pass

                # Code execution: code + result
                elif delta_type == "code_execution_call":
                    lang = (_get(delta, "language", None) or "python").strip() or "python"
                    code_txt = _get(delta, "code", "") or ""
                    if not state.is_code:
                        response_parts.append(f"\n\n**Code interpreter**\n```{lang.lower()}\n{code_txt}")
                        state.is_code = True
                    else:
                        response_parts.append(str(code_txt))
                elif delta_type == "code_execution_result":
                    # Close code block; keep output logging internal if needed
                    if state.is_code:
                        response_parts.append("\n\n```\n-----------\n")
                        state.is_code = False
                    _ensure_list_attr(state, "google_code_results")
                    try:
                        state.google_code_results.append(_to_plain_dict(delta))
                    except Exception:
                        pass

                # Images in stream
                elif delta_type == "image":
                    # ImageDelta may contain base64 data or uri
                    mime = (_get(delta, "mime_type", "") or "").lower()
                    data_b64 = _get(delta, "data", None)
                    uri = _get(delta, "uri", None)
                    if data_b64:
                        try:
                            img_bytes = base64.b64decode(data_b64)
                            save_path = core.image.gen_unique_path(ctx)
                            with open(save_path, "wb") as f:
                                f.write(img_bytes)
                            if not isinstance(ctx.images, list):
                                ctx.images = []
                            ctx.images.append(save_path)
                            state.image_paths.append(save_path)
                            state.has_google_inline_image = True
                        except Exception:
                            pass
                    elif uri:
                        try:
                            if not hasattr(ctx, "urls") or ctx.urls is None:
                                ctx.urls = []
                            ctx.urls.append(uri)
                        except Exception:
                            pass

                # URL context call/result (Deep Research tool)
                elif delta_type == "url_context_call":
                    urls = _get(delta, "urls", []) or []
                    _ensure_list_attr(state, "google_url_context_calls")
                    try:
                        state.google_url_context_calls.append({"urls": list(urls)})
                    except Exception:
                        pass
                elif delta_type == "url_context_result":
                    url = _get(delta, "url", None)
                    status = _get(delta, "status", None)
                    _ensure_list_attr(state, "google_url_context_results")
                    try:
                        state.google_url_context_results.append({"url": url, "status": status, "raw": _to_plain_dict(delta)})
                    except Exception:
                        pass
                    if url:
                        try:
                            if not hasattr(ctx, "urls") or ctx.urls is None:
                                ctx.urls = []
                            ctx.urls.append(url)
                        except Exception:
                            pass

                # Google Search call/result (Deep Research tool)
                elif delta_type == "google_search_call":
                    queries = _get(delta, "queries", []) or []
                    _ensure_list_attr(state, "google_research_queries")
                    try:
                        state.google_research_queries.extend(list(queries))
                    except Exception:
                        pass
                elif delta_type == "google_search_result":
                    url = _get(delta, "url", None)
                    title = _get(delta, "title", None)
                    rendered = _get(delta, "rendered_content", None)
                    _ensure_list_attr(state, "google_search_results")
                    try:
                        state.google_search_results.append({
                            "url": url,
                            "title": title,
                            "rendered_content": rendered,
                            "raw": _to_plain_dict(delta),
                        })
                    except Exception:
                        pass
                    if url:
                        try:
                            if not hasattr(ctx, "urls") or ctx.urls is None:
                                ctx.urls = []
                            ctx.urls.append(url)
                        except Exception:
                            pass

                # File search results (optional)
                elif delta_type == "file_search_result":
                    _ensure_list_attr(state, "google_file_search_results")
                    try:
                        state.google_file_search_results.append(_to_plain_dict(delta))
                    except Exception:
                        pass

                # Thought signature delta (optional, store)
                elif delta_type == "thought_signature":
                    _ensure_list_attr(state, "google_thought_signatures")
                    try:
                        state.google_thought_signatures.append(_to_plain_dict(delta))
                    except Exception:
                        pass

                # Other modalities: audio/video/document (store URIs if available)
                elif delta_type in ("audio", "video", "document"):
                    uri = _get(delta, "uri", None)
                    if uri:
                        try:
                            if not hasattr(ctx, "urls") or ctx.urls is None:
                                ctx.urls = []
                            ctx.urls.append(uri)
                        except Exception:
                            pass

    except Exception:
        pass

    # Let Computer Use handler inspect chunk and tool calls (no-op if irrelevant)
    new_calls, has_calls = core.api.google.computer.handle_stream_chunk(ctx, chunk, new_calls)
    if has_calls:
        ctx.extra["function_response_required"] = True  # required for automatic with-screenshot response
        ctx.extra["function_response_source"] = "ctx.tool_calls"
        ctx.extra["function_response_reason"] = "computer_use"
        state.force_func_call = True

    if new_calls:
        seen = {(tc["function"]["name"], tc["function"]["arguments"]) for tc in state.tool_calls}
        for tc in new_calls:
            key = (tc["function"]["name"], tc["function"]["arguments"])
            if key not in seen:
                state.tool_calls.append(tc)
                seen.add(key)

    # Responses API-specific: parts parsing (code, images, file_data, etc.)
    try:
        cands = getattr(chunk, "candidates", None) or []
        for cand in cands:
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", None) or []

            for p in parts:
                ex = getattr(p, "executable_code", None)
                if ex:
                    lang = (getattr(ex, "language", None) or "python").strip() or "python"
                    code_txt = (
                        getattr(ex, "code", None) or
                        getattr(ex, "program", None) or
                        getattr(ex, "source", None) or
                        ""
                    )
                    if code_txt is None:
                        code_txt = ""
                    if not state.is_code:
                        response_parts.append(f"\n\n**Code interpreter**\n```{lang.lower()}\n{code_txt}")
                        state.is_code = True
                    else:
                        response_parts.append(str(code_txt))

                cer = getattr(p, "code_execution_result", None)
                if cer:
                    if state.is_code:
                        response_parts.append("\n\n```\n-----------\n")
                        state.is_code = False

                blob = getattr(p, "inline_data", None)
                if blob:
                    mime = (getattr(blob, "mime_type", "") or "").lower()
                    if mime.startswith("image/"):
                        data = getattr(blob, "data", None)
                        if data:
                            if isinstance(data, (bytes, bytearray)):
                                img_bytes = bytes(data)
                            else:
                                img_bytes = base64.b64decode(data)
                            save_path = core.image.gen_unique_path(ctx)
                            with open(save_path, "wb") as f:
                                f.write(img_bytes)
                            if not isinstance(ctx.images, list):
                                ctx.images = []
                            ctx.images.append(save_path)
                            state.image_paths.append(save_path)
                            state.has_google_inline_image = True

                fdata = getattr(p, "file_data", None)
                if fdata:
                    uri = getattr(fdata, "file_uri", None) or getattr(fdata, "uri", None)
                    mime = (getattr(fdata, "mime_type", "") or "").lower()
                    if uri and mime.startswith("image/") and (uri.startswith("http://") or uri.startswith("https://")):
                        if ctx.urls is None:
                            ctx.urls = []
                        ctx.urls.append(uri)

        collect_google_citations(ctx, state, chunk)

    except Exception:
        pass

    # Interactions API citations: try to collect from delta.annotations if present
    try:
        if _get(chunk, "event_type", None) == "content.delta":
            delta = _get(chunk, "delta", {}) or {}
            annotations = _get(delta, "annotations", None)
            if annotations:
                _ensure_list_attr(state, "google_annotations")
                try:
                    state.google_annotations.extend(_to_plain_dict(annotations) or [])
                except Exception:
                    pass
    except Exception:
        pass

    return "".join(response_parts) if response_parts else None