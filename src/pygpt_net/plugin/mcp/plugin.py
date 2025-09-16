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

import asyncio
import hashlib
import re
import shlex
import time
from typing import Dict, List, Tuple, Any, Optional
from urllib.parse import urlparse

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem

from .config import Config


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "mcp"
        self.name = "MCP"
        self.description = "Use remote tools via MCP"
        self.prefix = "RemoteTool"
        self.order = 100
        self.use_locale = True
        self.worker = None
        self.config = Config(self)
        self.init_options()

        # Runtime index for quick execution lookup
        self.tools_index: Dict[str, Dict[str, Any]] = {}

        # In-memory discovery cache (per server)
        self._tools_cache: Dict[str, Dict[str, Any]] = {}
        self._last_config_signature: Optional[str] = None

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: event args
        :param kwargs: event kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data['commands'],
            )

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX
        Build "cmd" entries based on tools discovered from active MCP servers.
        Applies allow/deny per server. Uses cache with TTL.

        :param data: event data dict
        """
        servers: List[dict] = self.get_option_value("servers") or []
        active_servers = [(i, s) for i, s in enumerate(servers) if s.get("active", False)]
        self.tools_index.clear()

        if len(active_servers) == 0:
            return

        # Invalidate cache if config changed
        current_sig = self._config_signature(active_servers)
        if current_sig != self._last_config_signature:
            self._tools_cache.clear()
            self._last_config_signature = current_sig

        try:
            discovered = self._discover_tools_sync(active_servers)
        except Exception as e:
            self.error(e)
            self.error(f"MCP: discovery failed: {e}")
            return

        used_names = set()  # to ensure unique tool names in this batch

        for (server_idx, server_tag, transport, tool, server_cfg) in discovered:
            tool_name = getattr(tool, "name", None) or tool.get("name")
            description = getattr(tool, "description", None) or tool.get("description")
            input_schema = getattr(tool, "inputSchema", None) or tool.get("inputSchema")

            # Human-friendly display name
            display_name = tool_name
            try:
                from mcp.shared.metadata_utils import get_display_name  # type: ignore
                display_name = get_display_name(tool) or tool_name
            except Exception:
                pass

            # Server label -> used in tool name (avoid dots and other invalid chars)
            server_label = (server_cfg.get("label") or server_tag or f"srv{server_idx}").strip()
            server_slug = self._slugify(server_label)

            # Compose final tool "cmd" name acceptable by OpenAI: ^[a-zA-Z0-9_-]+$, <=64 chars
            cmd_name = self._compose_cmd_name(server_slug, tool_name, used_names)
            used_names.add(cmd_name)

            params = self.extract_params_from_schema(input_schema)

            # Instruction for the model
            if description and display_name and display_name != tool_name:
                instruction = f"{display_name}: {description} (server: {server_label})"
            elif description:
                instruction = f"{description} (server: {server_label})"
            else:
                instruction = f"Call remote MCP tool '{display_name}' on server '{server_label}'."

            cmd_syntax = {
                "cmd": cmd_name,
                "instruction": instruction,
                "params": params,
                "enabled": True,
            }
            data['cmd'].append(cmd_syntax)

            # Index for execution
            self.tools_index[cmd_name] = {
                "server_idx": server_idx,
                "server": server_cfg,
                "server_tag": server_tag,
                "transport": transport,
                "tool_name": tool_name,
                "schema": input_schema,
                "description": description,
                "display_name": display_name,
            }

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        from .worker import Worker

        my_commands = [item for item in cmds if item.get("cmd") in self.tools_index]
        if len(my_commands) == 0:
            return

        # set state: busy
        self.cmd_prepare(ctx, my_commands)

        try:
            worker = Worker()
            worker.from_defaults(self)
            worker.plugin = self
            worker.cmds = my_commands
            worker.ctx = ctx
            worker.tools_index = self.tools_index

            if not self.is_async(ctx):
                worker.run()
                return
            worker.run_async()

        except Exception as e:
            self.error(e)

    # ---------------------------
    # Discovery + caching
    # ---------------------------

    def _discover_tools_sync(self, active_servers: List[Tuple[int, dict]]) -> List[Tuple[int, str, str, Any, dict]]:
        """Run async discovery in a dedicated loop and return collected tools."""
        return asyncio.run(self._discover_tools_async(active_servers))

    async def _discover_tools_async(
        self,
        active_servers: List[Tuple[int, dict]],
        per_server_timeout: float = 8.0
    ) -> List[Tuple[int, str, str, Any, dict]]:
        """
        Discover tools for each active server (with cache).
        Returns tuples: (server_idx, server_tag, transport, tool, server_cfg)
        """
        results: List[Tuple[int, str, str, Any, dict]] = []

        # Lazy import
        try:
            from mcp import ClientSession  # type: ignore
            from mcp.client.stdio import stdio_client  # type: ignore
            from mcp.client.streamable_http import streamablehttp_client  # type: ignore
            from mcp.client.sse import sse_client  # type: ignore
            from mcp import StdioServerParameters  # type: ignore
        except Exception as e:
            self.error('MCP SDK not installed. Install with: pip install "mcp[cli]"')
            self.log(f"MCP import error: {e}")
            return results

        cache_enabled = bool(self.get_option_value("tools_cache_enabled"))
        try:
            ttl = int(self.get_option_value("tools_cache_ttl") or 300)
        except Exception:
            ttl = 300

        for server_idx, server in active_servers:
            address = (server.get("server_address") or "").strip()
            if not address:
                continue

            transport = self._detect_transport(address)
            server_tag = self._make_server_tag(server, server_idx)
            server_key = self._server_key(server)
            headers = self._build_headers(server)

            allowed = self._parse_csv(server.get("allowed_commands"))
            disabled = self._parse_csv(server.get("disabled_commands"))

            # Cache
            cached_tools = None
            if cache_enabled:
                cached = self._tools_cache.get(server_key)
                if cached and cached.get("transport") == transport:
                    if (time.time() - float(cached.get("ts", 0))) <= ttl:
                        cached_tools = cached.get("tools", None)

            async def list_tools_for_session(session: ClientSession) -> List[Any]:
                tools_resp = await session.list_tools()
                return list(tools_resp.tools)

            try:
                if cached_tools is None:
                    async def _run_discovery():
                        if transport == "stdio":
                            cmd, args = self._parse_stdio_command(address)
                            params = StdioServerParameters(command=cmd, args=args)
                            async with stdio_client(params) as (read, write):
                                async with ClientSession(read, write) as session:
                                    await session.initialize()
                                    return await list_tools_for_session(session)

                        elif transport == "http":
                            # Streamable HTTP – pass Authorization if set
                            async with streamablehttp_client(address, headers=headers or None) as (read, write, _):
                                async with ClientSession(read, write) as session:
                                    await session.initialize()
                                    return await list_tools_for_session(session)

                        elif transport == "sse":
                            # SSE – pass Authorization if set
                            async with sse_client(address, headers=headers or None) as (read, write):
                                async with ClientSession(read, write) as session:
                                    await session.initialize()
                                    return await list_tools_for_session(session)

                        else:
                            raise RuntimeError(f"Unsupported MCP transport for server '{server_tag}': {transport}")

                    tools = await asyncio.wait_for(_run_discovery(), timeout=per_server_timeout)

                    if cache_enabled:
                        self._tools_cache[server_key] = {
                            "ts": time.time(),
                            "transport": transport,
                            "tools": tools,
                        }
                else:
                    tools = cached_tools

                for tool in tools:
                    tname = getattr(tool, "name", None) or tool.get("name")
                    if disabled and tname in disabled:
                        continue
                    if allowed and tname not in allowed:
                        continue
                    results.append((server_idx, server_tag, transport, tool, server))

            except asyncio.TimeoutError:
                self.error(f"MCP: timeout during discovery on server '{server_tag}'")
            except Exception as e:
                self.log(f"MCP discovery error on '{server_tag}': {e}")
                self.error(f"MCP: discovery error on '{server_tag}': {e}")

        return results

    # --------------
    # Schema helpers
    # --------------

    def extract_params(self, text: str) -> list:
        """Extract params to list."""
        params = []
        if text is None or text == "":
            return params
        params_list = text.split(",")
        for param in params_list:
            param = param.strip()
            if param == "":
                continue
            params.append({
                "name": param,
                "type": "str",
                "description": param,
            })
        return params

    def extract_params_from_schema(self, schema: Optional[dict]) -> List[dict]:
        """Convert MCP tool inputSchema (JSON Schema) to {name, type, description} list."""
        params: List[dict] = []
        if not schema or not isinstance(schema, dict):
            return params

        properties = schema.get("properties", {})
        required = set(schema.get("required", []) or [])

        for name, prop in properties.items():
            jtype = prop.get("type", "string")
            desc = prop.get("description", "")
            ptype = self._map_json_type_to_param_type(jtype)
            if name in required and desc:
                desc = f"{desc} [required]"
            elif name in required:
                desc = "[required]"
            params.append({
                "name": name,
                "type": ptype,
                "description": desc or name,
            })

        return params

    # ---------------------------
    # Low-level utilities
    # ---------------------------

    def _map_json_type_to_param_type(self, jtype: str) -> str:
        """Map JSON Schema types to simple plugin param types."""
        t = (jtype or "string").lower()
        if t in ("string",):
            return "str"
        if t in ("integer", "number"):
            return "float" if t == "number" else "int"
        if t in ("boolean",):
            return "bool"
        if t in ("array", "object"):
            return "str"
        return "str"

    def _parse_csv(self, text: Optional[str]) -> Optional[set]:
        """Parse comma-separated string into a set of stripped items or None if empty."""
        if not text:
            return None
        items = [x.strip() for x in text.split(",")]
        items = [x for x in items if x]
        return set(items) if items else None

    def _detect_transport(self, address: str) -> str:
        """
        Detect transport from address:
        - 'stdio: ...' -> stdio
        - 'http(s)://.../mcp' or general http(s) -> http (Streamable HTTP)
        - 'sse://' or 'sse+http(s)://' or path containing '/sse' -> sse
        """
        if address.lower().startswith("stdio:"):
            return "stdio"
        lower = address.lower()
        if lower.startswith(("sse://", "sse+http://", "sse+https://")):
            return "sse"
        if lower.startswith(("http://", "https://")):
            try:
                parsed = urlparse(address)
                path = (parsed.path or "").lower()
            except Exception:
                path = ""
            if "/sse" in path or path.endswith("/sse"):
                return "sse"
            return "http"
        return "stdio"

    def _parse_stdio_command(self, address: str) -> Tuple[str, List[str]]:
        """Parse 'stdio: <command line>' into (command, args)."""
        cmdline = address[len("stdio:"):].strip()
        tokens = shlex.split(cmdline)
        if not tokens:
            raise ValueError("Invalid stdio address: empty command")
        return tokens[0], tokens[1:]

    def _make_server_tag(self, server: dict, idx: int) -> str:
        """
        Create a short tag for the server (for display only).
        Prefer explicit 'label'; fallback to host/path-derived value.
        """
        label = (server.get("label") or "").strip()
        if label:
            return label
        address = (server.get("server_address") or "").strip()
        if address.startswith("stdio:"):
            cmdline = address[len("stdio:"):].strip()
            exe = shlex.split(cmdline)[0] if cmdline else f"stdio_{idx}"
            return exe
        try:
            parsed = urlparse(address)
            host = (parsed.netloc or f"server_{idx}")
            tail = (parsed.path.rstrip("/").split("/")[-1] or "mcp")
            return f"{host}_{tail}"
        except Exception:
            return f"server_{idx}"

    def _build_headers(self, server: dict) -> Optional[dict]:
        """
        Build optional headers for HTTP/SSE transports.
        Currently supports Authorization only.
        """
        auth = (server.get("authorization") or "").strip()
        headers = {}
        if auth:
            # If user passed only token, you may expect 'Bearer <token>'
            headers["Authorization"] = auth
        return headers or None

    def _slugify(self, text: str) -> str:
        """
        Sanitize text to allowed chars for tool names: [a-zA-Z0-9_-]
        Collapse multiple underscores and strip from ends.
        """
        if not text:
            return "srv"
        s = re.sub(r"[^a-zA-Z0-9_-]+", "_", text)
        s = re.sub(r"_+", "_", s).strip("_")
        return s or "srv"

    def _truncate_with_hash(self, base: str, max_len: int) -> str:
        """
        Truncate a string to max_len with a short hash suffix to preserve uniqueness.
        """
        if len(base) <= max_len:
            return base
        h = hashlib.sha1(base.encode("utf-8")).hexdigest()[:6]
        keep = max_len - 7  # 1 for '-' + 6 for hash
        keep = max(1, keep)
        return f"{base[:keep]}-{h}"

    def _compose_cmd_name(self, server_slug: str, tool_name: str, used: set) -> str:
        """
        Compose final command name:
        - No global prefixes
        - Format: <server_slug>__<tool_slug>
        - Allowed charset: [a-zA-Z0-9_-]
        - Max length: 64 (OpenAI requirement)
        - Ensure uniqueness within one CMD_SYNTAX build
        """
        tool_slug = self._slugify(tool_name)

        # Initial compose and length guard
        base = f"{server_slug}__{tool_slug}"
        name = self._truncate_with_hash(base, 64)

        # Ensure uniqueness; add numeric suffix if needed (within 64 limit)
        if name not in used:
            return name

        i = 2
        while True:
            suffix = f"-{i}"
            max_len = 64 - len(suffix)
            candidate = self._truncate_with_hash(base, max_len) + suffix
            if candidate not in used:
                return candidate
            i += 1

    def _server_key(self, server: dict) -> str:
        """Deterministic key for a server config entry."""
        addr = (server.get("server_address") or "").strip()
        if addr.lower().startswith("http"):
            try:
                parsed = urlparse(addr)
                return f"http::{parsed.netloc}{parsed.path}"
            except Exception:
                return f"http::{addr}"
        if addr.lower().startswith(("sse://", "sse+http://", "sse+https://")):
            return f"sse::{addr}"
        if addr.startswith("stdio:"):
            return f"stdio::{addr[len('stdio:'):].strip()}"
        return addr

    def _config_signature(self, active_servers: List[Tuple[int, dict]]) -> str:
        """Signature of current config to invalidate cache when config changes."""
        norm: List[str] = []
        for idx, srv in active_servers:
            addr = (srv.get("server_address") or "").strip()
            label = (srv.get("label") or "").strip()
            auth = (srv.get("authorization") or "").strip()
            a = ",".join(sorted(list(self._parse_csv(srv.get("allowed_commands")) or [])))
            d = ",".join(sorted(list(self._parse_csv(srv.get("disabled_commands")) or [])))
            norm.append(f"{idx}|{label}|{addr}|AUTH:{bool(auth)}|A:{a}|D:{d}")
        blob = "|#|".join(norm)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()