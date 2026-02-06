#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.02.06 03:00:00                  #
# ================================================== #

from __future__ import annotations

import base64
import json
import os
from typing import Optional, Dict, Any, List, Tuple

from pygpt_net.core.types import MODE_CHAT
from pygpt_net.core.bridge.context import BridgeContext, MultimodalContext
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem

from xai_sdk.chat import system as xsystem, user as xuser, assistant as xassistant, image as ximage


class Chat:
    def __init__(self, window=None):
        """
        Chat wrapper for xAI: SDK for plain chat, HTTP for tools/search/stream/vision.

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0
        self.allowed_mimes = {"image/jpeg", "image/png"}
        self.default_image_max_bytes = 10 * 1024 * 1024  # 10 MiB default

    # ---------- SEND ----------

    def send(self, context: BridgeContext, extra: Optional[Dict[str, Any]] = None):
        """
        Entry point for xAI chat/multimodal.

        Streaming:
        - Uses HTTP SSE for compatibility with tool calls and Live Search (citations/usage).

        Non-stream:
        - Uses SDK when safe (no tools, no Live Search, no tool-turns, no images).
        - Otherwise uses HTTP for OpenAI-compatible tool calling/search/vision.

        :param context: BridgeContext with all parameters
        :param extra: Extra parameters (not used)
        :return: dict with 'output_text', 'tool_calls', 'citations', 'usage' (non-stream)
                 or an iterable/generator yielding SDK-like response chunks (stream)
        """
        prompt = context.prompt
        system_prompt = context.system_prompt
        model_item = context.model
        functions = context.external_functions
        attachments = context.attachments
        multimodal_ctx = context.multimodal_ctx
        ctx = context.ctx or CtxItem()

        client = self.window.core.api.xai.get_client(context.mode, model_item)

        # Build SDK messages (used only on SDK/HTTP path without server-side tools)
        sdk_messages = self.build_messages(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model_item,
            history=context.history,
            attachments=attachments,
            multimodal_ctx=multimodal_ctx,
        )

        # Local tokens estimate
        self.reset_tokens()
        count_msgs = self._build_count_messages(prompt, system_prompt, model_item, context.history)
        self.input_tokens += self.window.core.tokens.from_messages(count_msgs, model_item.id)

        # Tools config
        tools_prepared = self.window.core.api.xai.tools.prepare(functions)

        # Detect tool-turns and image attachments
        has_tool_turns = self._has_tool_turns(context.history)
        has_images = self._attachments_have_images(attachments)

        # If images present and current model is not a vision model, select a safe fallback
        model_id = model_item.id
        if has_images and not self._is_vision_model(model_item):
            fb = self.window.core.config.get("xai_vision_fallback_model") or "grok-2-vision-latest"
            self.window.core.debug.info(f"[xai] Switching to vision model: {fb} (was: {model_id}) due to image input")
            model_id = fb

        # Server-side Agent Tools availability (web_search/x_search/code_execution/MCP/collections)
        # If any server-side tool is enabled, delegate to the Responses API which implements the Agent Tools flow.
        srv_cfg = self.window.core.api.xai.remote.build_for_chat(model_item, stream=context.stream)
        srv_tools_present = bool((srv_cfg.get("tools") or []))
        if srv_tools_present:
            return self.window.core.api.xai.responses.send(context=context, extra=extra)

        # STREAM: use HTTP SSE for consistent tool/citation/vision handling (legacy Chat Completions without Agent Tools)
        if context.stream:
            return self.call_http_stream(
                model=model_id,
                messages=sdk_messages,
                tools=tools_prepared or None,
                search_parameters=None,  # Live Search removed from Chat Completions; handled via Agent Tools in Responses API
                temperature=context.temperature,
                max_tokens=context.max_tokens,
                system_prompt=system_prompt,
                history=context.history,
                attachments=attachments,
                prompt=prompt,
            )

        # NON-STREAM: prefer SDK only for plain chat (no function tools/tool-turns/images)
        prefer_sdk_plain = (not tools_prepared) and (not has_tool_turns) and (not has_images)
        if prefer_sdk_plain:
            chat = client.chat.create(model=model_id, messages=sdk_messages)
            try:
                if hasattr(chat, "sample"):
                    return chat.sample()
                if hasattr(chat, "output_text"):
                    return chat
                if hasattr(chat, "message"):
                    return chat
            except Exception:
                pass
            return chat

        # Otherwise HTTP non-stream for legacy function-calling/vision/tool-turns (without Live Search)
        text, calls, citations, usage = self.call_http_nonstream(
            model=model_id,
            prompt=prompt,
            system_prompt=system_prompt,
            history=context.history,
            attachments=attachments,
            multimodal_ctx=multimodal_ctx,
            tools=tools_prepared or [],
            search_parameters=None,  # Live Search removed from Chat Completions; handled via Agent Tools in Responses API
            temperature=context.temperature,
            max_tokens=context.max_tokens,
        )
        return {
            "output_text": text or "",
            "tool_calls": calls or [],
            "citations": citations or [],
            "usage": usage or None,
        }

    # ---------- UNPACK (non-stream) ----------

    def unpack_response(self, mode: str, response, ctx: CtxItem):
        """
        Unpack non-streaming xAI response into ctx (text, tool calls, usage, citations, images).

        :param mode: mode (chat, etc)
        :param response: Response object from SDK or HTTP (dict)
        :param ctx: CtxItem to fill
        """
        # Text
        txt = getattr(response, "content", None)
        if not txt and isinstance(response, dict):
            txt = response.get("output_text") or ""
            if not txt:
                try:
                    ch = (response.get("choices") or [])
                    if ch:
                        msg = (ch[0].get("message") or {})
                        txt = self._message_to_text(msg)
                except Exception:
                    pass

        if not txt and not isinstance(response, dict):
            try:
                msg = getattr(response, "message", None) or getattr(response, "output_message", None)
                if msg is not None:
                    mc = getattr(msg, "content", None)
                    if mc is None and isinstance(msg, dict):
                        mc = msg.get("content")
                    txt = self._content_to_text(mc)
            except Exception:
                pass
            if not txt:
                try:
                    proto = getattr(response, "proto", None)
                    if proto:
                        choices = getattr(proto, "choices", None) or []
                        if choices:
                            m = getattr(choices[0], "message", None)
                            if m:
                                txt = self._content_to_text(getattr(m, "content", None))
                except Exception:
                    pass

        ctx.output = (str(txt or "")).strip()

        # Tool calls
        calls = []
        if isinstance(response, dict) and response.get("tool_calls"):
            calls = response["tool_calls"]

        if not calls:
            try:
                msg = getattr(response, "message", None) or getattr(response, "output_message", None)
            except Exception:
                msg = None
            try:
                if msg:
                    tcs = getattr(msg, "tool_calls", None)
                    if tcs is None and isinstance(msg, dict):
                        tcs = msg.get("tool_calls")
                    if tcs:
                        out = []
                        for tc in tcs:
                            fn = getattr(tc, "function", None)
                            if isinstance(tc, dict):
                                fn = tc.get("function", fn)
                            args = getattr(fn, "arguments", None) if fn is not None else None
                            if isinstance(fn, dict):
                                args = fn.get("arguments", args)
                            if isinstance(args, (dict, list)):
                                try:
                                    args = json.dumps(args, ensure_ascii=False)
                                except Exception:
                                    args = str(args)
                            out.append({
                                "id": (getattr(tc, "id", None) if not isinstance(tc, dict) else tc.get("id")) or "",
                                "type": "function",
                                "function": {
                                    "name": (getattr(fn, "name", None) if not isinstance(fn, dict) else fn.get("name")) or "",
                                    "arguments": args or "{}",
                                }
                            })
                        calls = out
            except Exception:
                pass

        if not calls:
            try:
                proto = getattr(response, "proto", None)
                tool_calls = getattr(getattr(getattr(proto, "choices", [None])[0], "message", None), "tool_calls", None)
                if tool_calls:
                    out = []
                    for tc in tool_calls:
                        out.append({
                            "id": getattr(tc, "id", "") or "",
                            "type": "function",
                            "function": {
                                "name": getattr(getattr(tc, "function", None), "name", "") or "",
                                "arguments": getattr(getattr(tc, "function", None), "arguments", "") or "{}",
                            }
                        })
                    calls = out
            except Exception:
                pass

        if calls:
            ctx.tool_calls = calls

        # Citations and URLs
        try:
            urls: List[str] = []
            if isinstance(response, dict):
                urls = self._extract_urls(response.get("citations"))
                if not urls:
                    choices = response.get("choices") or []
                    if choices:
                        msg = choices[0].get("message") or {}
                        urls = self._extract_urls(msg.get("citations"))
                # Additionally scan assistant message content for http(s) links in text parts
                try:
                    choices = response.get("choices") or []
                    if choices:
                        msg = choices[0].get("message") or {}
                        parts = msg.get("content")
                        if isinstance(parts, list):
                            for p in parts:
                                if isinstance(p, dict) and p.get("type") == "text":
                                    t = p.get("text")
                                    if isinstance(t, str):
                                        for u in self._extract_urls([t]):
                                            if u not in urls:
                                                urls.append(u)
                except Exception:
                    pass
            else:
                cits = getattr(response, "citations", None)
                urls = self._extract_urls(cits)
                if not urls:
                    msg = getattr(response, "message", None) or getattr(response, "output_message", None)
                    if msg:
                        mc = getattr(msg, "citations", None)
                        if mc is None and isinstance(msg, dict):
                            mc = msg.get("citations")
                        urls = self._extract_urls(mc)
            if urls:
                if ctx.urls is None:
                    ctx.urls = []
                for u in urls:
                    if u not in ctx.urls:
                        ctx.urls.append(u)
        except Exception:
            pass

        # Images possibly returned in assistant content as image_url parts
        try:
            parts = None
            if isinstance(response, dict):
                choices = response.get("choices") or []
                if choices:
                    msg = choices[0].get("message") or {}
                    parts = msg.get("content")
            else:
                msg = getattr(response, "message", None) or getattr(response, "output_message", None)
                if msg:
                    parts = getattr(msg, "content", None)
            if isinstance(parts, list):
                self._collect_images_from_message_parts(parts, ctx)
        except Exception:
            pass

        try:
            # Attempt to auto-download file parts or references (file id)
            self._maybe_download_files_from_response(response, ctx)
        except Exception:
            pass

        # Usage
        try:
            if isinstance(response, dict) and response.get("usage"):
                u = self._normalize_usage(response["usage"])
                if u:
                    ctx.set_tokens(u.get("in", 0), u.get("out", 0))
                    if not isinstance(ctx.extra, dict):
                        ctx.extra = {}
                    ctx.extra["usage"] = {
                        "vendor": "xai",
                        "input_tokens": u.get("in", 0),
                        "output_tokens": u.get("out", 0),
                        "reasoning_tokens": u.get("reasoning", 0),
                        "total_reported": u.get("total"),
                    }
                    return

            uattr = getattr(response, "usage", None)
            if isinstance(uattr, dict):
                u = self._normalize_usage(uattr)
                if u:
                    ctx.set_tokens(u.get("in", 0), u.get("out", 0))
                    if not isinstance(ctx.extra, dict):
                        ctx.extra = {}
                    ctx.extra["usage"] = {
                        "vendor": "xai",
                        "input_tokens": u.get("in", 0),
                        "output_tokens": u.get("out", 0),
                        "reasoning_tokens": u.get("reasoning", 0),
                        "total_reported": u.get("total"),
                    }
                    return

            proto = getattr(response, "proto", None)
            usage = getattr(proto, "usage", None)
            if usage:
                p = int(getattr(usage, "prompt_tokens", 0) or 0)
                c = int(getattr(usage, "completion_tokens", 0) or 0)
                r = int(getattr(usage, "reasoning_tokens", 0) or 0)
                t = int(getattr(usage, "total_tokens", (p + c + r)) or (p + c + r))
                out_tok = max(0, t - p) if t else c
                ctx.set_tokens(p, out_tok)
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra["usage"] = {
                    "vendor": "xai",
                    "input_tokens": p,
                    "output_tokens": out_tok,
                    "reasoning_tokens": r,
                    "total_reported": t,
                }
        except Exception:
            pass

    # ---------- BUILDERS (SDK + HTTP) ----------

    def build_messages(
        self,
        prompt: str,
        system_prompt: str,
        model: ModelItem,
        history: Optional[List[CtxItem]] = None,
        attachments: Optional[Dict[str, AttachmentItem]] = None,
        multimodal_ctx: Optional[MultimodalContext] = None,
    ) -> list:
        """
        Build xAI SDK messages list for chat.create(...).

        :param prompt: Current user prompt
        :param system_prompt: System prompt
        :param model: ModelItem
        :param history: List of CtxItem for context
        :param attachments: Dict of AttachmentItem for images
        :param multimodal_ctx: MultimodalContext (not used)
        :return: List of SDK message objects
        """
        self.window.core.api.xai.vision.reset()
        out = []
        if system_prompt:
            out.append(xsystem(system_prompt))

        if self.window.core.config.get('use_context'):
            used = self.window.core.tokens.from_user(prompt, system_prompt)
            items = self.window.core.ctx.get_history(
                history, model.id, MODE_CHAT, used, self._fit_ctx(model),
            )
            for item in items:
                if item.final_input:
                    out.append(xuser(str(item.final_input)))
                if item.final_output:
                    out.append(xassistant(str(item.final_output)))

        parts = [str(prompt or "")]
        for img in self.window.core.api.xai.vision.build_images_for_chat(attachments):
            parts.append(ximage(img))
        out.append(xuser(*parts))
        return out

    # ---------- HTTP (tools/search/vision) ----------

    def call_http_nonstream(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str],
        history: Optional[List[CtxItem]],
        attachments: Optional[Dict[str, AttachmentItem]],
        multimodal_ctx: Optional[MultimodalContext],
        tools: List[dict],
        search_parameters: Optional[Dict[str, Any]],
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> Tuple[str, List[dict], List[str], Optional[dict]]:
        """
        Non-streaming HTTP Chat Completions call to xAI with optional tools, Live Search, and vision.
        Returns (text, tool_calls, citations, usage).
        """
        import requests

        cfg = self.window.core.config
        api_key = cfg.get("api_key_xai") or ""
        base_url = self._build_base_url(cfg.get("api_endpoint_xai"))

        messages = self._build_http_messages(
            model_id=model,
            system_prompt=system_prompt,
            history=history,
            prompt=prompt,
            attachments=attachments,
        )

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.window.core.config.get('temperature'),
        }
        if max_tokens:
            payload["max_tokens"] = int(max_tokens)

        tools_payload = self._make_tools_payload(tools)
        if tools_payload:
            payload["tools"] = tools_payload
            payload["tool_choice"] = "auto"

        # Live Search via 'search_parameters' is deprecated on Chat Completions.
        # It is intentionally not attached here; Agent Tools are handled by the Responses API path.

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        data = {}
        try:
            resp = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=180)
            if not resp.encoding:
                resp.encoding = "utf-8"
            if resp.status_code >= 400:
                self.window.core.debug.error(f"[xai.http] {resp.status_code} {resp.reason}: {resp.text}")
            resp.raise_for_status()
            data = resp.json() if resp.content else {}
        except Exception as e:
            self.window.core.debug.error(f"[xai.http] error: {e}")
            return "", [], [], None

        text = ""
        calls: List[dict] = []
        try:
            choices = data.get("choices") or []
            if choices:
                msg = (choices[0].get("message") or {})
                mc = msg.get("content")
                if isinstance(mc, str):
                    text = mc.strip()
                elif isinstance(mc, list):
                    out_parts: List[str] = []
                    for p in mc:
                        if isinstance(p, dict) and p.get("type") == "text":
                            t = p.get("text")
                            if isinstance(t, str):
                                out_parts.append(t)
                    text = "".join(out_parts).strip()

                tlist = msg.get("tool_calls") or []
                for t in tlist:
                    fn = t.get("function") or {}
                    args = fn.get("arguments")
                    if isinstance(args, (dict, list)):
                        try:
                            args = json.dumps(args, ensure_ascii=False)
                        except Exception:
                            args = str(args)
                    calls.append({
                        "id": t.get("id") or "",
                        "type": "function",
                        "function": {"name": fn.get("name") or "", "arguments": args or "{}"},
                    })
        except Exception:
            pass

        citations: List[str] = []
        try:
            citations = self._extract_urls(data.get("citations")) or []
            if not citations:
                choices = data.get("choices") or []
                if choices:
                    msg = choices[0].get("message") or {}
                    citations = self._extract_urls(msg.get("citations"))
        except Exception:
            citations = citations or []

        usage: Optional[dict] = None
        try:
            usage = self._normalize_usage(data.get("usage"))
        except Exception:
            usage = usage or None

        return text, calls, citations, usage

    def call_http_stream(
        self,
        model: str,
        messages: Optional[list] = None,
        tools: Optional[List[dict]] = None,
        search_parameters: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
        history: Optional[List[CtxItem]] = None,
        attachments: Optional[Dict[str, AttachmentItem]] = None,
        prompt: Optional[str] = None,
    ):
        """
        Streaming HTTP Chat Completions (SSE) for xAI.
        Sends OpenAI-compatible JSON; rebuilds messages when given SDK objects.

        :return: Iterable/generator yielding SDK-like response chunks with 'content', 'tool_calls', 'citations', 'usage'
        """
        import requests
        from types import SimpleNamespace
        import json as _json

        cfg = self.window.core.config
        api_key = cfg.get("api_key_xai") or ""
        base_url = self._build_base_url(cfg.get("api_endpoint_xai"))

        if not self._looks_like_http_messages(messages):
            messages = self._build_http_messages(
                model_id=model,
                system_prompt=system_prompt,
                history=history,
                prompt=prompt,
                attachments=attachments,
            )

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.window.core.config.get('temperature'),
            "stream": True,
        }
        if max_tokens:
            payload["max_tokens"] = int(max_tokens)

        tools_payload = self._make_tools_payload(tools or [])
        if tools_payload:
            payload["tools"] = tools_payload
            payload["tool_choice"] = "auto"

        # Live Search via 'search_parameters' is deprecated on Chat Completions and omitted here.

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        def _mk_chunk(delta_text=None, tool_calls=None, citations=None, usage=None):
            delta_dict: Dict[str, Any] = {}
            if delta_text is not None:
                delta_dict["content"] = delta_text
            if tool_calls is not None:
                delta_dict["tool_calls"] = tool_calls
            choice = SimpleNamespace(delta=SimpleNamespace(**delta_dict))
            obj = SimpleNamespace(choices=[choice])
            if citations is not None:
                setattr(obj, "citations", citations)
            if usage is not None:
                setattr(obj, "usage", usage)
            return obj

        class XAIHTTPStream:
            __slots__ = ("_resp", "_iter_started")

            def __init__(self, resp):
                self._resp = resp
                self._iter_started = False
                if not self._resp.encoding:
                    self._resp.encoding = "utf-8"

            def __iter__(self):
                if self._iter_started:
                    return
                self._iter_started = True
                try:
                    for raw in self._resp.iter_lines(decode_unicode=False):
                        if not raw:
                            continue
                        try:
                            s = raw.decode("utf-8", errors="replace").lstrip("\ufeff").strip()
                        except Exception:
                            continue
                        if not s.startswith("data:"):
                            continue
                        data_str = s[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            obj = _json.loads(data_str)
                        except Exception:
                            continue

                        # OpenAI-style choices path
                        try:
                            chs = obj.get("choices") or []
                            if chs:
                                delta = chs[0].get("delta") or {}
                                message = chs[0].get("message") or {}
                                if "content" in delta and delta["content"] is not None:
                                    yield _mk_chunk(delta_text=str(delta["content"]))
                                elif "content" in message and message["content"] is not None:
                                    mc = message["content"]
                                    if isinstance(mc, str):
                                        yield _mk_chunk(delta_text=mc)
                                    elif isinstance(mc, list):
                                        out_parts: List[str] = []
                                        for p in mc:
                                            if isinstance(p, dict) and p.get("type") == "text":
                                                t = p.get("text")
                                                if isinstance(t, str):
                                                    out_parts.append(t)
                                        if out_parts:
                                            yield _mk_chunk(delta_text="".join(out_parts))
                                tc = delta.get("tool_calls") or message.get("tool_calls") or []
                                if tc:
                                    yield _mk_chunk(tool_calls=tc)
                                u = obj.get("usage")
                                cits = self_outer._extract_urls(obj.get("citations"))
                                if u or cits:
                                    yield _mk_chunk(delta_text="", citations=cits if cits else None, usage=u if u else None)
                                continue
                        except Exception:
                            pass

                        # Event-style root-level delta/message
                        try:
                            if isinstance(obj.get("delta"), dict):
                                d = obj["delta"]
                                if "content" in d and d["content"] is not None:
                                    yield _mk_chunk(delta_text=str(d["content"]))
                                tc = d.get("tool_calls") or []
                                if tc:
                                    yield _mk_chunk(tool_calls=tc)
                            if isinstance(obj.get("message"), dict) and "content" in obj["message"]:
                                mc = obj["message"]["content"]
                                if isinstance(mc, str):
                                    yield _mk_chunk(delta_text=mc)
                                elif isinstance(mc, list):
                                    out_parts: List[str] = []
                                    for p in mc:
                                        if isinstance(p, dict) and p.get("type") == "text":
                                            t = p.get("text")
                                            if isinstance(t, str):
                                                out_parts.append(t)
                                    if out_parts:
                                        yield _mk_chunk(delta_text="".join(out_parts))
                            u = obj.get("usage")
                            cits = self_outer._extract_urls(obj.get("citations"))
                            if u or cits:
                                yield _mk_chunk(delta_text="", citations=cits if cits else None, usage=u if u else None)
                        except Exception:
                            pass
                finally:
                    try:
                        self._resp.close()
                    except Exception:
                        pass

            def close(self):
                try:
                    self._resp.close()
                except Exception:
                    pass

            def resolve(self):
                return

        self_outer = self

        try:
            resp = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, stream=True, timeout=300)
            if not resp.encoding:
                resp.encoding = "utf-8"
            if resp.status_code >= 400:
                try:
                    body = resp.text
                except Exception:
                    body = ""
                self.window.core.debug.error(f"[xai.http.stream] {resp.status_code} {resp.reason}: {body}")
            resp.raise_for_status()
            return XAIHTTPStream(resp)
        except Exception as e:
            self.window.core.debug.error(f"[xai.http.stream] error: {e}")

            class _Empty:
                def __iter__(self):
                    return iter(())
                def close(self):
                    pass
                def resolve(self):
                    pass
            return _Empty()

    # ---------- UTILS ----------

    def _fit_ctx(self, model: ModelItem) -> int:
        """
        Fit to max model tokens (uses model.ctx if present).
        """
        max_ctx_tokens = self.window.core.config.get('max_total_tokens')
        if model and model.ctx and 0 < model.ctx < max_ctx_tokens:
            max_ctx_tokens = model.ctx
        return max_ctx_tokens

    def _build_count_messages(
        self,
        prompt: str,
        system_prompt: str,
        model: ModelItem,
        history: Optional[List[CtxItem]] = None,
    ) -> List[dict]:
        """
        Build simple messages structure for local token estimation.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if self.window.core.config.get('use_context'):
            used_tokens = self.window.core.tokens.from_user(prompt, system_prompt)
            items = self.window.core.ctx.get_history(
                history, model.id, MODE_CHAT, used_tokens, self._fit_ctx(model),
            )
            for item in items:
                if item.final_input:
                    messages.append({"role": "user", "content": str(item.final_input)})
                if item.final_output:
                    messages.append({"role": "assistant", "content": str(item.final_output)})

        messages.append({"role": "user", "content": str(prompt)})
        return messages

    def _content_to_text(self, content) -> str:
        """
        Convert message content (SDK or HTTP shapes) into plain text.
        """
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            out: List[str] = []
            for p in content:
                if isinstance(p, dict) and p.get("type") == "text":
                    t = p.get("text")
                    if isinstance(t, str):
                        out.append(t)
                elif isinstance(p, str):
                    out.append(p)
                else:
                    t = getattr(p, "text", None)
                    if isinstance(t, str):
                        out.append(t)
            return "".join(out)
        if isinstance(content, dict):
            if isinstance(content.get("text"), str):
                return content["text"]
            if isinstance(content.get("content"), str):
                return content["content"]
        t = getattr(content, "text", None)
        if isinstance(t, str):
            return t
        return str(content)

    def _message_to_text(self, msg: Dict[str, Any]) -> str:
        """
        Extract text from a dict message with 'content' possibly being str or list of parts.
        """
        if not isinstance(msg, dict):
            return ""
        mc = msg.get("content")
        return self._content_to_text(mc)

    def _extract_urls(self, raw) -> List[str]:
        """
        Normalize list of citations into a list of HTTP(S) URLs.
        """
        urls: List[str] = []
        seen = set()
        if not raw:
            return urls
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

    def _normalize_usage(self, raw) -> Optional[dict]:
        """
        Normalize usage to a common dict: {'in','out','reasoning','total'}.
        Accepts either:
          - {'input_tokens','output_tokens','total_tokens'}
          - {'prompt_tokens','completion_tokens','total_tokens'}
        """
        if not isinstance(raw, dict):
            return None

        def _as_int(v) -> int:
            try:
                return int(v)
            except Exception:
                try:
                    return int(float(v))
                except Exception:
                    return 0

        in_tok = raw.get("input_tokens") if "input_tokens" in raw else raw.get("prompt_tokens")
        out_tok = raw.get("output_tokens") if "output_tokens" in raw else raw.get("completion_tokens")
        reasoning_tok = raw.get("reasoning_tokens", 0)
        tot = raw.get("total_tokens")

        i = _as_int(in_tok or 0)
        o = _as_int(out_tok or 0)
        r = _as_int(reasoning_tok or 0)
        t = _as_int(tot if tot is not None else (i + o + r))
        return {"in": i, "out": max(0, t - i) if t else o, "reasoning": r, "total": t}

    def _looks_like_http_messages(self, messages) -> bool:
        """
        Return True if 'messages' looks like an OpenAI-style array of dicts with 'role' and 'content'.
        """
        if not isinstance(messages, list):
            return False
        for m in messages:
            if not isinstance(m, dict):
                return False
            if "role" not in m or "content" not in m:
                return False
        return True

    def _build_http_messages(
        self,
        model_id: str,
        system_prompt: Optional[str],
        history: Optional[List[CtxItem]],
        prompt: Optional[str],
        attachments: Optional[Dict[str, AttachmentItem]],
    ) -> list:
        """
        Build OpenAI-compatible messages array (vision-safe):
        - If images present: content is a list of parts, with image parts first, then text part.
        - Only JPEG/PNG allowed; size validated; on violation we raise clear error in logs.
        - Tool-turns from ctx are injected like OpenAI (assistant.tool_calls + tool).
        """
        self.window.core.api.xai.vision.reset()
        messages: List[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        items: List[CtxItem] = []
        if self.window.core.config.get('use_context'):
            used = self.window.core.tokens.from_user(prompt or "", system_prompt or "")
            mdl = self.window.core.models.get(model_id) if self.window.core.models.has(model_id) else self.window.core.models.from_defaults()
            items = self.window.core.ctx.get_history(history, model_id, MODE_CHAT, used, self._fit_ctx(mdl))
            for it in items:
                if it.final_input:
                    messages.append({"role": "user", "content": str(it.final_input)})
                if it.final_output:
                    messages.append({"role": "assistant", "content": str(it.final_output)})

        self._append_tool_turns_from_ctx(messages, items)

        parts: List[dict] = []
        img_found = False
        if attachments:
            cfg = self.window.core.config
            max_bytes = int(cfg.get("xai_image_max_bytes") or self.default_image_max_bytes)

            for _, att in attachments.items():
                try:
                    if not (att and att.path):
                        continue
                    if not self.window.core.api.xai.vision.is_image(att.path):
                        continue
                    mime = self.window.core.api.xai.vision.guess_mime(att.path)
                    if mime not in self.allowed_mimes:
                        self.window.core.debug.error(f"[xai.vision] Unsupported image MIME: {mime}. Use JPEG/PNG.")
                        continue
                    try:
                        fsz = os.path.getsize(att.path)
                        if fsz > max_bytes:
                            self.window.core.debug.error(f"[xai.vision] Image too large ({fsz} bytes). Max: {max_bytes}.")
                            continue
                    except Exception:
                        pass
                    with open(att.path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                    parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"},
                    })
                    att.consumed = True
                    img_found = True
                    self.window.core.api.xai.vision.attachments[att.id] = att.path
                except Exception as e:
                    self.window.core.debug.error(f"[xai.vision] Error processing image '{getattr(att,'path',None)}': {e}")
                    continue

        if img_found:
            if prompt:
                parts.append({"type": "text", "text": str(prompt)})
            messages.append({"role": "user", "content": parts})
        else:
            messages.append({"role": "user", "content": str(prompt or "")})

        return messages

    def _append_tool_turns_from_ctx(self, messages: List[dict], items: List[CtxItem]):
        """
        Append assistant.tool_calls and subsequent tool messages from last ctx item (OpenAI-compatible).
        """
        tool_call_native_enabled = self.window.core.config.get('func_call.native', False)
        if not (items and tool_call_native_enabled):
            return
        last = items[-1]
        if not (last.extra and isinstance(last.extra, dict)):
            return
        tool_calls = last.extra.get("tool_calls")
        tool_output = last.extra.get("tool_output")
        if not (tool_calls and isinstance(tool_calls, list)):
            return

        idx = None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "assistant":
                idx = i
                break
        if idx is None:
            return

        messages[idx]["tool_calls"] = []
        messages[idx]["content"] = ""
        for call in tool_calls:
            fn = call.get("function", {})
            messages[idx]["tool_calls"].append({
                "id": call.get("id", ""),
                "type": "function",
                "function": {
                    "name": fn.get("name", ""),
                    "arguments": json.dumps(fn.get("arguments", {})),
                }
            })

        if tool_output and isinstance(tool_output, list):
            for out in tool_output:
                if isinstance(out, dict) and "result" in out:
                    content = str(out["result"])
                    tool_call_id = None
                    if "cmd" in out:
                        for c in tool_calls:
                            if c.get("function", {}).get("name") == out.get("cmd"):
                                tool_call_id = c.get("id")
                                break
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id or tool_calls[0].get("id", ""),
                        "content": content,
                    })
                else:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_calls[0].get("id", ""),
                        "content": str(out),
                    })

    def _has_tool_turns(self, history: Optional[List[CtxItem]]) -> bool:
        """
        Return True if the last history item contains tool call(s) with tool output.
        """
        if not history:
            return False
        last = history[-1]
        if not (last.extra and isinstance(last.extra, dict)):
            return False
        calls = last.extra.get("tool_calls")
        outs = last.extra.get("tool_output")
        return bool(calls and isinstance(calls, list) and outs and isinstance(outs, list))

    def _attachments_have_images(self, attachments: Optional[Dict[str, AttachmentItem]]) -> bool:
        """
        Detect if attachments contain at least one image file.
        """
        if not attachments:
            return False
        for _, att in attachments.items():
            try:
                if att.path and self.window.core.api.xai.vision.is_image(att.path):
                    return True
            except Exception:
                continue
        return False

    def _is_vision_model(self, model: ModelItem) -> bool:
        """
        Heuristic check for vision-capable model IDs.
        """
        model_id = (model.id if model and model.id else "").strip()
        if not model or not model_id:
            return False
        if model.is_image_input():
            return True
        mid = model_id.lower()
        return ("vision" in mid) or ("-v" in mid and "grok" in mid)

    def _make_tools_payload(self, tools: Optional[List[dict]]) -> List[dict]:
        """
        Normalize tools to [{"type":"function","function":{...}}] without double-wrapping.
        """
        out: List[dict] = []
        for t in tools or []:
            if isinstance(t, dict) and t.get("type") == "function" and "function" in t:
                out.append(t)
            else:
                out.append({"type": "function", "function": t})
        return out

    def _build_base_url(self, cfg_endpoint: Optional[str]) -> str:
        """
        Return normalized base URL like 'https://api.x.ai/v1' without trailing slash.
        """
        base = (cfg_endpoint or "https://api.x.ai/v1").strip()
        if base.endswith("/"):
            base = base[:-1]
        return base

    def _collect_images_from_message_parts(self, parts: List[dict], ctx: CtxItem):
        """
        Inspect assistant message parts for image_url outputs and URLs.
        For http(s) URLs -> add to ctx.urls; for data URLs -> save to file and add to ctx.images.
        """
        try:
            if not isinstance(parts, list):
                return
            for p in parts:
                if not isinstance(p, dict):
                    continue
                if p.get("type") == "file":
                    file_id = p.get("id") or p.get("file_id")
                    if isinstance(file_id, str):
                        try:
                            save = self.window.core.api.xai.store.download_to_dir(file_id)
                            if save:
                                if not isinstance(ctx.files, list):
                                    ctx.files = []
                                if save not in ctx.files:
                                    ctx.files.append(save)
                                ext = os.path.splitext(save)[1].lower().lstrip(".")
                                if ext in ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"]:
                                    if not isinstance(ctx.images, list):
                                        ctx.images = []
                                    if save not in ctx.images:
                                        ctx.images.append(save)
                        except Exception:
                            pass
                    continue
                if p.get("type") != "image_url":
                    continue
                img = p.get("image_url") or {}
                url = img.get("url")
                if not isinstance(url, str):
                    continue
                if url.startswith("http://") or url.startswith("https://"):
                    if ctx.urls is None:
                        ctx.urls = []
                    if url not in ctx.urls:
                        ctx.urls.append(url)
                elif url.startswith("data:image/"):
                    try:
                        header, b64 = url.split(",", 1)
                        mime = header.split(";")[0].split(":")[1].lower()
                        ext = "png"
                        if "jpeg" in mime or "jpg" in mime:
                            ext = "jpg"
                        save_path = self.window.core.image.gen_unique_path(ctx, ext=ext)
                        with open(save_path, "wb") as f:
                            f.write(base64.b64decode(b64))
                        if not isinstance(ctx.images, list):
                            ctx.images = []
                        ctx.images.append(save_path)
                    except Exception:
                        pass
        except Exception:
            pass

    def reset_tokens(self):
        """Reset input tokens counter."""
        self.input_tokens = 0

    def get_used_tokens(self) -> int:
        """
        Return the locally estimated input tokens count.
        """
        return self.input_tokens

    def _maybe_download_files_from_response(self, response, ctx: CtxItem) -> None:
        """
        Attempt to download any files referenced by id in response payloads (dict/SDK/proto).
        """
        def _walk(o, acc: set):
            if o is None:
                return
            if isinstance(o, dict):
                fid = o.get("file_id") or o.get("id") if o.get("type") == "file" else None
                if isinstance(fid, str) and fid.startswith("file-"):
                    acc.add(fid)
                for v in o.values():
                    _walk(v, acc)
            elif isinstance(o, (list, tuple)):
                for it in o:
                    _walk(it, acc)

        ids = set()
        try:
            if isinstance(response, dict):
                _walk(response, ids)
            else:
                msg = getattr(response, "message", None) or getattr(response, "output_message", None)
                if msg:
                    _walk(getattr(msg, "content", None), ids)
                proto = getattr(response, "proto", None)
                if proto:
                    ch = getattr(proto, "choices", None) or []
                    if ch:
                        m = getattr(ch[0], "message", None)
                        if m:
                            _walk(getattr(m, "content", None), ids)
        except Exception:
            pass

        if not ids:
            return
        saved = []
        for fid in ids:
            try:
                p = self.window.core.api.xai.store.download_to_dir(fid)
                if p:
                    saved.append(p)
            except Exception:
                continue
        if saved:
            saved = self.window.core.filesystem.make_local_list(saved)
            if not isinstance(ctx.files, list):
                ctx.files = []
            for p in saved:
                if p not in ctx.files:
                    ctx.files.append(p)
            imgs = []
            for p in saved:
                ext = os.path.splitext(p)[1].lower().lstrip(".")
                if ext in ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"]:
                    imgs.append(p)
            if imgs:
                if not isinstance(ctx.images, list):
                    ctx.images = []
                for p in imgs:
                    if p not in ctx.images:
                        ctx.images.append(p)