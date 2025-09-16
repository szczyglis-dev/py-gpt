#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.16 22:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        """
        Set default options for plugin

        :param plugin: plugin instance
        """
        keys = {
            "active": "bool",
            "label": "text",
            "server_address": "text",
            "authorization": "text",
            "allowed_commands": "text",
            "disabled_commands": "text",
        }
        items = [
            {
                "active": False,
                "label": "quickstart",
                "server_address": "stdio: uv run server fastmcp_quickstart stdio",
                "authorization": "",
                "allowed_commands": "",
                "disabled_commands": "",
            },
            {
                "active": False,
                "label": "local_http",
                "server_address": "http://localhost:8000/mcp",
                "authorization": "",
                "allowed_commands": "",
                "disabled_commands": "",
            },
            {
                "active": False,
                "label": "local_sse",
                "server_address": "http://localhost:8000/sse",
                "authorization": "",
                "allowed_commands": "",
                "disabled_commands": "",
            },
            {
                "active": False,
                "label": "deep_wiki",
                "server_address": "https://mcp.deepwiki.com/mcp",
                "authorization": "",
                "allowed_commands": "",
                "disabled_commands": "",
            },
        ]
        desc = (
            "Configure MCP servers. Supported transports: "
            "'stdio: <command ...>' for stdio servers, 'http(s)://...' for Streamable HTTP, "
            "and 'http(s)://.../sse' (or 'sse://', 'sse+http(s)://') for SSE. "
            "Use 'label' as a short, human-friendly server name used in tool names. "
            "Use 'authorization' to send an Authorization header for HTTP/SSE connections. "
            "Use 'allowed_commands' (comma-separated) to whitelist tools; "
            "use 'disabled_commands' to blacklist tools."
        )
        tooltip = "Requires MCP Python SDK. Install: pip install \"mcp[cli]\""
        plugin.add_option(
            "servers",
            type="dict",
            value=items,
            label="MCP servers",
            description=desc,
            tooltip=tooltip,
            keys=keys,
        )

        plugin.add_option(
            "tools_cache_enabled",
            type="bool",
            value=True,
            label="Cache tools list",
            description="Enable in-memory cache for discovered tools to avoid re-discovery on each prompt.",
            tooltip="If enabled, tools discovery results are cached per server.",
        )
        plugin.add_option(
            "tools_cache_ttl",
            type="text",
            value="300",
            label="Cache TTL (seconds)",
            description="Time-to-live for tools cache per server.",
            tooltip="Set to 0 to disable TTL (not recommended).",
        )