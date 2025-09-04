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

from typing import Optional, Dict, Any, List

from pygpt_net.core.types import MODE_CHAT, MODE_AUDIO
from pygpt_net.core.bridge.context import BridgeContext, MultimodalContext
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem

import anthropic
from anthropic.types import Message


class Chat:
    def __init__(self, window=None):
        """
        Anthropic chat / multimodal API wrapper.

        :param window: Window instance
        """
        self.window = window
        self.input_tokens = 0

    def send(self, context: BridgeContext, extra: Optional[Dict[str, Any]] = None):
        """
        Call Anthropic Messages API for chat / multimodal.

        :param context: BridgeContext
        :param extra: Extra parameters (not used)
        :return: Message or generator of Message (if streaming)
        """
        prompt = context.prompt
        stream = context.stream
        system_prompt = context.system_prompt
        model = context.model
        functions = context.external_functions
        attachments = context.attachments
        multimodal_ctx = context.multimodal_ctx
        mode = context.mode
        ctx = context.ctx or CtxItem()
        api = self.window.core.api.anthropic
        client: anthropic.Anthropic = api.get_client(context.mode, model)

        msgs = self.build_input(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            history=context.history,
            attachments=attachments,
            multimodal_ctx=multimodal_ctx,
        )

        self.reset_tokens()
        count_msgs = self._build_count_messages(prompt, system_prompt, model, context.history)
        self.input_tokens += self.window.core.tokens.from_messages(count_msgs, model.id)

        tools = api.tools.get_all_tools(model, functions)
        max_tokens = context.max_tokens if context.max_tokens else 1024
        temperature = self.window.core.config.get('temperature')
        top_p = self.window.core.config.get('top_p')

        params: Dict[str, Any] = {
            "model": model.id,
            "messages": msgs,
            "max_tokens": max_tokens,
        }
        # Add optional fields only if provided
        if system_prompt:
            params["system"] = system_prompt  # SDK expects string or blocks, not None
        if temperature is not None:
            params["temperature"] = temperature  # keep as-is; upstream config controls the type
        if top_p is not None:
            params["top_p"] = top_p
        if tools:  # only include when non-empty list
            params["tools"] = tools  # must be a valid list per API

        if mode == MODE_AUDIO:
            stream = False  # no native TTS

        if stream:
            return client.messages.create(stream=True, **params)
        else:
            return client.messages.create(**params)

    def unpack_response(self, mode: str, response: Message, ctx: CtxItem):
        """
        Unpack non-streaming response and set context.

        :param mode: Mode (chat/audio)
        :param response: Message response from API
        :param ctx: CtxItem to update
        """
        ctx.output = self.extract_text(response)

        calls = self.extract_tool_calls(response)
        if calls:
            ctx.tool_calls = calls

        # Usage
        try:
            usage = getattr(response, "usage", None)
            if usage:
                p = getattr(usage, "input_tokens", 0) or 0
                c = getattr(usage, "output_tokens", 0) or 0
                ctx.set_tokens(p, c)
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra["usage"] = {"vendor": "anthropic", "input_tokens": p, "output_tokens": c}
        except Exception:
            pass

        # Collect web search citations (web_search_tool_result blocks)
        try:
            self._collect_web_search_urls(response, ctx)
        except Exception:
            pass

    def extract_text(self, response: Message) -> str:
        """
        Extract text from response content blocks.

        Join all text blocks into a single string.

        :param response: Message response from API
        :return: Extracted text
        """
        out: List[str] = []
        try:
            for blk in getattr(response, "content", []) or []:
                if getattr(blk, "type", "") == "text" and getattr(blk, "text", None):
                    out.append(str(blk.text))
        except Exception:
            pass
        return "".join(out).strip()

    def extract_tool_calls(self, response: Message) -> List[dict]:
        """
        Extract tool_use blocks as app tool calls.

        Each tool call is a dict with keys: id (str), type="function", function (dict with name and arguments).

        :param response: Message response from API
        :return: List of tool calls
        """
        out: List[dict] = []

        def to_plain(obj):
            try:
                if hasattr(obj, "model_dump"):
                    return obj.model_dump()
                if hasattr(obj, "to_dict"):
                    return obj.to_dict()
            except Exception:
                pass
            if isinstance(obj, dict):
                return {k: to_plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [to_plain(x) for x in obj]
            return obj

        try:
            for blk in getattr(response, "content", []) or []:
                if getattr(blk, "type", "") == "tool_use":
                    out.append({
                        "id": getattr(blk, "id", "") or "",
                        "type": "function",
                        "function": {
                            "name": getattr(blk, "name", "") or "",
                            "arguments": to_plain(getattr(blk, "input", {}) or {}),
                        }
                    })
        except Exception:
            pass
        return out

    def _collect_web_search_urls(self, response: Message, ctx: CtxItem):
        """
        Collect URLs from web_search_tool_result blocks and attach to ctx.urls.

        :param response: Message response from API
        :param ctx: CtxItem to update
        """
        urls: List[str] = []
        try:
            for blk in getattr(response, "content", []) or []:
                if getattr(blk, "type", "") == "web_search_tool_result":
                    content = getattr(blk, "content", None) or []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "web_search_result":
                            u = (item.get("url") or "").strip()
                            if u.startswith("http://") or u.startswith("https://"):
                                urls.append(u)
        except Exception:
            pass

        if urls:
            if ctx.urls is None:
                ctx.urls = []
            for u in urls:
                if u not in ctx.urls:
                    ctx.urls.append(u)

    def build_input(
            self,
            prompt: str,
            system_prompt: str,
            model: ModelItem,
            history: Optional[List[CtxItem]] = None,
            attachments: Optional[Dict[str, AttachmentItem]] = None,
            multimodal_ctx: Optional[MultimodalContext] = None) -> List[dict]:
        """
        Build Anthropic messages list.

        :param prompt: User prompt
        :param system_prompt: System prompt
        :param model: ModelItem
        :param history: Optional list of CtxItem for context
        :param attachments: Optional dict of attachments (id -> AttachmentItem)
        :param multimodal_ctx: Optional MultimodalContext
        :return: List of messages for API
        """
        messages: List[dict] = []

        if self.window.core.config.get('use_context'):
            items = self.window.core.ctx.get_history(
                history,
                model.id,
                MODE_CHAT,
                self.window.core.tokens.from_user(prompt, system_prompt),
                self._fit_ctx(model),
            )
            for item in items:
                if item.final_input:
                    messages.append({"role": "user", "content": str(item.final_input)})
                if item.final_output:
                    messages.append({"role": "assistant", "content": str(item.final_output)})

        parts = self._build_user_parts(
            content=str(prompt or ""),
            attachments=attachments,
            multimodal_ctx=multimodal_ctx,
        )
        messages.append({"role": "user", "content": parts if parts else [{"type": "text", "text": str(prompt or "")}]})
        return messages

    def _build_user_parts(
            self,
            content: str,
            attachments: Optional[Dict[str, AttachmentItem]] = None,
            multimodal_ctx: Optional[MultimodalContext] = None) -> List[dict]:
        """
        Build user content blocks (image + text).

        :param content: Text content
        :param attachments: Optional dict of attachments (id -> AttachmentItem)
        :param multimodal_ctx: Optional MultimodalContext
        :return: List of content blocks
        """
        parts: List[dict] = []
        self.window.core.api.anthropic.vision.reset()
        if attachments:
            img_parts = self.window.core.api.anthropic.vision.build_blocks(content, attachments)
            parts.extend(img_parts)
        if content:
            parts.append({"type": "text", "text": str(content)})

        # No input_audio supported in SDK at the time of writing
        if multimodal_ctx and getattr(multimodal_ctx, "is_audio_input", False):
            pass

        return parts

    def _fit_ctx(self, model: ModelItem) -> int:
        """
        Fit context length to model limits.

        :param model: ModelItem
        :return: Max context tokens
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
            history: Optional[List[CtxItem]] = None) -> List[dict]:
        """
        Build messages for token counting (without attachments).

        :param prompt: User prompt
        :param system_prompt: System prompt
        :param model: ModelItem
        :param history: Optional list of CtxItem for context
        :return: List of messages for token counting
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if self.window.core.config.get('use_context'):
            used_tokens = self.window.core.tokens.from_user(prompt, system_prompt)
            items = self.window.core.ctx.get_history(
                history,
                model.id,
                MODE_CHAT,
                used_tokens,
                self._fit_ctx(model),
            )
            for item in items:
                if item.final_input:
                    messages.append({"role": "user", "content": str(item.final_input)})
                if item.final_output:
                    messages.append({"role": "assistant", "content": str(item.final_output)})

        messages.append({"role": "user", "content": str(prompt or "")})
        return messages

    def reset_tokens(self):
        """Reset input tokens counter."""
        self.input_tokens = 0

    def get_used_tokens(self) -> int:
        """
        Get used input tokens count.

        :return: used input tokens
        """
        return self.input_tokens