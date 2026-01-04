#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.04 19:00:00                  #
# ================================================== #

from __future__ import annotations

import json
from typing import Optional, Dict, Any, List, Tuple

from pygpt_net.core.types import MODE_CHAT
from pygpt_net.core.bridge.context import BridgeContext, MultimodalContext
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem

# xAI SDK chat helpers (system/user/assistant/image) for message building
from xai_sdk.chat import (
    system as xsystem,
    user as xuser,
    assistant as xassistant,
    image as ximage,
    tool_result as xtool_result
)

# get_tool_call_type helps filter client-side vs server-side tools
try:
    from xai_sdk.tools import get_tool_call_type as x_get_tool_call_type
except Exception:
    x_get_tool_call_type = None


class Responses:
    def __init__(self, window=None):
        """
        Chat wrapper for xAI using Chat Responses via xai_sdk.

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0
        # Image constraints
        self.allowed_mimes = {"image/jpeg", "image/png"}
        self.default_image_max_bytes = 10 * 1024 * 1024  # 10 MiB default

    # ---------- SEND (Chat Responses) ----------

    def send(self, context: BridgeContext, extra: Optional[Dict[str, Any]] = None):
        """
        Entry point for xAI chat/multimodal using Chat Responses (stateful).

        Streaming:
        - Uses xai_sdk chat.stream() (tuples of (response, chunk)).

        Non-stream:
        - Uses xai_sdk chat.sample().

        Client-side tools:
        - Prepared from app functions and mixed with server-side tools.
        - Only client-side tool calls are returned in ctx.tool_calls (server-side are executed on xAI).

        :param context: BridgeContext with all parameters
        :param extra: Extra parameters (not used)
        :return: SDK response object (non-stream) or an iterable for streaming (generator/iterator)
        """
        prompt = context.prompt
        system_prompt = context.system_prompt
        model_item = context.model
        functions = context.external_functions
        attachments = context.attachments
        multimodal_ctx = context.multimodal_ctx
        stream = context.stream
        history = context.history
        ctx = context.ctx or CtxItem()

        client = self.window.core.api.xai.get_client(context.mode, model_item)

        # Local input token estimate (best effort)
        self.reset_tokens()
        cnt_msgs = self._build_count_messages(prompt, system_prompt, model_item, history)
        self.input_tokens += self.window.core.tokens.from_messages(cnt_msgs, model_item.id)

        # Remote (server-side) tools and include flags
        rt_cfg = self.window.core.api.xai.remote.build_for_chat(
            model=model_item,
            stream=stream,
        )
        srv_tools = rt_cfg.get("tools", []) or []
        include = rt_cfg.get("include", []) or []
        use_encrypted = bool(rt_cfg.get("use_encrypted_content", False))
        max_turns = rt_cfg.get("max_turns", None)

        # Client-side tools (from app functions)
        client_tools = self.window.core.api.xai.tools.prepare_sdk_tools(functions)
        all_tools = (srv_tools + client_tools) if (srv_tools or client_tools) else None

        # Vision fallback if needed
        has_images = self._attachments_have_images(attachments)
        model_id = model_item.id
        if has_images and not self._is_vision_model(model_item):
            fb = self.window.core.config.get("xai_vision_fallback_model") or "grok-2-vision-latest"
            self.window.core.debug.info(f"[xai] Switching to vision model: {fb} (was: {model_id}) due to image input")
            model_id = fb

        # Store messages: false when images present (SDK guidance), otherwise configurable (default True)
        store_messages = True
        cfg_store = self.window.core.config.get("remote_tools.xai.store_messages")
        if cfg_store is not None:
            try:
                store_messages = bool(cfg_store)
            except Exception:
                pass
        if has_images:
            store_messages = False

        # previous_response_id from last history item or current ctx
        prev_id = self._detect_previous_response_id(history, ctx)

        # Create chat session in SDK
        chat_kwargs: Dict[str, Any] = {
            "model": model_id,
            "tools": all_tools,
            "include": (include if include else None),
            "store_messages": store_messages,
            "previous_response_id": prev_id,
        }
        if use_encrypted:
            chat_kwargs["use_encrypted_content"] = True
        if isinstance(max_turns, int) and max_turns > 0:
            chat_kwargs["max_turns"] = max_turns

        chat = client.chat.create(**chat_kwargs)

        # Append history (only when not continuing via previous_response_id)
        self.append_history_sdk(
            chat=chat,
            system_prompt=system_prompt,
            model=model_item,
            history=history if prev_id is None else None,  # do not duplicate when chaining
        )

        # If last turn contained client-side tool outputs, append them first
        self._append_tool_results_from_ctx(chat, history)

        # Append current user message (with images if any)
        self.append_current_user_sdk(
            chat=chat,
            prompt=prompt,
            attachments=attachments,
            multimodal_ctx=multimodal_ctx,
        )

        # STREAMING: return raw iterator (handler attaches ctx.msg_id)
        if stream:
            return chat.stream()

        # NON-STREAM
        response = chat.sample()
        return response

    # ---------- UNPACK (non-stream) ----------

    def unpack_response(self, mode: str, response, ctx: CtxItem):
        """
        Unpack non-streaming xAI response into ctx (text, tool calls, usage, citations, images).

        :param mode: mode (chat, etc)
        :param response: Response object from SDK or dict
        :param ctx: CtxItem to fill
        """
        # Output text
        out = ""
        try:
            out = getattr(response, "content", None) or ""
        except Exception:
            pass
        if not out and isinstance(response, dict):
            out = response.get("output_text") or ""

        ctx.output = (str(out or "")).strip()

        # Citations (list of urls)
        try:
            cits = getattr(response, "citations", None)
            if isinstance(cits, list) and cits:
                if ctx.urls is None:
                    ctx.urls = []
                for u in cits:
                    if isinstance(u, str) and (u.startswith("http://") or u.startswith("https://")):
                        if u not in ctx.urls:
                            ctx.urls.append(u)
        except Exception:
            pass

        # Tool calls: only return client-side tools to be executed by the app
        try:
            raw_calls = getattr(response, "tool_calls", None) or []
            client_side = []
            for tc in raw_calls:
                # filter client-side tool calls using SDK helper when available
                ttype = None
                if x_get_tool_call_type is not None:
                    try:
                        ttype = x_get_tool_call_type(tc)
                    except Exception:
                        ttype = None
                # treat as client-side when helper says so, or when object looks like function call
                if ttype == "client_side_tool" or self._looks_like_client_tool(tc):
                    fn = getattr(tc, "function", None)
                    name = getattr(fn, "name", "") if fn is not None else ""
                    args = getattr(fn, "arguments", "") if fn is not None else ""
                    if isinstance(args, (dict, list)):
                        try:
                            args = json.dumps(args, ensure_ascii=False)
                        except Exception:
                            args = str(args)
                    client_side.append({
                        "id": getattr(tc, "id", "") or "",
                        "type": "function",
                        "function": {"name": name or "", "arguments": args or ""},
                    })
            if client_side:
                ctx.tool_calls = client_side
        except Exception:
            pass

        # Usage
        try:
            usage = getattr(response, "usage", None)
            if isinstance(usage, dict):
                u = self._normalize_usage(usage)
            else:
                # Sometimes SDK exposes usage as object with attributes
                u = self._normalize_usage({
                    "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                    "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
                    "reasoning_tokens": getattr(usage, "reasoning_tokens", 0) if usage else 0,
                })
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
        except Exception:
            pass

        # Response ID
        try:
            rid = getattr(response, "id", None)
            if not rid and isinstance(response, dict):
                rid = response.get("id")
            if rid:
                ctx.msg_id = str(rid)
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra["xai_response_id"] = ctx.msg_id
        except Exception:
            pass

    # ---------- SDK message building helpers ----------

    def append_history_sdk(
        self,
        chat,
        system_prompt: Optional[str],
        model: ModelItem,
        history: Optional[List[CtxItem]] = None,
    ):
        """
        Append history to SDK chat (only when not using previous_response_id).

        :param chat: xai_sdk chat instance
        :param system_prompt: system prompt
        :param model: model item
        :param history: history items
        """
        if history is None:
            # initial turn, append system only (if any)
            if system_prompt:
                chat.append(xsystem(system_prompt))
            return

        # system prompt first (if any)
        if system_prompt:
            chat.append(xsystem(system_prompt))

        # history pairs
        if self.window.core.config.get('use_context'):
            used = self.window.core.tokens.from_user("", system_prompt or "")
            items = self.window.core.ctx.get_history(
                history, model.id, MODE_CHAT, used, self._fit_ctx(model),
            )
            for item in items:
                if item.final_input:
                    chat.append(xuser(str(item.final_input)))
                if item.final_output:
                    chat.append(xassistant(str(item.final_output)))

    def append_current_user_sdk(
        self,
        chat,
        prompt: str,
        attachments: Optional[Dict[str, AttachmentItem]],
        multimodal_ctx: Optional[MultimodalContext],
    ):
        """
        Append current user message with optional inline images.

        :param chat: xai_sdk chat instance
        :param prompt: user text
        :param attachments: attachments dict (images)
        :param multimodal_ctx: multimodal context (not used here)
        """
        parts = [str(prompt or "")]
        for img in self.window.core.api.xai.vision.build_images_for_chat(attachments):
            parts.append(ximage(img))
        chat.append(xuser(*parts))

    def _append_tool_results_from_ctx(self, chat, history: Optional[List[CtxItem]]):
        """
        Append tool results from the last ctx item when function-calling loop is active.
        """
        tool_call_native_enabled = self.window.core.config.get('func_call.native', False)
        if not (history and tool_call_native_enabled):
            return
        last = history[-1]
        if not (last.extra and isinstance(last.extra, dict)):
            return
        tool_output = last.extra.get("tool_output")
        if not (tool_output and isinstance(tool_output, list)):
            return

        for out in tool_output:
            # accept direct result value or whole dict
            if isinstance(out, dict) and "result" in out:
                chat.append(xtool_result(str(out["result"])))
            else:
                chat.append(xtool_result(str(out)))

    # ---------- legacy/local utils ----------

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

    def _looks_like_client_tool(self, tc_obj) -> bool:
        """
        Best-effort detection of a client-side tool call when helper is not available.
        """
        try:
            fn = getattr(tc_obj, "function", None)
            if fn is None:
                return False
            name = getattr(fn, "name", None)
            # arguments can be str/dict/list; presence indicates structured call
            has_args = hasattr(fn, "arguments")
            return isinstance(name, str) and name != "" and has_args
        except Exception:
            return False

    def _detect_previous_response_id(self, history: Optional[List[CtxItem]], ctx: CtxItem) -> Optional[str]:
        """
        Return last response id from history or current ctx when available.
        """
        try:
            if history and len(history) > 0:
                last = history[-1]
                if last and last.msg_id:
                    return str(last.msg_id)
        except Exception:
            pass
        try:
            if ctx and ctx.msg_id:
                return str(ctx.msg_id)
        except Exception:
            pass
        return None

    def reset_tokens(self):
        """Reset input tokens counter."""
        self.input_tokens = 0

    def get_used_tokens(self) -> int:
        """
        Return the locally estimated input tokens count.
        """
        return self.input_tokens

    # ---------- helpers for quick_call compatibility ----------

    def quick_collect_response_id(self, response, ctx: CtxItem):
        """
        Set response id and xai_response_id after non-stream sample() in quick paths.

        :param response: Response object from SDK or dict
        :param ctx: CtxItem to fill
        """
        try:
            rid = getattr(response, "id", None)
            if rid:
                ctx.msg_id = str(rid)
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra["xai_response_id"] = ctx.msg_id
        except Exception:
            pass