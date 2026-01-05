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

from typing import Optional, List, Dict, Any
import base64
import re


def _stringify_content(content) -> Optional[str]:
    """
    Convert various xAI content shapes into a plain text string.
    Handles:
    - str
    - list of parts (dicts with {'type':'text','text':...} or str)
    - objects with .text or .content attributes
    - dict with 'text' or nested shapes
    """
    try:
        if content is None:
            return None
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            buf: List[str] = []
            for p in content:
                if isinstance(p, str):
                    buf.append(p)
                elif isinstance(p, dict):
                    if isinstance(p.get("text"), str):
                        buf.append(p["text"])
                    elif isinstance(p.get("content"), str):
                        buf.append(p["content"])
                    elif isinstance(p.get("delta"), str):
                        buf.append(p["delta"])
                else:
                    t = getattr(p, "text", None)
                    if isinstance(t, str):
                        buf.append(t)
            return "".join(buf) if buf else None
        if isinstance(content, dict):
            if isinstance(content.get("text"), str):
                return content["text"]
            if isinstance(content.get("content"), str):
                return content["content"]
            if isinstance(content.get("delta"), str):
                return content["delta"]
        t = getattr(content, "text", None)
        if isinstance(t, str):
            return t
        c = getattr(content, "content", None)
        if isinstance(c, str):
            return c
        return str(content)
    except Exception:
        return None


def _extract_http_urls_from_text(text: Optional[str]) -> List[str]:
    """
    Extract http(s) URLs from plain text.
    """
    if not text or not isinstance(text, str):
        return []
    pattern = re.compile(r"(https?://[^\s)>\]\"']+)", re.IGNORECASE)
    urls = pattern.findall(text)
    out, seen = [], set()
    for u in urls:
        if u not in seen:
            out.append(u)
            seen.add(u)
    return out


def _append_urls(ctx, state, urls: List[str]):
    """
    Merge a list of URLs into state.citations and ctx.urls (unique, http/https only).
    """
    if not urls:
        return
    if not isinstance(state.citations, list):
        state.citations = []
    if ctx.urls is None:
        ctx.urls = []
    seen = set(state.citations) | set(ctx.urls)
    for u in urls:
        if not isinstance(u, str):
            continue
        if not (u.startswith("http://") or u.startswith("https://")):
            continue
        if u in seen:
            continue
        state.citations.append(u)
        ctx.urls.append(u)
        seen.add(u)


def _try_save_data_url_image(core, ctx, data_url: str) -> Optional[str]:
    """
    Save data:image/*;base64,... to file and return path.
    """
    try:
        if not data_url.startswith("data:image/"):
            return None
        header, b64 = data_url.split(",", 1)
        ext = "png"
        if ";base64" in header:
            mime = header.split(";")[0].split(":")[1].lower()
            if "jpeg" in mime or "jpg" in mime:
                ext = "jpg"
            elif "png" in mime:
                ext = "png"
        img_bytes = base64.b64decode(b64)
        save_path = core.image.gen_unique_path(ctx, ext=ext)
        with open(save_path, "wb") as f:
            f.write(img_bytes)
        return save_path
    except Exception:
        return None


def _process_message_content_for_outputs(core, ctx, state, content):
    """
    Inspect assistant message content (list of parts) for image_url outputs and URLs.
    - If image_url.url is data:... -> save to file and append to state.image_paths + ctx.images
    - If image_url.url is http(s) -> append to ctx.urls
    - Extract URLs from adjacent text parts conservatively
    - If file part present -> auto-download via Files API
    """
    if not isinstance(content, list):
        return
    any_image = False
    for p in content:
        if not isinstance(p, dict):
            continue
        ptype = p.get("type")
        if ptype == "image_url":
            img = p.get("image_url") or {}
            url = img.get("url")
            if isinstance(url, str):
                if url.startswith("data:image/"):
                    path = _try_save_data_url_image(core, ctx, url)
                    if path:
                        if not isinstance(ctx.images, list):
                            ctx.images = []
                        ctx.images.append(path)
                        state.image_paths.append(path)
                        any_image = True
                elif url.startswith("http://") or url.startswith("https://"):
                    _append_urls(ctx, state, [url])
        elif ptype == "text":
            t = p.get("text")
            if isinstance(t, str):
                urls = _extract_http_urls_from_text(t)
                if urls:
                    _append_urls(ctx, state, urls)
        elif ptype == "file":
            fid = p.get("id") or p.get("file_id")
            if isinstance(fid, str):
                if not hasattr(state, "xai_downloaded_file_ids"):
                    state.xai_downloaded_file_ids = set()
                if fid not in state.xai_downloaded_file_ids:
                    try:
                        path = core.api.xai.store.download_to_dir(fid)
                    except Exception:
                        path = None
                    if path:
                        if not isinstance(ctx.files, list):
                            ctx.files = []
                        if path not in ctx.files:
                            ctx.files.append(path)
                        ext = path.lower().rsplit(".", 1)[-1] if "." in path else ""
                        if ext in ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"]:
                            if not isinstance(ctx.images, list):
                                ctx.images = []
                            if path not in ctx.images:
                                ctx.images.append(path)
                        state.xai_downloaded_file_ids.add(fid)
    if any_image:
        try:
            state.has_xai_inline_image = True
        except Exception:
            pass


