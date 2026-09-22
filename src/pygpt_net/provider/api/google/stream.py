#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.22 12:52:00                  #
# ================================================== #

import base64
import json
from typing import Optional, Any

from .utils import capture_google_usage, collect_google_citations
from pygpt_net.provider.api.reasoning import stream_reasoning_delta, stream_text_delta


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
    chunk_text: Optional[str] = None
    structured_text_seen = False
    interaction_text_seen = False

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
            chunk_text = str(t)
    except Exception:
        pass

    fc_list = []
    try:
        fc_list = getattr(chunk, "function_calls", None) or []
    except Exception:
        fc_list = []

    new_calls = []
    computer_use_active = bool(
        isinstance(getattr(ctx, "extra", None), dict)
        and ctx.extra.get("google_computer_use_active")
    )

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
        try:
            values = vars(obj)
            if isinstance(values, dict):
                return {k: _to_plain_dict(v) for k, v in values.items() if not str(k).startswith("_")}
        except Exception:
            pass
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

    def _try_download_uri(uri: Optional[str], prefer_name: Optional[str] = None) -> Optional[str]:
        """
        Attempt to download a Files API URI via store; return local path or None.
        """
        if not isinstance(uri, str) or not uri:
            return None
        try:
            path = core.api.google.store.download_to_dir(uri, prefer_name=prefer_name, ctx=ctx)
            return path
        except Exception:
            return None

    def _append_downloaded(paths):
        if not paths:
            return
        try:
            loc = core.filesystem.make_local_list(paths, ctx=ctx)
        except Exception:
            loc = paths
        if not isinstance(ctx.files, list):
            ctx.files = []
        for p in loc:
            if p not in ctx.files:
                ctx.files.append(p)
        # images
        imgs = []
        for p in loc:
            ext = p.lower().rsplit(".", 1)[-1] if "." in p else ""
            if ext in ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"]:
                imgs.append(p)
        if imgs:
            if not isinstance(ctx.images, list):
                ctx.images = []
            for p in imgs:
                if p not in ctx.images:
                    ctx.images.append(p)

    # Preserve Gemini's provider-facing model parts for the immediate Computer Use
    # FunctionResponse turn. In particular, Gemini 3 requires the opaque
    # thought_signature to be returned unchanged with the functionCall. Streaming
    # responses must capture it here because unpack_response() is not used.
    if computer_use_active:
        try:
            if not isinstance(ctx.extra, dict):
                ctx.extra = {}
            stored_parts = ctx.extra.setdefault("prev_model_parts", [])
            if not isinstance(stored_parts, list):
                stored_parts = []
                ctx.extra["prev_model_parts"] = stored_parts

            for cand in getattr(chunk, "candidates", None) or []:
                parts = getattr(getattr(cand, "content", None), "parts", None) or []
                dumped = core.api.google.chat._dump_model_parts(parts)
                for item in dumped:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") == "function_call":
                        # SDK streams may expose the same completed call through more than
                        # one aggregate chunk. Keep one protocol part per provider id/call.
                        item_id = str(item.get("id") or "")
                        fingerprint = (
                            item_id,
                            str(item.get("name") or ""),
                            json.dumps(item.get("args") or {}, sort_keys=True,
                                       ensure_ascii=False, default=str),
                        )
                        duplicate = False
                        for old in stored_parts:
                            if not isinstance(old, dict) or old.get("type") != "function_call":
                                continue
                            old_fp = (
                                str(old.get("id") or ""),
                                str(old.get("name") or ""),
                                json.dumps(old.get("args") or {}, sort_keys=True,
                                           ensure_ascii=False, default=str),
                            )
                            if old_fp == fingerprint:
                                duplicate = True
                                # Prefer the later copy if it carries a thought signature.
                                if item.get("thought_signature") is not None:
                                    old.update(item)
                                break
                        if not duplicate:
                            stored_parts.append(item)
                    elif item.get("type") == "text":
                        # Text parts are deltas in generate_content_stream; preserving them
                        # in arrival order recreates candidate.content without mixing them
                        # into the local tool call list.
                        stored_parts.append(item)
        except Exception:
            pass

    # GenerateContent thought summaries arrive as ordinary text parts carrying
    # part.thought=True. Parse parts directly so they are not mixed into the
    # final answer exposed by chunk.text.
    try:
        for cand in getattr(chunk, "candidates", None) or []:
            for part in getattr(getattr(cand, "content", None), "parts", None) or []:
                txt = getattr(part, "text", None)
                if not txt:
                    continue
                structured_text_seen = True
                if bool(getattr(part, "thought", False)):
                    delta = stream_reasoning_delta(
                        state, txt, provider="google", kind="thought_summary", raw=False,
                    )
                else:
                    delta = stream_text_delta(state, txt)
                if delta:
                    response_parts.append(delta)
    except Exception:
        pass

    # Collect ordinary Google function calls. Computer Use is intentionally excluded:
    # its raw Gemini name (e.g. ``hotkey``) must not be added here and then added a
    # second time by computer.handle_stream_chunk() as the mapped local command
    # (e.g. ``keyboard_keys``). That double path caused every action to run twice.
    if not computer_use_active:
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
                        # Download Files API file_data parts if present
                        try:
                            fdata = getattr(p, "file_data", None)
                            if fdata:
                                uri = getattr(fdata, "file_uri", None) or getattr(fdata, "uri", None)
                                name = getattr(fdata, "file_name", None) or getattr(fdata, "display_name", None)
                                if uri and isinstance(uri, str):
                                    if not hasattr(state, "google_downloaded_uris"):
                                        state.google_downloaded_uris = set()
                                    if uri not in state.google_downloaded_uris:
                                        save = _try_download_uri(uri, name)
                                        if save:
                                            _append_downloaded([save])
                                            state.google_downloaded_uris.add(uri)
                        except Exception:
                            pass

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

    # Interactions API / Deep Research: collect streaming deltas and metadata.
    # google-genai 2.x migrated from content.* to step.* events and from outputs
    # to steps. Keep the legacy aliases so 1.75-era streams remain readable.
    try:
        event_type = _get(chunk, "event_type", None) or _get(chunk, "type", None)
        event_type = str(event_type or "").strip().lower()

        def _ensure_extra():
            if not hasattr(ctx, "extra") or not isinstance(ctx.extra, dict):
                ctx.extra = {}
            return ctx.extra

        def _normalize_scalar(value):
            try:
                return getattr(value, "value", value)
            except Exception:
                return value

        def _append_ctx_url(url):
            if not isinstance(url, str):
                return
            url = url.strip()
            if not url.startswith(("http://", "https://")):
                return
            if not isinstance(getattr(ctx, "urls", None), list):
                ctx.urls = []
            if url not in ctx.urls:
                ctx.urls.append(url)

        def _collect_urls(node, depth=0):
            if node is None or depth > 6:
                return
            plain = _to_plain_dict(node)
            if isinstance(plain, dict):
                for key, value in plain.items():
                    normalized = str(key).lower().replace("-", "_")
                    if normalized in ("url", "uri", "source_url", "source_uri"):
                        _append_ctx_url(value)
                    if isinstance(value, (dict, list, tuple)):
                        _collect_urls(value, depth + 1)
            elif isinstance(plain, (list, tuple)):
                for value in plain:
                    _collect_urls(value, depth + 1)

        def _capture_interaction(interaction, fallback_status=None, fallback_id=None):
            if interaction is None and fallback_status is None and fallback_id is None:
                return
            interaction_id = (
                _get(interaction, "id", None) if interaction is not None else None
            ) or fallback_id
            status = _get(interaction, "status", None) if interaction is not None else None
            status = status or fallback_status
            if interaction_id:
                interaction_id = str(_normalize_scalar(interaction_id))
                try:
                    state.google_interaction_id = interaction_id
                except Exception:
                    pass
                extra_ctx = _ensure_extra()
                extra_ctx["google_interaction_id"] = interaction_id
                extra_ctx["google_last_interaction_id"] = interaction_id
            if status:
                status = str(_normalize_scalar(status))
                try:
                    state.google_interaction_status = status
                except Exception:
                    pass
                _ensure_extra()["google_interaction_status"] = status
            usage = _get(interaction, "usage", None) if interaction is not None else None
            if usage:
                capture_google_usage(state, usage)
            _collect_urls(interaction)

        def _pending_calls():
            pending = getattr(state, "google_interaction_pending_calls", None)
            if not isinstance(pending, dict):
                pending = {}
                try:
                    state.google_interaction_pending_calls = pending
                except Exception:
                    pass
            return pending

        def _flush_pending_call(index):
            pending = _pending_calls()
            item = pending.pop(index, None)
            if not item:
                return
            arguments = item.get("arguments", "")
            if isinstance(arguments, dict):
                arguments = json.dumps(arguments, ensure_ascii=False)
            elif arguments is None:
                arguments = ""
            else:
                arguments = str(arguments)
            if not arguments.strip():
                arguments = "{}"
            new_calls.append({
                "id": item.get("id", "") or "",
                "type": "function",
                "function": {
                    "name": item.get("name", "") or "",
                    "arguments": arguments,
                },
            })

        if event_type:
            # Track last event id for reconnection/resume.
            event_id = _get(chunk, "event_id", None)
            if event_id:
                try:
                    state.google_last_event_id = event_id
                except Exception:
                    pass
                _ensure_extra()["google_last_event_id"] = event_id

            # Interaction lifecycle.
            if event_type in ("interaction.start", "interaction.created"):
                _capture_interaction(_get(chunk, "interaction", None) or chunk)
            elif event_type == "interaction.status_update":
                status = _get(chunk, "status", None)
                interaction = _get(chunk, "interaction", None)
                _capture_interaction(
                    interaction,
                    fallback_status=status,
                    fallback_id=_get(chunk, "interaction_id", None),
                )
            elif event_type in ("interaction.in_progress", "interaction.requires_action"):
                _capture_interaction(
                    _get(chunk, "interaction", None),
                    fallback_status=event_type.split(".", 1)[1],
                    fallback_id=_get(chunk, "interaction_id", None),
                )
            elif event_type in ("interaction.complete", "interaction.completed"):
                # Flush any function call whose step.stop was omitted by an old
                # or interrupted stream implementation before storing final usage.
                for index in list(_pending_calls().keys()):
                    _flush_pending_call(index)
                _capture_interaction(_get(chunk, "interaction", None) or chunk)
            elif event_type in ("error", "interaction.error", "interaction.failed"):
                err = _get(chunk, "error", None) or _get(_get(chunk, "interaction", None), "error", None) or {}
                _ensure_extra()["google_interactions_error"] = _to_plain_dict(err)
                _capture_interaction(_get(chunk, "interaction", None), fallback_status="failed")

            # New 2.x function-call metadata arrives in step.start; argument JSON
            # then arrives incrementally as arguments_delta events.
            if event_type == "step.start":
                step = _get(chunk, "step", {}) or {}
                index = _get(chunk, "index", 0)
                step_type = str(_normalize_scalar(_get(step, "type", "")) or "").lower()
                if step_type == "function_call":
                    initial_args = _get(step, "arguments", "")
                    if isinstance(initial_args, dict):
                        initial_args = json.dumps(initial_args, ensure_ascii=False) if initial_args else ""
                    _pending_calls()[index] = {
                        "id": _get(step, "id", "") or "",
                        "name": _get(step, "name", "") or "",
                        "arguments": initial_args or "",
                    }
                elif step_type:
                    _ensure_list_attr(state, "google_interaction_steps")
                    state.google_interaction_steps.append(_to_plain_dict(step))
                    _collect_urls(step)

            elif event_type == "step.stop":
                index = _get(chunk, "index", 0)
                if index in _pending_calls():
                    _flush_pending_call(index)
                # 2.x may report cumulative interaction usage on step.stop
                # (and step_usage separately). Prefer the cumulative value so
                # the token counter remains correct before interaction.completed.
                stop_usage = _get(chunk, "usage", None)
                if stop_usage:
                    capture_google_usage(state, stop_usage)

            # Legacy 1.x used content.delta; 2.x uses step.delta.
            if event_type in ("content.delta", "step.delta"):
                delta = _get(chunk, "delta", {}) or {}
                delta_type = str(_normalize_scalar(_get(delta, "type", "")) or "").lower()

                # Step metadata can carry cumulative usage before final completion.
                metadata = _get(chunk, "metadata", None) or _get(delta, "metadata", None)
                total_usage = _get(metadata, "total_usage", None) if metadata else None
                if total_usage:
                    capture_google_usage(state, total_usage)

                # Text delta.
                if delta_type == "text":
                    txt = _get(delta, "text", None)
                    if txt:
                        interaction_text_seen = True
                        rendered = stream_text_delta(state, txt)
                        if rendered:
                            response_parts.append(rendered)

                # Thought summaries. Old schemas may expose type=thought/text.
                elif delta_type in ("thought", "thought_summary"):
                    content_obj = _get(delta, "content", None)
                    thought_txt = _get(content_obj, "text", None) if content_obj is not None else None
                    thought_txt = thought_txt or _get(delta, "text", None) or _get(delta, "thought", None)
                    if thought_txt:
                        rendered = stream_reasoning_delta(
                            state, thought_txt, provider="google",
                            kind="thought_summary", raw=False,
                        )
                        if rendered:
                            response_parts.append(rendered)
                        if bool(getattr(state, "reasoning_enabled", True)):
                            _ensure_list_attr(state, "google_thought_summaries")
                            state.google_thought_summaries.append(thought_txt)
                            extra_ctx = _ensure_extra()
                            if not isinstance(extra_ctx.get("google_thought_summaries"), list):
                                extra_ctx["google_thought_summaries"] = []
                            extra_ctx["google_thought_summaries"].append(thought_txt)

                # 2.x streams function arguments as JSON string fragments.
                elif delta_type in ("arguments_delta", "arguments"):
                    index = _get(chunk, "index", 0)
                    pending = _pending_calls().get(index)
                    if pending is not None:
                        fragment = _get(delta, "arguments", None)
                        if fragment is None:
                            fragment = _get(delta, "partial_arguments", "")
                        pending["arguments"] = str(pending.get("arguments", "") or "") + str(fragment or "")

                # Legacy Interactions function-call delta.
                elif delta_type == "function_call":
                    fname = _get(delta, "name", "") or ""
                    fargs_obj = _get(delta, "arguments", {}) or {}
                    call_id = _get(delta, "id", "") or ""
                    fargs = _to_plain_dict(fargs_obj) or {}
                    if not isinstance(fargs, str):
                        fargs = json.dumps(fargs, ensure_ascii=False)
                    new_calls.append({
                        "id": call_id,
                        "type": "function",
                        "function": {"name": fname, "arguments": fargs},
                    })

                elif delta_type == "function_result":
                    _ensure_list_attr(state, "google_function_results")
                    state.google_function_results.append(_to_plain_dict(delta))

                # Code execution.
                elif delta_type == "code_execution_call":
                    arguments = _get(delta, "arguments", None)
                    lang = (_get(delta, "language", None) or _get(arguments, "language", None) or "python")
                    lang = str(lang).strip() or "python"
                    code_txt = _get(delta, "code", None) or _get(arguments, "code", None) or ""
                    if not state.is_code:
                        response_parts.append(f"\n\n**Code interpreter**\n```{lang.lower()}\n{code_txt}")
                        state.is_code = True
                    else:
                        response_parts.append(str(code_txt))
                elif delta_type == "code_execution_result":
                    if state.is_code:
                        response_parts.append("\n\n```\n-----------\n")
                        state.is_code = False
                    _ensure_list_attr(state, "google_code_results")
                    state.google_code_results.append(_to_plain_dict(delta))

                # Images in stream.
                elif delta_type == "image":
                    data_b64 = _get(delta, "data", None)
                    uri = _get(delta, "uri", None)
                    if data_b64:
                        try:
                            img_bytes = bytes(data_b64) if isinstance(data_b64, (bytes, bytearray)) else base64.b64decode(data_b64)
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
                        save = _try_download_uri(uri)
                        if save:
                            _append_downloaded([save])
                        else:
                            _append_ctx_url(uri)

                # URL Context server tool. 2.x nests call args under arguments
                # and returns result arrays; 1.x exposed direct fields.
                elif delta_type == "url_context_call":
                    args_obj = _get(delta, "arguments", None)
                    urls = _get(args_obj, "urls", None) or _get(delta, "urls", []) or []
                    if isinstance(urls, str):
                        urls = [urls]
                    _ensure_list_attr(state, "google_url_context_calls")
                    state.google_url_context_calls.append({"urls": list(urls), "raw": _to_plain_dict(delta)})
                    for url in urls:
                        _append_ctx_url(url)
                elif delta_type == "url_context_result":
                    results = _get(delta, "result", None)
                    if results is None:
                        results = [delta]
                    elif not isinstance(results, (list, tuple)):
                        results = [results]
                    _ensure_list_attr(state, "google_url_context_results")
                    for result in results:
                        state.google_url_context_results.append(_to_plain_dict(result))
                        _collect_urls(result)

                # Google Search server tool.
                elif delta_type == "google_search_call":
                    args_obj = _get(delta, "arguments", None)
                    queries = _get(args_obj, "queries", None) or _get(delta, "queries", []) or []
                    if isinstance(queries, str):
                        queries = [queries]
                    _ensure_list_attr(state, "google_research_queries")
                    state.google_research_queries.extend(list(queries))
                elif delta_type == "google_search_result":
                    _ensure_list_attr(state, "google_search_results")
                    state.google_search_results.append(_to_plain_dict(delta))
                    _collect_urls(delta)

                # File Search and 2.24 retrieval steps.
                elif delta_type in ("file_search_call", "file_search_result"):
                    attr = "google_file_search_calls" if delta_type.endswith("_call") else "google_file_search_results"
                    _ensure_list_attr(state, attr)
                    getattr(state, attr).append(_to_plain_dict(delta))
                    _collect_urls(delta)
                elif delta_type in ("retrieval_call", "retrieval_result"):
                    attr = "google_retrieval_calls" if delta_type.endswith("_call") else "google_retrieval_results"
                    _ensure_list_attr(state, attr)
                    getattr(state, attr).append(_to_plain_dict(delta))
                    _collect_urls(delta)

                # Other server-side tools introduced across 2.x. Preserve the
                # raw payload even when PyGPT has no dedicated renderer yet.
                elif delta_type in (
                    "processing_call", "processing_result",
                    "google_maps_call", "google_maps_result",
                    "mcp_server_tool_call", "mcp_server_tool_result",
                ):
                    _ensure_list_attr(state, "google_server_tool_events")
                    state.google_server_tool_events.append(_to_plain_dict(delta))
                    _collect_urls(delta)

                elif delta_type == "thought_signature":
                    _ensure_list_attr(state, "google_thought_signatures")
                    state.google_thought_signatures.append(_to_plain_dict(delta))

                # 2.x may stream annotations separately from text. Preserve the
                # full annotation delta and collect any source URLs it carries.
                elif delta_type == "text_annotation_delta":
                    _ensure_list_attr(state, "google_annotations")
                    state.google_annotations.append(_to_plain_dict(delta))
                    _collect_urls(delta)

                # Other modalities: audio/video/document.
                elif delta_type in ("audio", "video", "document"):
                    uri = _get(delta, "uri", None)
                    if uri:
                        save = _try_download_uri(uri)
                        if save:
                            _append_downloaded([save])
                        else:
                            _append_ctx_url(uri)

                _collect_urls(delta)

    except Exception:
        pass

    # response.text is a convenient SDK aggregate for normal chunks, but when
    # include_thoughts is enabled it is safer to prefer the structured parts
    # above so summaries and final output remain separated.
    if chunk_text and not structured_text_seen and not interaction_text_seen:
        rendered = stream_text_delta(state, chunk_text)
        if rendered:
            response_parts.append(rendered)

    # Let the Computer Use handler inspect chunks only for an active Computer
    # session; ordinary Google function calls must keep their normal flow.
    if computer_use_active:
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
                    prefer = getattr(fdata, "file_name", None) or getattr(fdata, "display_name", None)
                    if uri:
                        if not hasattr(state, "google_downloaded_uris"):
                            state.google_downloaded_uris = set()
                        if uri not in state.google_downloaded_uris:
                            save = _try_download_uri(uri, prefer)
                            if save:
                                _append_downloaded([save])
                                state.google_downloaded_uris.add(uri)
                        # keep original behavior for image http links
                        mime = (getattr(fdata, "mime_type", "") or "").lower()
                        if uri.startswith(("http://", "https://")) and mime.startswith("image/"):
                            if ctx.urls is None:
                                ctx.urls = []
                            ctx.urls.append(uri)

        collect_google_citations(ctx, state, chunk)

    except Exception:
        pass

    # Interactions API citations: try to collect from delta.annotations if present
    try:
        if (_get(chunk, "event_type", None) or _get(chunk, "type", None)) in ("content.delta", "step.delta"):
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