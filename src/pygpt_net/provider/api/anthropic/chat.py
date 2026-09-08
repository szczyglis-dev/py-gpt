#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.08.12 12:00:00                  #
# ================================================== #

import json
import os
import re
from typing import Optional, Dict, Any, List, Set

from pygpt_net.core.types import MODE_CHAT, MODE_AUDIO, MODE_COMPUTER
from pygpt_net.core.bridge.context import BridgeContext, MultimodalContext
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from pygpt_net.provider.api.reasoning import ensure_reasoning_metadata, store_reasoning

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
            tool = self.window.core.api.anthropic.computer.get_tool(model=model)
            tools = [tool]  # reset tools to only Computer Use (multiple tools not supported together)

        # MCP: servers from config
        mcp_servers = self._load_mcp_servers_from_cfg()

        # Compute betas required by selected server tools or MCP
        betas = self._compute_required_betas(tools, mcp_servers)
        if self.window.core.attachments.native.get_refs(attachments, "anthropic"):
            betas.add("files-api-2025-04-14")

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
        # Claude 4.x: top_p is rejected when temperature is also present.
        # Opus 4.x and claude-3-7-sonnet have deprecated temperature entirely (extended thinking).
        _no_temp = ("claude-opus-4-", "claude-3-7-sonnet", "claude-fable-5", "claude-opus-5", "claude-sonnet-5")
        if temperature is not None and not any(model.id.startswith(p) for p in _no_temp):
            params["temperature"] = temperature
        if tools:  # only include when non-empty list
            params["tools"] = tools  # must be a valid list per API
        if mcp_servers:
            params["mcp_servers"] = mcp_servers  # MCP connector servers per docs

        # Request readable summarized thinking only where it does not interfere
        # with the app's separate client/server-tool continuation flow. Anthropic
        # requires thinking blocks/signatures to be preserved across tool turns;
        # until that whole tool transcript is round-tripped here, keep automatic
        # thinking display to plain chat requests.
        no_tools = not tools and not mcp_servers and mode != MODE_COMPUTER
        model_id_lc = str(model.id or "").lower()
        thinking_cfg = None
        if no_tools:
            # Claude 4.6+ and Claude 5 use adaptive thinking.
            version_match = re.search(r"-4-(\d+)(?:-|$)", model_id_lc)
            is_adaptive = (
                bool(version_match and int(version_match.group(1)) >= 6)
                or bool(re.search(r"-(?:opus|sonnet|fable|haiku|mythos)-5(?:-|$)", model_id_lc))
            )
            if is_adaptive:
                thinking_cfg = {"type": "adaptive", "display": "summarized"}
            # Claude 4.5 / 3.7 use legacy fixed-budget extended thinking.
            elif ("-4-5" in model_id_lc or "claude-3-7-sonnet" in model_id_lc) and max_tokens > 1024:
                budget = min(4096, max(1024, max_tokens // 2), max_tokens - 1)
                thinking_cfg = {
                    "type": "enabled",
                    "budget_tokens": budget,
                    "display": "summarized",
                }

        if thinking_cfg is not None:
            params["thinking"] = thinking_cfg
            # Sampling temperature is incompatible with thinking on affected
            # Claude generations; default sampling is the safest common path.
            params.pop("temperature", None)

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
        reasoning = self.extract_reasoning(response)
        if reasoning:
            store_reasoning(
                ctx, provider="anthropic", text=reasoning,
                kind="thinking_summary", raw=False, visible=True,
            )
            signatures = self.extract_thinking_signatures(response)
            if signatures:
                ctx.extra["reasoning"]["signatures"] = signatures

        calls = self.extract_tool_calls(response)
        if calls:
            # Keep the raw Anthropic computer tool_use block for the required
            # tool_result continuation, then map its action to PyGPT plugin calls.
            raw_computer_uses = []
            try:
                for block in getattr(response, "content", None) or []:
                    if getattr(block, "type", "") != "tool_use":
                        continue
                    name = str(getattr(block, "name", "") or "")
                    toolset_name = str(getattr(block, "toolset_name", "") or "")
                    computer = self.window.core.api.anthropic.computer
                    is_legacy = name in computer.COMPUTER_TOOL_NAMES
                    is_toolset = toolset_name == "computer" and name in computer.TOOLSET_MEMBER_NAMES
                    if not (is_legacy or is_toolset):
                        continue
                    record = {
                        "id": str(getattr(block, "id", "") or ""),
                        "name": name,
                        "input": getattr(block, "input", {}) or {},
                    }
                    if toolset_name:
                        record["toolset_name"] = toolset_name
                        if not isinstance(ctx.extra, dict):
                            ctx.extra = {}
                        ctx.extra["computer_stop_on_error"] = True
                    raw_computer_uses.append(record)
            except Exception:
                raw_computer_uses = []
            if raw_computer_uses:
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra["anthropic_tool_uses"] = raw_computer_uses
                ctx.tool_calls = self.window.core.api.anthropic.computer.rewrite_tool_calls(calls)
            else:
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
                details = getattr(usage, "output_tokens_details", None)
                thinking_tokens = getattr(details, "thinking_tokens", 0) if details else 0
                ctx.extra["usage"] = {
                    "vendor": "anthropic",
                    "input_tokens": p,
                    "output_tokens": c,
                    "reasoning_tokens": thinking_tokens or 0,
                    "server_tool_use": server_tool_use,
                }
                ensure_reasoning_metadata(ctx, "anthropic", thinking_tokens)
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

    def extract_reasoning(self, response: Message) -> str:
        """Extract Anthropic summarized thinking blocks."""
        out: List[str] = []
        try:
            for blk in getattr(response, "content", []) or []:
                if getattr(blk, "type", "") == "thinking" and getattr(blk, "thinking", None):
                    out.append(str(blk.thinking))
        except Exception:
            pass
        return "".join(out).strip()

    def extract_thinking_signatures(self, response: Message) -> List[str]:
        """Extract integrity signatures associated with thinking blocks."""
        out: List[str] = []
        try:
            for blk in getattr(response, "content", []) or []:
                if getattr(blk, "type", "") != "thinking":
                    continue
                signature = getattr(blk, "signature", None)
                if signature:
                    out.append(str(signature))
        except Exception:
            pass
        return out

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
                    call = {
                        "id": getattr(blk, "id", "") or "",
                        "type": "function",
                        "function": {
                            "name": getattr(blk, "name", "") or "",
                            "arguments": to_plain(getattr(blk, "input", {}) or {}),
                        }
                    }
                    toolset_name = getattr(blk, "toolset_name", None)
                    if toolset_name:
                        call["toolset_name"] = str(toolset_name)
                    out.append(call)
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
        if content:
            parts.append({"type": "text", "text": str(content)})
        for ref in self.window.core.attachments.native.get_refs(attachments, "anthropic"):
            parts.append({
                "type": "document",
                "source": {
                    "type": "file",
                    "file_id": ref["id"],
                },
            })

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
            elif ttype == "computer_20251124":
                betas.add("computer-use-2025-11-24")
            elif ttype == "computer_20250124":
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

        # Recreate every assistant tool_use exactly as Anthropic emitted it.
        assistant_parts: List[dict] = []
        for tu in tool_uses:
            block = {
                "type": "tool_use",
                "id": str(tu.get("id", "") or ""),
                "name": str(tu.get("name", "") or "computer"),
                "input": tu.get("input", {}) or {},
            }
            if tu.get("toolset_name"):
                block["toolset_name"] = str(tu.get("toolset_name"))
            assistant_parts.append(block)
        assistant_msg = {"role": "assistant", "content": assistant_parts} if assistant_parts else None

        # Computer toolset requires exactly one tool_result for every member tool_use,
        # in the same order. A screenshot image belongs inside the screenshot result.
        image_blocks: List[dict] = []
        if attachments:
            for part in self.window.core.api.anthropic.vision.build_blocks("", attachments):
                if isinstance(part, dict) and part.get("type") in ("image", "input_image"):
                    image_blocks.append(part)
        screenshot_block = image_blocks[0] if image_blocks else None

        result_blocks: List[dict] = []
        has_toolset_batch = any(str(tu.get("toolset_name", "") or "") == "computer" for tu in tool_uses)
        for index, tu in enumerate(tool_uses):
            # Toolset calls map 1:1 to local outputs. Legacy `computer` payloads may
            # expand internally, so preserve the old behavior of using the final result.
            if has_toolset_batch:
                output = tool_output[index] if index < len(tool_output) else None
            else:
                output = tool_output[index] if len(tool_uses) > 1 and index < len(tool_output) else tool_output[-1]
            name = str(tu.get("name", "") or "computer")
            toolset_name = str(tu.get("toolset_name", "") or "")
            text, is_error = self._tool_result_text(output)
            if toolset_name == "computer" and name == "cursor_position" and not is_error:
                try:
                    value = output.get("result", {}) if isinstance(output, dict) else {}
                    if isinstance(value, dict) and value.get("mouse_x") is not None and value.get("mouse_y") is not None:
                        text = f"X={int(value['mouse_x'])}, Y={int(value['mouse_y'])}"
                except Exception:
                    pass
            content: List[dict]
            if toolset_name == "computer" and name in ("screenshot", "zoom") and screenshot_block and not is_error:
                content = [screenshot_block]
            else:
                content = [{"type": "text", "text": text or "OK"}]
            result = {
                "type": "tool_result",
                "tool_use_id": str(tu.get("id", "") or ""),
                "content": content,
            }
            if toolset_name:
                result["toolset_name"] = toolset_name
            if is_error:
                result["is_error"] = True
            result_blocks.append(result)

        # Native user attachments are unrelated to Computer Use transport screenshots.
        native_blocks: List[dict] = []
        for ref in self.window.core.attachments.native.get_refs(attachments, "anthropic"):
            native_blocks.append({
                "type": "document",
                "source": {"type": "file", "file_id": ref["id"]},
            })

        extra_legacy_images = [] if has_toolset_batch else image_blocks
        user_msg_2 = {"role": "user", "content": result_blocks + extra_legacy_images + native_blocks}

        out: List[dict] = []
        if user_msg_1:
            out.append(user_msg_1)
        if assistant_msg:
            out.append(assistant_msg)
        out.append(user_msg_2)
        return out

    @staticmethod
    def _tool_result_text(output) -> tuple[str, bool]:
        if output is None:
            return "Missing tool output", True
        try:
            if isinstance(output, dict):
                value = output.get("result", output)
                if isinstance(value, dict):
                    error = value.get("error")
                    if error:
                        return str(error), True
                    status = str(value.get("result", "") or "").lower()
                    if status in {"error", "failed", "failure"}:
                        return json.dumps(value, ensure_ascii=False), True
                    # Toolset ordinary actions only need a short success result.
                    if status == "success" or value.get("ok") is True:
                        return "OK", False
                    return json.dumps(value, ensure_ascii=False), False
                text = str(value)
                return text, text.lower().startswith("error")
            return str(output), False
        except Exception:
            return "OK", False

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