def _merge_tool_calls(state, new_calls: List[Dict[str, Any]]):
    """
    Merge a list of tool_calls (dict-like) into state.tool_calls with de-duplication and streaming concat of arguments.
    """
    if not new_calls:
        return
    if not isinstance(state.tool_calls, list):
        state.tool_calls = []

    def _norm(tc: Dict[str, Any]) -> Dict[str, Any]:
        fn = tc.get("function") or {}
        args = fn.get("arguments")
        if isinstance(args, (dict, list)):
            try:
                import json as _json
                args = _json.dumps(args, ensure_ascii=False)
            except Exception:
                args = str(args)
        return {
            "id": tc.get("id") or "",
            "type": "function",
            "function": {
                "name": fn.get("name") or "",
                "arguments": args or "",
            },
        }

    def _find_existing(key_id: str, key_name: str) -> Optional[Dict[str, Any]]:
        if not state.tool_calls:
            return None
        for ex in state.tool_calls:
            if key_id and ex.get("id") == key_id:
                return ex
            if key_name and ex.get("function", {}).get("name") == key_name:
                # name match as fallback for SDKs that stream without ids
                return ex
        return None

    for tc in new_calls:
        if not isinstance(tc, dict):
            continue
        nid = tc.get("id") or ""
        fn = tc.get("function") or {}
        nname = fn.get("name") or ""
        nargs = fn.get("arguments")
        if isinstance(nargs, (dict, list)):
            try:
                import json as _json
                nargs = _json.dumps(nargs, ensure_ascii=False)
            except Exception:
                nargs = str(nargs)

        existing = _find_existing(nid, nname)
        if existing is None:
            state.tool_calls.append(_norm(tc))
        else:
            if nname:
                existing["function"]["name"] = nname
            if nargs:
                existing["function"]["arguments"] = (existing["function"].get("arguments", "") or "") + str(nargs)


def _maybe_collect_tail_meta(state, obj: Dict[str, Any], ctx=None):
    """
    Collect tail metadata like citations and usage into state (and ctx for urls), if these fields exist.
    """
    try:
        if not isinstance(obj, dict):
            return
        if "citations" in obj:
            c = obj.get("citations") or []
            if isinstance(c, list):
                if ctx is not None:
                    _append_urls(ctx, state, [u for u in c if isinstance(u, str)])
                else:
                    try:
                        setattr(state, "xai_stream_citations", c)
                    except Exception:
                        pass
        if "usage" in obj and isinstance(obj["usage"], dict):
            try:
                state.usage_vendor = "xai"
                u = obj["usage"]
                def _as_int(v):
                    try:
                        return int(v)
                    except Exception:
                        try:
                            return int(float(v))
                        except Exception:
                            return 0
                p = _as_int(u.get("prompt_tokens") or u.get("input_tokens") or 0)
                c = _as_int(u.get("completion_tokens") or u.get("output_tokens") or 0)
                r = _as_int(u.get("reasoning_tokens") or 0)
                t = _as_int(u.get("total_tokens") or (p + c + r))
                state.usage_payload = {"in": p, "out": max(0, t - p) if t else c, "reasoning": r, "total": t}
            except Exception:
                pass
    except Exception:
        pass


