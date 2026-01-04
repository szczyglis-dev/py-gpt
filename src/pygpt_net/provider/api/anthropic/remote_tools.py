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
from typing import List, Any, Dict, Optional

from pygpt_net.item.model import ModelItem

class RemoteTools:
    def __init__(self, window=None):
        """
        Remote tools mapper for Anthropic Messages API.

        :param window: Window instance
        """
        self.window = window

    def build_remote_tools(self, model: ModelItem = None) -> List[dict]:
        """
        Build Anthropic server tools (remote tools) based on config flags.
        Supports: Web Search, Code Execution, Web Fetch, Tool Search, MCP toolset.

        Returns a list of tool dicts to be appended to 'tools' in messages.create.

        :param model: ModelItem
        :return: List of remote tool dicts
        """
        cfg = self.window.core.config
        tools: List[dict] = []

        # keep compatibility with previous models that had no remote tool support
        if model and model.id and model.id.startswith("claude-3-5"):
            # remote tool availability on 3.5 models varies; previous behavior was to skip
            return tools

        # Helper: bool from config with provider-specific fallback
        def cfg_bool(*keys: str, default: bool = False) -> bool:
            for k in keys:
                v = cfg.get(k)
                if isinstance(v, bool):
                    return v
            return default

        def parse_csv_list(key: str) -> list:
            raw = cfg.get(key, "")
            if not raw:
                return []
            if isinstance(raw, list):
                return [str(x).strip() for x in raw if str(x).strip()]
            return [s.strip() for s in str(raw).split(",") if s.strip()]

        # --- Web Search (server tool) ---
        is_web = self.window.controller.chat.remote_tools.enabled(model, "web_search")
        if is_web:
            ttype = cfg.get("remote_tools.anthropic.web_search.type", "web_search_20250305")
            tname = "web_search"
            tool_def: Dict[str, Any] = {
                "type": ttype,
                "name": tname,
            }
            max_uses = cfg.get("remote_tools.anthropic.web_search.max_uses")
            if isinstance(max_uses, int) and max_uses > 0:
                tool_def["max_uses"] = max_uses
            allowed = parse_csv_list("remote_tools.anthropic.web_search.allowed_domains")
            blocked = parse_csv_list("remote_tools.anthropic.web_search.blocked_domains")
            if allowed:
                tool_def["allowed_domains"] = allowed
            elif blocked:
                tool_def["blocked_domains"] = blocked
            loc_city = cfg.get("remote_tools.anthropic.web_search.user_location.city")
            loc_region = cfg.get("remote_tools.anthropic.web_search.user_location.region")
            loc_country = cfg.get("remote_tools.anthropic.web_search.user_location.country")
            loc_tz = cfg.get("remote_tools.anthropic.web_search.user_location.timezone")
            if any([loc_city, loc_region, loc_country, loc_tz]):
                tool_def["user_location"] = {
                    "type": "approximate",
                    "city": str(loc_city) if loc_city else None,
                    "region": str(loc_region) if loc_region else None,
                    "country": str(loc_country) if loc_country else None,
                    "timezone": str(loc_tz) if loc_tz else None,
                }
                tool_def["user_location"] = {k: v for k, v in tool_def["user_location"].items() if v is not None}
            tools.append(tool_def)

        # --- Code Execution (server tool) ---
        is_code_exec = cfg_bool("remote_tools.anthropic.code_execution", default=False)
        if is_code_exec:
            tools.append({
                "type": "code_execution_20250825",
                "name": "code_execution",
            })

        # --- Web Fetch (server tool) ---
        is_web_fetch = cfg_bool("remote_tools.anthropic.web_fetch", default=False)
        if is_web_fetch:
            fetch_def: Dict[str, Any] = {
                "type": "web_fetch_20250910",
                "name": "web_fetch",
            }
            max_uses = cfg.get("remote_tools.anthropic.web_fetch.max_uses")
            if isinstance(max_uses, int) and max_uses > 0:
                fetch_def["max_uses"] = max_uses
            allowed = parse_csv_list("remote_tools.anthropic.web_fetch.allowed_domains")
            blocked = parse_csv_list("remote_tools.anthropic.web_fetch.blocked_domains")
            if allowed:
                fetch_def["allowed_domains"] = allowed
            elif blocked:
                fetch_def["blocked_domains"] = blocked
            citations_enabled = cfg_bool("remote_tools.anthropic.web_fetch.citations.enabled", default=True)
            if citations_enabled:
                fetch_def["citations"] = {"enabled": True}
            max_content_tokens = cfg.get("remote_tools.anthropic.web_fetch.max_content_tokens")
            if isinstance(max_content_tokens, int) and max_content_tokens > 0:
                fetch_def["max_content_tokens"] = max_content_tokens
            tools.append(fetch_def)

        # --- Tool Search (server tool) ---
        """
        is_tool_search = cfg_bool("remote_tools.anthropic.tool_search", default=False)
        if is_tool_search:
            variant = (cfg.get("remote_tools.anthropic.tool_search.variant")
                       or cfg.get("remote_tools.tool_search.variant") or "regex")
            # accept full type as well
            raw_type = str(cfg.get("remote_tools.anthropic.tool_search.type")
                           or cfg.get("remote_tools.tool_search.type") or "").strip()
            if raw_type.startswith("tool_search_tool_"):
                ttype = raw_type
                tname = "tool_search_tool_regex" if "regex" in raw_type else "tool_search_tool_bm25"
            else:
                if str(variant).lower() == "bm25":
                    ttype = "tool_search_tool_bm25_20251119"
                    tname = "tool_search_tool_bm25"
                else:
                    ttype = "tool_search_tool_regex_20251119"
                    tname = "tool_search_tool_regex"
            tools.append({
                "type": ttype,
                "name": tname,
            })
        """

        # --- MCP toolset (server-side tool catalog from MCP servers) ---
        is_mcp = cfg_bool("remote_tools.anthropic.mcp", default=False)
        if is_mcp:
            raw_tools = cfg.get("remote_tools.anthropic.mcp.tools")
            if raw_tools:
                try:
                    if isinstance(raw_tools, (list, dict)):
                        mcp_tools = raw_tools
                    else:
                        mcp_tools = json.loads(raw_tools)
                    # ensure list
                    if isinstance(mcp_tools, dict):
                        mcp_tools = [mcp_tools]
                    for t in mcp_tools:
                        if isinstance(t, dict):
                            # default type if not set
                            if "type" not in t:
                                t["type"] = "mcp_toolset"
                            tools.append(t)
                except Exception:
                    pass  # ignore invalid JSON to avoid breaking existing flows

        return tools