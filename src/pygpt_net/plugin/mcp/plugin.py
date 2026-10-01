#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.21 16:30:00                  #
# ================================================== #

import asyncio
import hashlib
import re
import shlex
import tempfile
import time
from typing import Dict, List, Tuple, Any, Optional
from urllib.parse import urlparse

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem

from .config import Config
from .runtime import build_env, build_headers, float_option, parse_stdio, tool_allowed


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "mcp"
        self.is_common_plugin = True
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
        self._last_config_signature: Dict[str, str] = {}

        # Model-defined MCP connections are runtime-only and scoped to a chat.
        # They are deliberately not written into the persistent `servers` option.
        self._self_servers: Dict[str, List[dict]] = {}

        # Stdio connectors without an explicit cwd must never inherit the app's
        # process cwd (for source runs this can be the repository root). Keep a
        # per-server temporary working directory for the lifetime of the plugin.
        self._stdio_tempdirs: Dict[str, tempfile.TemporaryDirectory] = {}

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
            self.cmd_syntax(data, ctx)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data['commands'],
            )

    def cmd_syntax(self, data: dict, ctx: Optional[CtxItem] = None):
        """
        Event: CMD_SYNTAX.

        Expose the model self-connect tool only when at least one self-MCP
        transport is explicitly allowed. Model-defined servers are runtime-only
        and scoped to the current conversation. Their discovered tools share the
        same cache/index path as configured MCP servers.
        """
        allow_http = bool(self.get_option_value("allow_self_mcp"))
        allow_stdio = bool(self.get_option_value("allow_self_mcp_stdio"))
        if allow_http or allow_stdio:
            data['cmd'].append(self._get_self_connect_cmd(allow_http, allow_stdio))

        servers: List[dict] = self.get_option_value("servers") or []
        active_servers = [(i, s) for i, s in enumerate(servers) if s.get("active", False)]

        scope = self._self_scope(ctx)
        self_servers = self._allowed_self_servers(scope, allow_http, allow_stdio)
        base_idx = len(servers) + 1000
        active_servers.extend((base_idx + i, s) for i, s in enumerate(self_servers))
        self.tools_index.clear()

        if len(active_servers) == 0:
            return

        self._last_config_signature[scope] = self._config_signature(active_servers)

        try:
            discovered = self._discover_tools_sync(active_servers)
        except Exception as e:
            self.error(e)
            self.error(f"MCP: discovery failed: {e}")
            return

        used_names = {"mcp_connect"}

        for (server_idx, server_tag, transport, tool, server_cfg) in discovered:
            tool_name = getattr(tool, "name", None) or tool.get("name")
            description = getattr(tool, "description", None) or tool.get("description")
            input_schema = getattr(tool, "inputSchema", None) or tool.get("inputSchema")

            display_name = tool_name
            try:
                from mcp.shared.metadata_utils import get_display_name  # type: ignore
                display_name = get_display_name(tool) or tool_name
            except Exception:
                pass

            server_label = (server_cfg.get("label") or server_tag or f"srv{server_idx}").strip()
            server_slug = self._slugify(server_label)
            cmd_name = self._compose_cmd_name(server_slug, tool_name, used_names)
            used_names.add(cmd_name)
            params = self.extract_params_from_schema(input_schema)

            if description and display_name and display_name != tool_name:
                instruction = f"{display_name}: {description} (server: {server_label})"
            elif description:
                instruction = f"{description} (server: {server_label})"
            else:
                instruction = f"Call remote MCP tool '{display_name}' on server '{server_label}'."

            data['cmd'].append({
                "cmd": cmd_name,
                "instruction": instruction,
                "params": params,
                "enabled": True,
            })
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
        """Event: CMD_EXECUTE."""
        from .worker import Worker

        connect_commands = [item for item in cmds if item.get("cmd") == "mcp_connect"]
        remote_commands = [item for item in cmds if item.get("cmd") in self.tools_index]
        if not connect_commands and not remote_commands:
            return

        self.cmd_prepare(ctx, connect_commands + remote_commands)

        # The connect operation must complete before the next model request so
        # the next CMD_SYNTAX build can immediately expose discovered tools.
        for item in connect_commands:
            try:
                result = self._connect_self_server(ctx, item.get("params") or {})
            except Exception as e:
                result = f"MCP self-connect failed: {e}"
            self.reply({
                "request": {"cmd": "mcp_connect"},
                "result": result,
            }, ctx)

        if not remote_commands:
            return

        try:
            worker = Worker()
            worker.from_defaults(self)
            worker.plugin = self
            worker.cmds = remote_commands
            worker.ctx = ctx
            worker.tools_index = self.tools_index

            if not self.is_async(ctx):
                worker.run()
                return
            worker.run_async()
        except Exception as e:
            self.error(e)

    def _get_self_connect_cmd(self, allow_http: bool, allow_stdio: bool) -> dict:
        transports = []
        if allow_http:
            transports.extend(["http", "sse"])
        if allow_stdio:
            transports.append("stdio")
        transport_text = ", ".join(transports) or "none"
        return {
            "cmd": "mcp_connect",
            "instruction": (
                "Define a runtime MCP server connection, discover its tools, and make them available "
                "on the next tool-selection step. The connection is scoped to the current chat. "
                "Allowed transports: {transport_text}. "
                "For HTTP/SSE use an http:// or https:// URL. For stdio use 'stdio: <command ...>' "
                "or set transport=stdio. JSON fields accept JSON object strings."
            ),
            "params": [
                {"name": "server_address", "type": "str", "description": "MCP URL or stdio command. [required]"},
                {"name": "label", "type": "str", "description": "Short server label used in generated tool names."},
                {"name": "transport", "type": "str", "description": "auto, http, sse, or stdio. Default: auto."},
                {"name": "authorization", "type": "str", "description": "Authorization header value for HTTP/SSE."},
                {"name": "headers", "type": "str", "description": "JSON object with HTTP/SSE headers."},
                {"name": "env_http_headers", "type": "str", "description": "JSON object mapping HTTP header names to environment variable names."},
                {"name": "bearer_token_env_var", "type": "str", "description": "Environment variable containing a bearer token."},
                {"name": "env", "type": "str", "description": "JSON object with environment variables for stdio."},
                {"name": "cwd", "type": "str", "description": "Working directory for stdio. Empty uses an isolated temporary directory."},
            ],
            "enabled": True,
        }

    def _self_scope(self, ctx: Optional[CtxItem]) -> str:
        meta_id = getattr(ctx, "meta_id", None) if ctx is not None else None
        if meta_id not in (None, ""):
            return f"meta:{meta_id}"
        meta = getattr(ctx, "meta", None) if ctx is not None else None
        meta_id = getattr(meta, "id", None) if meta is not None else None
        if meta_id not in (None, ""):
            return f"meta:{meta_id}"
        return "current"

    def _allowed_self_servers(self, scope: str, allow_http: bool, allow_stdio: bool) -> List[dict]:
        allowed = []
        for server in self._self_servers.get(scope, []):
            address = str(server.get("server_address") or "").strip()
            transport = self._detect_transport(address, server)
            if transport == "stdio" and allow_stdio:
                allowed.append(server)
            elif transport in ("http", "sse") and allow_http:
                allowed.append(server)
        return allowed

    def _connect_self_server(self, ctx: Optional[CtxItem], params: dict) -> str:
        address = str(params.get("server_address") or "").strip()
        if not address:
            raise ValueError("server_address is required")

        explicit_transport = str(params.get("transport") or "auto").strip().lower()
        if explicit_transport not in ("", "auto", "http", "sse", "stdio"):
            raise ValueError("transport must be one of: auto, http, sse, stdio")

        server = {
            "active": True,
            "label": str(params.get("label") or "").strip(),
            "server_address": address,
            "authorization": str(params.get("authorization") or ""),
            "allowed_commands": str(params.get("allowed_commands") or ""),
            "disabled_commands": str(params.get("disabled_commands") or ""),
            "transport": explicit_transport or "auto",
            "env": params.get("env") or "",
            "headers": params.get("headers") or "",
            "env_http_headers": params.get("env_http_headers") or "",
            "bearer_token_env_var": str(params.get("bearer_token_env_var") or ""),
            "cwd": str(params.get("cwd") or ""),
            "startup_timeout_sec": str(params.get("startup_timeout_sec") or ""),
            "tool_timeout_sec": str(params.get("tool_timeout_sec") or ""),
            "source": "model-runtime",
            "extra": "",
        }
        transport = self._detect_transport(address, server)

        if transport in ("http", "sse"):
            if not bool(self.get_option_value("allow_self_mcp")):
                raise PermissionError("model-defined MCP HTTP/SSE connections are disabled")
            lower = address.lower()
            if not lower.startswith(("http://", "https://", "sse://", "sse+http://", "sse+https://")):
                raise ValueError("HTTP/SSE self-MCP requires an http(s) or SSE URL")
        elif transport == "stdio":
            if not bool(self.get_option_value("allow_self_mcp_stdio")):
                raise PermissionError("model-defined MCP stdio connections are disabled")
            if not address.lower().startswith("stdio:"):
                server["server_address"] = f"stdio: {address}"
                address = server["server_address"]
        else:
            raise ValueError(f"unsupported MCP transport: {transport}")

        if not server["label"]:
            server["label"] = self._make_server_tag(server, 0)

        scope = self._self_scope(ctx)
        runtime_servers = self._self_servers.setdefault(scope, [])
        key = self._server_key(server)
        replaced = False
        for i, existing in enumerate(runtime_servers):
            if self._server_key(existing) == key:
                runtime_servers[i] = server
                replaced = True
                break
        if not replaced:
            runtime_servers.append(server)

        # Force a fresh discovery for this explicit connect call. The result is
        # then stored in the normal per-server cache (when cache is enabled),
        # so the immediately following syntax rebuild does not reconnect.
        self._tools_cache.pop(key, None)
        discovered = self._discover_tools_sync([(100000, server)])
        tool_names = []
        for _, _, _, tool, _ in discovered:
            name = getattr(tool, "name", None)
            if name is None and isinstance(tool, dict):
                name = tool.get("name")
            if name:
                tool_names.append(str(name))

        self._last_config_signature.pop(scope, None)
        if not tool_names:
            if replaced:
                runtime_servers[i] = existing
            else:
                runtime_servers[:] = [item for item in runtime_servers if item is not server]
            self._tools_cache.pop(key, None)
            raise RuntimeError("connection failed or no MCP tools were discovered")

        action = "updated" if replaced else "connected"
        return (
            f"MCP server {action}: {server['label']} ({transport}). "
            f"Discovered {len(tool_names)} tool(s): {', '.join(tool_names)}. "
            "They will be exposed on the next tool-selection step."
        )

    # ---------------------------
    # Discovery + caching
    # ---------------------------

    def _discover_tools_sync(self, active_servers: List[Tuple[int, dict]]) -> List[Tuple[int, str, str, Any, dict]]:
        """Run async discovery in a dedicated loop and return collected tools.

        If an event loop is already running (e.g. from agents v2), we create
        a new loop in a separate thread to avoid ``RuntimeError: This event
        loop is already running``.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            return asyncio.run(self._discover_tools_async(active_servers))

        import threading

        result = None
        exc = None

        def _target():
            nonlocal result, exc
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result = new_loop.run_until_complete(
                        self._discover_tools_async(active_servers)
                    )
                finally:
                    new_loop.close()
            except Exception as e:
                exc = e

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join(timeout=30)

        if exc is not None:
            raise exc
        return result if result is not None else []

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

        async def list_tools_for_session(session: ClientSession) -> List[Any]:
            tools_resp = await session.list_tools()
            return list(tools_resp.tools)

        async def _discover_single_server(
            server_idx: int, server: dict, address: str, transport: str, headers: Optional[dict]
        ) -> List[Any]:
            """Discover tools for a single server (called concurrently)."""
            async def _run_discovery():
                if transport == "stdio":
                    cmd, args = self._parse_stdio_command(address)
                    kwargs = {"command": cmd, "args": args}
                    env = build_env(server)
                    if env is not None:
                        kwargs["env"] = env
                    kwargs["cwd"] = self.get_stdio_cwd(server)
                    params = StdioServerParameters(**kwargs)
                    async with stdio_client(params) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            return await list_tools_for_session(session)
                elif transport == "http":
                    async with streamablehttp_client(address, headers=headers or None) as (read, write, _):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            return await list_tools_for_session(session)
                elif transport == "sse":
                    async with sse_client(address, headers=headers or None) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            return await list_tools_for_session(session)
                else:
                    raise RuntimeError(f"Unsupported MCP transport: {transport}")

            timeout = float_option(server, "startup_timeout_sec", per_server_timeout)
            return await asyncio.wait_for(_run_discovery(), timeout=timeout)

        # Cache / run discovery per server concurrently to bound total time
        tasks = []
        for server_idx, server in active_servers:
            address = (server.get("server_address") or "").strip()
            if not address:
                continue

            transport = self._detect_transport(address, server)
            server_tag = self._make_server_tag(server, server_idx)
            server_key = self._server_key(server)
            headers = self._build_headers(server)

            allowed = self._parse_csv(server.get("allowed_commands"))
            disabled = self._parse_csv(server.get("disabled_commands"))

            cached_tools = None
            cache_signature = self._server_cache_signature(server, transport)
            if cache_enabled:
                cached = self._tools_cache.get(server_key)
                if (
                    cached
                    and cached.get("transport") == transport
                    and cached.get("signature") == cache_signature
                ):
                    if (time.time() - float(cached.get("ts", 0))) <= ttl:
                        cached_tools = cached.get("tools", None)

            async def _with_cache(server_idx=server_idx, server=server, address=address,
                                  transport=transport, server_tag=server_tag, server_key=server_key,
                                  headers=headers, allowed=allowed, disabled=disabled,
                                  cached_tools=cached_tools, cache_signature=cache_signature):
                try:
                    tools = cached_tools
                    if tools is None:
                        tools = await _discover_single_server(
                            server_idx, server, address, transport, headers
                        )
                        if cache_enabled:
                            self._tools_cache[server_key] = {
                                "ts": time.time(),
                                "transport": transport,
                                "signature": cache_signature,
                                "tools": tools,
                            }
                    return (server_idx, server_tag, transport, allowed, disabled, tools, server)
                except asyncio.TimeoutError:
                    self.error(f"MCP: timeout during discovery on server '{server_tag}'")
                    return None
                except Exception as e:
                    self.log(f"MCP discovery error on '{server_tag}': {e}")
                    self.error(f"MCP: discovery error on '{server_tag}': {e}")
                    return None

            tasks.append(_with_cache())

        if not tasks:
            return results

        done = await asyncio.gather(*tasks, return_exceptions=True)
        for outcome in done:
            if isinstance(outcome, Exception):
                self.log(f"MCP discovery error: {outcome}")
                continue
            if outcome is None:
                continue
            server_idx, server_tag, transport, allowed, disabled, tools, server = outcome
            for tool in tools:
                tname = getattr(tool, "name", None) or tool.get("name")
                if not tool_allowed(tname, allowed, disabled):
                    continue
                results.append((server_idx, server_tag, transport, tool, server))

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

    def _detect_transport(self, address: str, server: Optional[dict] = None) -> str:
        """
        Detect transport from explicit connector metadata or address:
        - 'stdio: ...' -> stdio
        - 'http(s)://.../mcp' or general http(s) -> http (Streamable HTTP)
        - 'sse://' or 'sse+http(s)://' or path containing '/sse' -> sse
        """
        explicit = str((server or {}).get("transport") or "").strip().lower()
        if explicit in ("stdio", "http", "sse"):
            return explicit
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
        return parse_stdio(address)

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
        """Build connector HTTP/SSE headers, including env-backed values."""
        return build_headers(server)

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

    def get_stdio_cwd(self, server: dict) -> str:
        """Return an explicit or isolated working directory for an stdio server.

        Leaving cwd unset makes subprocesses inherit PyGPT's process cwd. Tools
        such as ``uv`` then discover the PyGPT repository as their project and
        may create files such as ``uv.lock`` there. An explicitly configured cwd
        is preserved; otherwise use an isolated system temporary directory.
        """
        cwd = str(server.get("cwd") or "").strip()
        if cwd:
            return cwd

        label = str(server.get("label") or "server").strip() or "server"
        key = f"{label}|{self._server_key(server)}"
        tempdir = self._stdio_tempdirs.get(key)
        if tempdir is None:
            slug = self._slugify(label)[:24] or "server"
            tempdir = tempfile.TemporaryDirectory(prefix=f"pygpt-mcp-{slug}-")
            self._stdio_tempdirs[key] = tempdir
        return tempdir.name

    def destroy(self):
        """Release temporary stdio working directories."""
        for tempdir in list(self._stdio_tempdirs.values()):
            try:
                tempdir.cleanup()
            except Exception:
                pass
        self._stdio_tempdirs.clear()
        self._self_servers.clear()
        self._last_config_signature.clear()

    def _server_cache_signature(self, server: dict, transport: str) -> str:
        """Signature of all connection/discovery fields that affect a server's tool list."""
        fields = [
            str(server.get("label") or ""),
            str(server.get("server_address") or ""),
            str(transport or ""),
            str(server.get("authorization") or ""),
            str(server.get("headers") or ""),
            str(server.get("env_http_headers") or ""),
            str(server.get("bearer_token_env_var") or ""),
            str(server.get("env") or ""),
            str(server.get("cwd") or ""),
            str(server.get("startup_timeout_sec") or ""),
            str(server.get("allowed_commands") or ""),
            str(server.get("disabled_commands") or ""),
        ]
        return hashlib.sha256("|".join(fields).encode("utf-8")).hexdigest()

    def _config_signature(self, active_servers: List[Tuple[int, dict]]) -> str:
        """Signature of current config to invalidate cache when config changes."""
        norm: List[str] = []
        for idx, srv in active_servers:
            allowed = ",".join(sorted(list(self._parse_csv(srv.get("allowed_commands")) or [])))
            disabled = ",".join(sorted(list(self._parse_csv(srv.get("disabled_commands")) or [])))
            fields = [
                str(idx), str(srv.get("label") or ""), str(srv.get("server_address") or ""),
                str(srv.get("transport") or ""), str(srv.get("authorization") or ""),
                str(srv.get("headers") or ""), str(srv.get("env_http_headers") or ""),
                str(srv.get("bearer_token_env_var") or ""), str(srv.get("env") or ""),
                str(srv.get("cwd") or ""), str(srv.get("startup_timeout_sec") or ""),
                allowed, disabled,
            ]
            norm.append("|".join(fields))
        return hashlib.sha256("|#|".join(norm).encode("utf-8")).hexdigest()