def process_xai_sdk_chunk(ctx, core, state, item) -> Optional[str]:
    """
    xAI SDK native streaming chunk.

    :param ctx: Chat context
    :param core: Core controller
    :param state: Chat state
    :param item: Incoming streaming chunk; supports:
                 - tuple(response, chunk) [old/new SDK style]
                 - chunk object with .delta/.content/.tool_calls/.tool_outputs/.citations
                 - dict/SimpleNamespace with OpenAI-like choices[0].delta.content
                 - dict event style with root 'delta' or 'message'
    :return: Extracted text delta or None
    """
    response = None
    chunk = None
    try:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            response, chunk = item
        else:
            chunk = item
    except Exception:
        return None

    # persist last response and attach response id to ctx once
    try:
        if response is not None:
            state.xai_last_response = response
            rid = getattr(response, "id", None)
            if rid and not getattr(ctx, "msg_id", None):
                ctx.msg_id = str(rid)
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra["xai_response_id"] = ctx.msg_id
                try:
                    core.ctx.update_item(ctx)
                except Exception:
                    pass
    except Exception:
        pass

    # Citations at chunk-level (last chunk in live search)
    try:
        cites = getattr(chunk, "citations", None)
        if cites and isinstance(cites, list):
            _append_urls(ctx, state, [u for u in cites if isinstance(u, str)])
    except Exception:
        pass

    # Tool calls emitted as dedicated SDK objects
    try:
        tc_list = getattr(chunk, "tool_calls", None) or []
        if tc_list:
            norm_list = []
            for tc in tc_list:
                if tc is None:
                    continue
                fn = getattr(tc, "function", None)
                name = getattr(fn, "name", "") if fn is not None else ""
                args = getattr(fn, "arguments", "") if fn is not None else ""
                if isinstance(args, (dict, list)):
                    try:
                        import json as _json
                        args = _json.dumps(args, ensure_ascii=False)
                    except Exception:
                        args = str(args)
                norm_list.append({
                    "id": getattr(tc, "id", "") or "",
                    "type": "function",
                    "function": {"name": name or "", "arguments": args or ""},
                })
            if norm_list:
                _merge_tool_calls(state, norm_list)
                state.force_func_call = True
    except Exception:
        pass

    # Tool outputs: scan for URLs to enrich ctx.urls (best effort)
    try:
        to_list = getattr(chunk, "tool_outputs", None) or []
        for to in to_list:
            content = getattr(to, "content", None)
            if isinstance(content, str):
                _append_urls(ctx, state, _extract_http_urls_from_text(content))
    except Exception:
        pass

    # 1) Direct .content (SDK chunk)
    try:
        if hasattr(chunk, "content"):
            t = _stringify_content(getattr(chunk, "content"))
            if t:
                _append_urls(ctx, state, _extract_http_urls_from_text(t))
                return str(t)
    except Exception:
        pass

    # 2) .delta object or dict
    try:
        delta = getattr(chunk, "delta", None)
        if delta is not None:
            try:
                tc = delta.get("tool_calls") if isinstance(delta, dict) else getattr(delta, "tool_calls", None)
                if tc:
                    if isinstance(tc, list):
                        # already OpenAI-like dicts
                        _merge_tool_calls(state, tc)
                        state.force_func_call = True
            except Exception:
                pass

            dc = delta.get("content") if isinstance(delta, dict) else getattr(delta, "content", None)
            if dc is not None:
                t = _stringify_content(dc)
                if t:
                    _append_urls(ctx, state, _extract_http_urls_from_text(t))
                    return str(t)
            if isinstance(delta, str) and delta:
                _append_urls(ctx, state, _extract_http_urls_from_text(delta))
                return delta
    except Exception:
        pass

    # 3) OpenAI-like dict with choices[0].delta or choices[0].message
    try:
        if isinstance(chunk, dict):
            # tools/citations/usage meta
            try:
                chs = chunk.get("choices") or []
                if chs:
                    candidate = chs[0] or {}
                    tc = (candidate.get("delta") or {}).get("tool_calls") or candidate.get("tool_calls") or []
                    if tc:
                        _merge_tool_calls(state, tc)
                        state.force_func_call = True
            except Exception:
                pass

            # text delta/message content
            chs = chunk.get("choices") or []
            if chs:
                first = chs[0] or {}
                d = first.get("delta") or {}
                m = first.get("message") or {}
                if "content" in d and d["content"] is not None:
                    t = _stringify_content(d["content"])
                    if t:
                        _append_urls(ctx, state, _extract_http_urls_from_text(t))
                        return str(t)
                if "content" in m and m["content"] is not None:
                    mc = m["content"]
                    # inspect for image_url outputs and URLs
                    if isinstance(mc, list):
                        _process_message_content_for_outputs(core, ctx, state, mc)
                        out_parts: List[str] = []
                        for p in mc:
                            if isinstance(p, dict) and p.get("type") == "text":
                                t = p.get("text")
                                if isinstance(t, str):
                                    out_parts.append(t)
                        if out_parts:
                            txt = "".join(out_parts)
                            _append_urls(ctx, state, _extract_http_urls_from_text(txt))
                            return txt
                    else:
                        t = _stringify_content(mc)
                        if t:
                            _append_urls(ctx, state, _extract_http_urls_from_text(t))
                            return str(t)

            # root-level delta/message
            if isinstance(chunk.get("delta"), dict) and "content" in chunk["delta"]:
                t = _stringify_content(chunk["delta"]["content"])
                if t:
                    _append_urls(ctx, state, _extract_http_urls_from_text(t))
                    return str(t)
            if isinstance(chunk.get("message"), dict) and "content" in chunk["message"]:
                mc = chunk["message"]["content"]
                _process_message_content_for_outputs(core, ctx, state, mc if isinstance(mc, list) else [])
                if isinstance(mc, str):
                    _append_urls(ctx, state, _extract_http_urls_from_text(mc))
                    return mc

            # tail metadata: citations and usage
            _maybe_collect_tail_meta(state, chunk, ctx=ctx)
    except Exception:
        pass

    # 4) SimpleNamespace with choices[0].delta/message
    try:
        chs = getattr(chunk, "choices", None)
        if chs:
            first = chs[0]
            delta = getattr(first, "delta", None)
            message = getattr(first, "message", None)
            if delta is not None:
                try:
                    tc = getattr(delta, "tool_calls", None)
                    if tc:
                        _merge_tool_calls(state, tc if isinstance(tc, list) else [])
                        state.force_func_call = True
                except Exception:
                    pass
                c = getattr(delta, "content", None)
                if c is not None:
                    t = _stringify_content(c)
                    if t:
                        _append_urls(ctx, state, _extract_http_urls_from_text(t))
                        return str(t)
            if message is not None:
                c = getattr(message, "content", None)
                if c is not None:
                    if isinstance(c, list):
                        _process_message_content_for_outputs(core, ctx, state, c)
                        # optional: also extract text parts
                        out_parts: List[str] = []
                        for p in c:
                            if isinstance(p, dict) and p.get("type") == "text":
                                t = p.get("text")
                                if isinstance(t, str):
                                    out_parts.append(t)
                        if out_parts:
                            txt = "".join(out_parts)
                            _append_urls(ctx, state, _extract_http_urls_from_text(txt))
                            return txt
                    else:
                        t = _stringify_content(c)
                        if t:
                            _append_urls(ctx, state, _extract_http_urls_from_text(t))
                            return str(t)
    except Exception:
        pass

    # 5) Plain string
    if isinstance(chunk, str):
        _append_urls(ctx, state, _extract_http_urls_from_text(chunk))
        return chunk

    return None


