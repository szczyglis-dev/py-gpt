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

import json
import os
from typing import Optional, Dict, Any, List, Set

from pygpt_net.core.types import MODE_CHAT, MODE_AUDIO, MODE_COMPUTER
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

        # Tool result turn (Computer Use): if previous assistant emitted tool_use and we have tool output,
        # build a minimal message triplet: [user(prompt that triggered tool), assistant(tool_use), user(tool_result + images)].
        tool_result_messages = self._build_tool_result_messages_if_needed(
            model=model,
            history=context.history,
            attachments=attachments,
        )
        if tool_result_messages is not None:
            msgs = tool_result_messages
        else:
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

        # Build tools (client tools + Anthropic server tools)
        tools = api.tools.get_all_tools(model, functions)

        # Enable Computer Use tool in computer mode (use the official Tool/ComputerUse object)
        if mode == MODE_COMPUTER or (model and isinstance(model.id, str) and "computer-use" in model.id.lower()):
            tool = self.window.core.api.anthropic.computer.get_tool()
            tools = [tool]  # reset tools to only Computer Use (multiple tools not supported together)

        # MCP: servers from config
        mcp_servers = self._load_mcp_servers_from_cfg()

        # Compute betas required by selected server tools or MCP
        betas = self._compute_required_betas(tools, mcp_servers)

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
        if mcp_servers:
            params["mcp_servers"] = mcp_servers  # MCP connector servers per docs

        if mode == MODE_AUDIO:
            stream = False  # no native TTS

        # Decide whether to call stable or beta endpoint
        use_beta = len(betas) > 0

        if stream:
            if use_beta:
                return client.beta.messages.create(stream=True, betas=list(betas), **params)
            else:
                return client.messages.create(stream=True, **params)
        else:
            if use_beta:
                return client.beta.messages.create(betas=list(betas), **params)
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
                # include server_tool_use counts if present
                server_tool_use = {}
                if hasattr(usage, "server_tool_use"):
                    try:
                        server_tool_use = dict(getattr(usage, "server_tool_use"))
                    except Exception:
                        server_tool_use = {}
                ctx.extra["usage"] = {
                    "vendor": "anthropic",
                    "input_tokens": p,
                    "output_tokens": c,
                    "server_tool_use": server_tool_use,
                }
        except Exception:
            pass

        # Collect web search citations (web_search_tool_result blocks)
        try:
            self._collect_web_search_urls(response, ctx)
        except Exception:
            pass

        # Collect fetched URLs from web_fetch_tool_result blocks
        try:
            self._collect_web_fetch_urls(response, ctx)
        except Exception:
            pass

        # Download files referenced by code execution results (Files API)
        try:
            self._maybe_download_files_from_response(response, ctx)
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

    def _collect_web_fetch_urls(self, response: Message, ctx: CtxItem):
        """
        Collect URLs from web_fetch_tool_result blocks and attach to ctx.urls.

        :param response: Message response from API
        :param ctx: CtxItem to update
        """
        urls: List[str] = []
        try:
            for blk in getattr(response, "content", []) or []:
                if getattr(blk, "type", "") == "web_fetch_tool_result":
                    content = getattr(blk, "content", {}) or {}
                    if isinstance(content, dict):
                        if content.get("type") == "web_fetch_result":
                            u = (content.get("url") or "").strip()
                            if u.startswith("http://") or u.startswith("https://"):
                                urls.append(u)
                        # citations may embed multiple URLs
                        if content.get("type") == "web_fetch_result" and isinstance(content.get("citations"), list):
                            for cit in content["citations"]:
                                u = (cit.get("url") or "").strip()
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
            content = ""  # image-first; do not duplicate text if build_blocks already added it
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

    def _load_mcp_servers_from_cfg(self) -> List[dict]:
        """
        Load MCP servers definition from config JSON string(s).

        Supports keys:
          - remote_tools.anthropic.mcp.mcp_servers

        :return: list of MCP servers dicts
        """
        cfg = self.window.core.config
        enabled = cfg.get("remote_tools.anthropic.mcp", False)
        if not enabled:
            return []  # do not load if MCP is disabled
        raw = cfg.get("remote_tools.anthropic.mcp.mcp_servers")
        if not raw:
            return []
        try:
            if isinstance(raw, (list, dict)):
                # ensure list
                return list(raw) if isinstance(raw, list) else [raw]
            return json.loads(raw) or []
        except Exception:
            return []

    def _compute_required_betas(self, tools: List[dict], mcp_servers: List[dict]) -> Set[str]:
        """
        Compute required beta headers for enabled server tools.

        :param tools: Final tools list
        :param mcp_servers: MCP servers list
        :return: set of beta header strings
        """
        betas: Set[str] = set()
        is_mcp = False
        for t in tools or []:
            ttype = str(t.get("type") or "")
            if ttype.startswith("web_fetch_"):
                betas.add("web-fetch-2025-09-10")
            elif ttype.startswith("code_execution_"):
                betas.add("code-execution-2025-08-25")
            elif ttype in ("tool_search_tool_regex_20251119", "tool_search_tool_bm25_20251119"):
                betas.add("advanced-tool-use-2025-11-20")
            elif ttype == "mcp_toolset":
                is_mcp = True
                betas.add("mcp-client-2025-11-20")
            elif ttype.startswith("computer_"):
                betas.add("computer-use-2025-01-24")
        if is_mcp and mcp_servers:
            betas.add("mcp-client-2025-11-20")
        return betas

    # -------------------------- Tool Result helpers (Anthropic Computer Use) -------------------------- #

    def _build_tool_result_messages_if_needed(
            self,
            model: ModelItem,
            history: Optional[List[CtxItem]],
            attachments: Optional[Dict[str, AttachmentItem]],
    ) -> Optional[List[dict]]:
        """
        If the previous assistant turn emitted tool_use (computer) and the plugin produced tool_output,
        construct a minimal continuation with tool_result content block(s), as required by Anthropic.

        Returns a messages list or None.
        """
        if not self.window.core.config.get('use_context'):
            return None

        items: List[CtxItem] = self.window.core.ctx.get_history(
            history,
            model.id,
            MODE_CHAT,
            self.window.core.tokens.from_user("", ""),
            self._fit_ctx(model),
        )
        if not items:
            return None

        last = items[-1]
        if not isinstance(getattr(last, "extra", None), dict):
            return None

        tool_uses = last.extra.get("anthropic_tool_uses") or []
        tool_output = last.extra.get("tool_output") or []
        if not tool_uses or not tool_output:
            return None

        # Build prior user message (the one that triggered the tool use)
        prior_user_text = ""
        if len(items) >= 2 and getattr(items[-2], "final_input", None):
            prior_user_text = str(items[-2].final_input)
        elif getattr(last, "input", None):
            prior_user_text = str(last.input)

        user_msg_1 = None
        if prior_user_text:
            user_msg_1 = {"role": "user", "content": [{"type": "text", "text": prior_user_text}]}

        # Recreate assistant tool_use block(s)
        assistant_parts: List[dict] = []
        for tu in tool_uses:
            tid = str(tu.get("id", "") or "")
            name = str(tu.get("name", "") or "computer")
            inp = tu.get("input", {}) or {}
            assistant_parts.append({
                "type": "tool_use",
                "id": tid,
                "name": name,
                "input": inp,
            })
        assistant_msg = {"role": "assistant", "content": assistant_parts} if assistant_parts else None

        # Build tool_result with last tool output; attach screenshot images (if any) as additional blocks
        result_text = self._best_tool_result_text(tool_output)
        last_tool_use_id = str(tool_uses[-1].get("id", "") or "")

        tool_result_block = {
            "type": "tool_result",
            "tool_use_id": last_tool_use_id,
            "content": [{"type": "text", "text": result_text}],
        }

        # Convert current attachments to image blocks and append after tool_result in the same user message
        image_blocks: List[dict] = []
        if attachments:
            img_parts = self.window.core.api.anthropic.vision.build_blocks("", attachments)
            for part in img_parts:
                if isinstance(part, dict) and part.get("type") in ("image", "input_image", "document"):
                    image_blocks.append(part)

        user_msg_2 = {"role": "user", "content": [tool_result_block] + image_blocks}

        out: List[dict] = []
        if user_msg_1:
            out.append(user_msg_1)
        if assistant_msg:
            out.append(assistant_msg)
        out.append(user_msg_2)
        return out

    @staticmethod
    def _best_tool_result_text(tool_output: List[dict]) -> str:
        """
        Build a compact text payload from plugin tool_output list.
        Prefers the last item with 'result' field; falls back to the last dict JSON.
        """
        if not tool_output:
            return "ok"
        last = tool_output[-1]
        try:
            if isinstance(last, dict):
                if "result" in last:
                    val = last["result"]
                    if isinstance(val, (dict, list)):
                        return json.dumps(val, ensure_ascii=False)
                    return str(val)
                return json.dumps(last, ensure_ascii=False)
            return str(last)
        except Exception:
            return "ok"

    # -------------------------- Files download helpers -------------------------- #

    def _maybe_download_files_from_response(self, response: Message, ctx: CtxItem) -> None:
        """
        Scan response content blocks for Files API file_ids and download them.
        Works for code execution tool results that output files.
        """
        file_ids: List[str] = []

        def _to_plain(obj):
            try:
                if hasattr(obj, "model_dump"):
                    return obj.model_dump()
                if hasattr(obj, "to_dict"):
                    return obj.to_dict()
            except Exception:
                pass
            if isinstance(obj, dict):
                return {k: _to_plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_to_plain(x) for x in obj]
            return obj

        def _walk(o):
            if o is None:
                return
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == "file_id" and isinstance(v, str) and v.startswith("file_"):
                        if v not in file_ids:
                            file_ids.append(v)
                    else:
                        _walk(v)
            elif isinstance(o, (list, tuple)):
                for it in o:
                    _walk(it)

        try:
            for blk in getattr(response, "content", []) or []:
                btype = getattr(blk, "type", "") or ""
                # code_execution results appear as *_tool_result with nested 'content'
                if btype.endswith("_tool_result"):
                    content = getattr(blk, "content", None)
                    _walk(_to_plain(content))
        except Exception:
            pass

        if not file_ids:
            return

        saved: List[str] = []
        for fid in file_ids:
            try:
                path = self.window.core.api.anthropic.store.download_to_dir(fid)
                if path:
                    saved.append(path)
            except Exception:
                continue

        if saved:
            saved = self.window.core.filesystem.make_local_list(saved)
            if not isinstance(ctx.files, list):
                ctx.files = []
            for p in saved:
                if p not in ctx.files:
                    ctx.files.append(p)
            images = []
            for path in saved:
                ext = os.path.splitext(path)[1].lower().lstrip(".")
                if ext in ["png", "jpg", "jpeg", "gif", "bmp", "tiff", "webp"]:
                    images.append(path)
            if images:
                if not isinstance(ctx.images, list):
                    ctx.images = []
                ctx.images += images