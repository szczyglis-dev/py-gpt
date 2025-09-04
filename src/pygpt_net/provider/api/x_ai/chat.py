#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 01:00:00                  #
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
        # Image constraints (can be overridden by config keys below)
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

        # Build SDK messages (used only on SDK path)
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

        # Tools and Live Search config
        tools_prepared = self.window.core.api.xai.tools.prepare(functions)
        rt_cfg = self.window.core.api.xai.remote.build_remote_tools(model_item)
        http_params = (rt_cfg.get("http") if isinstance(rt_cfg, dict) else None)
        sdk_live = bool(rt_cfg.get("sdk", {}).get("enabled")) if isinstance(rt_cfg, dict) else False

        # Detect tool-turns and image attachments
        has_tool_turns = self._has_tool_turns(context.history)
        has_images = self._attachments_have_images(attachments)

        # If images present and current model is not a vision model, select a safe fallback
        model_id = model_item.id
        if has_images and not self._is_vision_model(model_item):
            fb = self.window.core.config.get("xai_vision_fallback_model") or "grok-2-vision-latest"
            self.window.core.debug.info(f"[xai] Switching to vision model: {fb} (was: {model_id}) due to image input")
            model_id = fb

        # STREAM: use HTTP SSE for consistent tool/citation/vision handling
        if context.stream:
            return self.call_http_stream(
                model=model_id,
                messages=sdk_messages,  # may be SDK objects; HTTP builder will rebuild if needed
                tools=tools_prepared or None,
                search_parameters=http_params,
                temperature=context.temperature,
                max_tokens=context.max_tokens,
                system_prompt=system_prompt,
                history=context.history,
                attachments=attachments,
                prompt=prompt,
            )

        # NON-STREAM: prefer SDK only for plain chat (no tools/search/tool-turns/images)
        if sdk_live and not tools_prepared and http_params is None and not has_tool_turns and not has_images:
            chat = client.chat.create(model=model_id, messages=sdk_messages)
            return chat.sample()

        # Otherwise HTTP non-stream for tools/search/vision/tool-turns
        text, calls, citations, usage = self.call_http_nonstream(
            model=model_id,
            prompt=prompt,
            system_prompt=system_prompt,
            history=context.history,
            attachments=attachments,
            multimodal_ctx=multimodal_ctx,
            tools=tools_prepared or [],
            search_parameters=http_params,
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
        Unpack non-streaming xAI response into ctx (text, tool calls, usage, citations).

        :param mode: mode (chat, etc)
        :param response: Response object from SDK or HTTP (dict)
        :param ctx: CtxItem to fill
        """
        # Text
        txt = getattr(response, "content", None)
        if not txt and isinstance(response, dict):
            txt = response.get("output_text") or ""
        ctx.output = (str(txt or "")).strip()

        # Tool calls
        calls = []
        if isinstance(response, dict) and response.get("tool_calls"):
            calls = response["tool_calls"]

        if not calls:
            # SDK proto fallback (defensive)
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

        # Citations
        try:
            urls: List[str] = []
            if isinstance(response, dict):
                urls = self._extract_urls(response.get("citations"))
            else:
                cits = getattr(response, "citations", None)
                urls = self._extract_urls(cits)
            if urls:
                if ctx.urls is None:
                    ctx.urls = []
                for u in urls:
                    if u not in ctx.urls:
                        ctx.urls.append(u)
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

            proto = getattr(response, "proto", None)
            usage = getattr(proto, "usage", None)
            if usage:
                p = int(getattr(usage, "prompt_tokens", 0) or 0)
                c = int(getattr(usage, "completion_tokens", 0) or 0)
                t = int(getattr(usage, "total_tokens", (p + c)) or (p + c))
                out_tok = max(0, t - p) if t else c
                ctx.set_tokens(p, out_tok)
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra["usage"] = {
                    "vendor": "xai",
                    "input_tokens": p,
                    "output_tokens": out_tok,
                    "reasoning_tokens": 0,
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

        # Current user message with optional images (SDK accepts text first or images first)
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

        :param model: Model ID
        :param prompt: Current user prompt
        :param system_prompt: System prompt
        :param history: List of CtxItem for context
        :param attachments: Dict of AttachmentItem for images
        :param multimodal_ctx: MultimodalContext (not used)
        :param tools: List of tool dicts
        :param search_parameters: Live Search parameters dict
        :param temperature: Temperature float
        :param max_tokens: Max tokens int
        :return: (output text, tool calls list, citations list, usage dict)
        """
        import requests

        cfg = self.window.core.config
        api_key = cfg.get("api_key_xai") or ""
        base_url = self._build_base_url(cfg.get("api_endpoint_xai"))

        # unified HTTP messages (with tool-turns + images)
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

        if search_parameters:
            sp = dict(search_parameters)
            if "return_citations" not in sp:
                sp["return_citations"] = True
            payload["search_parameters"] = sp

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
                # Log server error body for diagnostics
                self.window.core.debug.error(f"[xai.http] {resp.status_code} {resp.reason}: {resp.text}")
            resp.raise_for_status()
            data = resp.json() if resp.content else {}
        except Exception as e:
            self.window.core.debug.error(f"[xai.http] error: {e}")
            return "", [], [], None

        # Text + tool calls
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

                # tool calls
                tlist = msg.get("tool_calls") or []
                for t in tlist:
                    fn = t.get("function") or {}
                    calls.append({
                        "id": t.get("id") or "",
                        "type": "function",
                        "function": {"name": fn.get("name") or "", "arguments": fn.get("arguments") or "{}"},
                    })
        except Exception:
            pass

        # Citations
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

        # Usage
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
        # fallback rebuild inputs if needed:
        system_prompt: Optional[str] = None,
        history: Optional[List[CtxItem]] = None,
        attachments: Optional[Dict[str, AttachmentItem]] = None,
        prompt: Optional[str] = None,
    ):
        """
        Streaming HTTP Chat Completions (SSE) for xAI.
        Sends OpenAI-compatible JSON; rebuilds messages when given SDK objects.

        :param model: Model ID
        :param messages: List of messages (SDK objects or HTTP-style dicts)
        :param tools: List of tool dicts
        :param search_parameters: Live Search parameters dict
        :param temperature: Temperature float
        :param max_tokens: Max tokens int
        :param system_prompt: System prompt (used if messages need rebuilding)
        :param history: List of CtxItem for context (used if messages need rebuilding)
        :param attachments: Dict of AttachmentItem for images (used if messages need rebuilding)
        :param prompt: Current user prompt (used if messages need rebuilding)
        :return: Iterable/generator yielding SDK-like response chunks with 'content', 'tool_calls', 'citations', 'usage'
        """
        import requests
        from types import SimpleNamespace
        import json as _json

        cfg = self.window.core.config
        api_key = cfg.get("api_key_xai") or ""
        base_url = self._build_base_url(cfg.get("api_endpoint_xai"))

        # Ensure HTTP messages are JSON-serializable dicts
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

        if search_parameters:
            sp = dict(search_parameters)
            if "return_citations" not in sp:
                sp["return_citations"] = True
            payload["search_parameters"] = sp

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

                        # delta or message styles
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
                                tc = delta.get("tool_calls") or message.get("tool_calls") or []
                                if tc:
                                    yield _mk_chunk(tool_calls=tc)
                        except Exception:
                            pass

                        # usage + citations tail
                        try:
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
                # Log server error body for diagnostics
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

        :param model: ModelItem
        :return: Max tokens int
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

        :param prompt: Current user prompt
        :param system_prompt: System prompt
        :param model: ModelItem
        :param history: List of CtxItem for context
        :return: List of dicts with 'role' and 'content'
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

    def _extract_urls(self, raw) -> List[str]:
        """
        Normalize list of citations into a list of HTTP(S) URLs.

        Accepts either:
        - A list of strings (URLs)
        - A list of dicts with 'url' or 'uri' keys

        :param raw: Raw citations input
        :return: List of unique HTTP(S) URLs
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

        :param raw: Raw usage input
        :return: Normalized usage dict or None
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
        tot = raw.get("total_tokens")

        i = _as_int(in_tok or 0)
        o = _as_int(out_tok or 0)
        t = _as_int(tot if tot is not None else (i + o))
        return {"in": i, "out": max(0, t - i) if t else o, "reasoning": 0, "total": t}

    def _looks_like_http_messages(self, messages) -> bool:
        """
        Return True if 'messages' looks like an OpenAI-style array of dicts with 'role' and 'content'.

        :param messages: Messages input
        :return: True if looks like HTTP messages
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

        :param model_id: Model ID
        :param system_prompt: System prompt
        :param history: List of CtxItem for context
        :param prompt: Current user prompt
        :param attachments: Dict of AttachmentItem for images
        :return: List of dicts with 'role' and 'content' (and optional tool_calls)
        """
        self.window.core.api.xai.vision.reset()
        messages: List[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # history as plain user/assistant turns
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

        # Inject tool-turns from last ctx item
        self._append_tool_turns_from_ctx(messages, items)

        # Current user content (images first -> then text), validated
        parts: List[dict] = []
        img_found = False
        if attachments:
            # image constraints
            cfg = self.window.core.config
            max_bytes = int(cfg.get("xai_image_max_bytes") or self.default_image_max_bytes)

            for _, att in attachments.items():
                try:
                    if not (att and att.path):
                        continue
                    if not self.window.core.api.xai.vision.is_image(att.path):
                        continue
                    mime = self.window.core.api.xai.vision.guess_mime(att.path)
                    # Enforce allowed MIME
                    if mime not in self.allowed_mimes:
                        self.window.core.debug.error(f"[xai.vision] Unsupported image MIME: {mime}. Use JPEG/PNG.")
                        continue
                    # Enforce size
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

        # Append text part last when images exist
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

        :param messages: Messages list to append to
        :param items: List of CtxItem (history) to extract tool calls from
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

        # find last assistant message to attach tool_calls
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

        # append tool messages
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

        :param history: List of CtxItem
        :return: True if last item has tool calls and output
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

        :param attachments: Dict of AttachmentItem
        :return: True if at least one image attachment found
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

        :param model: ModelItem
        :return: True if model ID indicates vision capability
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

        :param tools: List of tool dicts or None
        :return: Normalized list of tool dicts
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

        :param cfg_endpoint: Configured endpoint or None
        :return: Normalized base URL string
        """
        base = (cfg_endpoint or "https://api.x.ai/v1").strip()
        if base.endswith("/"):
            base = base[:-1]
        return base

    def reset_tokens(self):
        """Reset input tokens counter."""
        self.input_tokens = 0

    def get_used_tokens(self) -> int:
        """
        Return the locally estimated input tokens count.

        :return: Input tokens int
        """
        return self.input_tokens