def xai_extract_tool_calls(response) -> list[dict]:
    """
    Extract tool calls from xAI final response (proto or modern SDK/message shapes).

    :param response: xAI final response object or dict
    :return: List of tool calls in normalized dict format
    """
    out: list[dict] = []

    def _append_from_msg(msg_obj):
        try:
            if not msg_obj:
                return
            tcs = getattr(msg_obj, "tool_calls", None)
            if not tcs and isinstance(msg_obj, dict):
                tcs = msg_obj.get("tool_calls")
            if not tcs:
                return
            for tc in tcs:
                try:
                    fn = getattr(tc, "function", None)
                    if isinstance(tc, dict):
                        fn = tc.get("function", fn)
                    name = getattr(fn, "name", None) if fn is not None else None
                    args = getattr(fn, "arguments", None) if fn is not None else None
                    if isinstance(fn, dict):
                        name = fn.get("name", name)
                        args = fn.get("arguments", args)
                    if isinstance(args, (dict, list)):
                        try:
                            import json as _json
                            args = _json.dumps(args, ensure_ascii=False)
                        except Exception:
                            args = str(args)
                    out.append({
                        "id": (getattr(tc, "id", None) if not isinstance(tc, dict) else tc.get("id")) or "",
                        "type": "function",
                        "function": {"name": name or "", "arguments": args or "{}"},
                    })
                except Exception:
                    continue
        except Exception:
            pass

    try:
        if isinstance(response, dict):
            ch = (response.get("choices") or [])
            if ch:
                _append_from_msg(ch[0].get("message") or {})
            if "message" in response:
                _append_from_msg(response.get("message"))
            if "output_message" in response:
                _append_from_msg(response.get("output_message"))
            if out:
                return out
    except Exception:
        pass

    try:
        _append_from_msg(getattr(response, "message", None))
        _append_from_msg(getattr(response, "output_message", None))
        if out:
            return out
    except Exception:
        pass

    try:
        proto = getattr(response, "proto", None)
        if not proto:
            return out
        choices = getattr(proto, "choices", None) or []
        if not choices:
            return out
        msg = getattr(choices[0], "message", None)
        _append_from_msg(msg)
    except Exception:
        pass
    return out


def xai_extract_citations(response) -> list[str]:
    """
    Extract citations (URLs) from xAI final response if present.

    :param response: xAI final response object
    :return: List of citation URLs
    """
    def _norm_urls(raw) -> List[str]:
        urls: List[str] = []
        seen = set()
        if isinstance(raw, list):
            for it in raw:
                u = None
                if isinstance(it, str):
                    u = it
                elif isinstance(it, dict):
                    u = (it.get("url") or it.get("uri") or
                         (it.get("source") or {}).get("url") or (it.get("source") or {}).get("uri"))
                if isinstance(u, str) and (u.startswith("http://") or u.startswith("https://")):
                    if u not in seen:
                        urls.append(u); seen.add(u)
        return urls

    urls: list[str] = []
    try:
        cites = getattr(response, "citations", None)
        if cites is None and isinstance(response, dict):
            cites = response.get("citations")
        urls.extend([u for u in _norm_urls(cites or []) if u not in urls])
    except Exception:
        pass

    try:
        msg = getattr(response, "message", None)
        if msg is None and isinstance(response, dict):
            msg = response.get("message")
        if msg:
            mc = getattr(msg, "citations", None)
            if mc is None and isinstance(msg, dict):
                mc = msg.get("citations")
            urls.extend([u for u in _norm_urls(mc or []) if u not in urls])
    except Exception:
        pass

    try:
        out_msg = getattr(response, "output_message", None)
        if out_msg:
            mc = getattr(out_msg, "citations", None)
            if mc is None and isinstance(out_msg, dict):
                mc = out_msg.get("citations")
            urls.extend([u for u in _norm_urls(mc or []) if u not in urls])
    except Exception:
        pass

    try:
        proto = getattr(response, "proto", None)
        if proto:
            proto_cites = getattr(proto, "citations", None) or []
            urls.extend([u for u in _norm_urls(proto_cites) if u not in urls])
            choices = getattr(proto, "choices", None) or []
            if choices:
                m = getattr(choices[0], "message", None)
                if m:
                    urls.extend([u for u in _norm_urls(getattr(m, "citations", None) or []) if u not in urls])
    except Exception:
        pass
    return urls


def xai_extract_usage(response) -> dict:
    """
    Extract usage from xAI final response via proto or modern usage fields. Return {'in','out','reasoning','total'}.

    :param response: xAI final response object
    :return: Usage dict
    """
    def _as_int(v):
        try:
            return int(v)
        except Exception:
            try:
                return int(float(v))
            except Exception:
                return 0

    def _from_usage_dict(usage: Dict[str, Any]) -> dict:
        p = usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
        c = usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
        r = usage.get("reasoning_tokens", 0) or 0
        t = usage.get("total_tokens")
        p = _as_int(p); c = _as_int(c); r = _as_int(r)
        t = _as_int(t if t is not None else (p + c + r))
        out_total = max(0, t - p) if t else c
        return {"in": p, "out": out_total, "reasoning": r, "total": t}

    if isinstance(response, dict):
        u = response.get("usage")
        if isinstance(u, dict):
            return _from_usage_dict(u)

    try:
        u = getattr(response, "usage", None)
        if isinstance(u, dict):
            return _from_usage_dict(u)
    except Exception:
        pass

    try:
        proto = getattr(response, "proto", None)
        usage = getattr(proto, "usage", None) if proto else None
        if usage:
            p = _as_int(getattr(usage, "prompt_tokens", 0) or 0)
            c = _as_int(getattr(usage, "completion_tokens", 0) or 0)
            r = _as_int(getattr(usage, "reasoning_tokens", 0) or 0)
            t = _as_int(getattr(usage, "total_tokens", (p + c + r)) or (p + c + r))
            out_total = max(0, t - p) if t else c
            return {"in": p, "out": out_total, "reasoning": r, "total": t}
    except Exception:
        pass

    return {}