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
import json
import shlex
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Tuple, Optional
from urllib.parse import urlparse

from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass  # add custom signals here


class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = BaseSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds: Optional[List[dict]] = None
        self.ctx = None
        self.tools_index: Dict[str, Dict[str, Any]] = {}

    @Slot()
    def run(self):
        """
        Worker entry point executed in a background thread.
        Starts an asyncio loop to talk to MCP servers.
        """
        try:
            responses = asyncio.run(self._run_async())
            if responses:
                self.reply_more(responses)
        except Exception as e:
            self.error(e)
        finally:
            self.cleanup()

    async def _run_async(self) -> List[dict]:
        """
        Group commands per server, open a session per server, then call tools.
        """
        responses: List[dict] = []

        try:
            from mcp import ClientSession, types  # type: ignore
            from mcp.client.stdio import stdio_client  # type: ignore
            from mcp.client.streamable_http import streamablehttp_client  # type: ignore
            from mcp.client.sse import sse_client  # type: ignore
            from mcp import StdioServerParameters  # type: ignore
        except Exception as e:
            self.status('MCP SDK not installed. Install with: pip install "mcp[cli]"')
            self.log(f"MCP import error in worker: {e}")
            for item in (self.cmds or []):
                responses.append(self.make_response(item, f"MCP SDK not installed: {e}"))
            return responses

        # Group by server
        grouped: Dict[str, List[dict]] = {}
        for item in self.cmds or []:
            meta = self.tools_index.get(item["cmd"])
            if not meta:
                continue
            server_key = self._server_key(meta["server"])
            grouped.setdefault(server_key, []).append(item)

        # Execute per server
        for server_key, items in grouped.items():
            meta0 = self.tools_index.get(items[0]["cmd"])
            if not meta0:
                continue
            server_cfg = meta0["server"]
            address = (server_cfg.get("server_address") or "").strip()
            transport = meta0["transport"]
            headers = self._build_headers(server_cfg)

            try:
                async with self._open_session(address, transport, headers=headers) as session:
                    for item in items:
                        if self.is_stopped():
                            break

                        meta = self.tools_index.get(item["cmd"])
                        if not meta:
                            continue

                        tool_name = meta["tool_name"]
                        schema = meta.get("schema")
                        arguments = self._coerce_arguments(item.get("params", {}), schema)

                        try:
                            result = await session.call_tool(tool_name, arguments=arguments)
                            text = self._extract_text_result(result)
                            responses.append(self.make_response(item, text))
                        except Exception as e:
                            responses.append(self.make_response(item, self.throw_error(e)))

            except Exception as e:
                msg = f"MCP server error ({address}): {e}"
                self.log(msg)
                self.status(msg)
                for item in items:
                    responses.append(self.make_response(item, self.throw_error(e)))

        return responses

    # ---------------------------
    # Session / transport helpers
    # ---------------------------

    @asynccontextmanager
    async def _open_session(self, address: str, transport: str, headers: Optional[dict] = None):
        """
        Open and initialize MCP session for given server address and transport.
        Yields a ready-to-use ClientSession.
        """
        from mcp import ClientSession  # type: ignore

        if transport == "stdio":
            from mcp.client.stdio import stdio_client  # type: ignore
            from mcp import StdioServerParameters  # type: ignore
            cmd, args = self._parse_stdio_command(address)
            params = StdioServerParameters(command=cmd, args=args)
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

        elif transport == "http":
            from mcp.client.streamable_http import streamablehttp_client  # type: ignore
            async with streamablehttp_client(address, headers=headers or None) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

        elif transport == "sse":
            from mcp.client.sse import sse_client  # type: ignore
            async with sse_client(address, headers=headers or None) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

        else:
            raise RuntimeError(f"Unsupported transport: {transport}")

    def _parse_stdio_command(self, address: str) -> Tuple[str, List[str]]:
        """Parse 'stdio: <command line>' into (command, args)."""
        cmdline = address[len("stdio:"):].strip()
        tokens = shlex.split(cmdline)
        if not tokens:
            raise ValueError("Invalid stdio address: empty command")
        return tokens[0], tokens[1:]

    # ---------------------------
    # Result & argument handling
    # ---------------------------

    def _coerce_arguments(self, params: Dict[str, Any], schema: Optional[dict]) -> Dict[str, Any]:
        """Coerce incoming params into types expected by the tool schema."""
        if not schema or not isinstance(schema, dict):
            return params or {}

        props = schema.get("properties", {}) or {}
        coerced: Dict[str, Any] = {}

        for name, value in (params or {}).items():
            target = props.get(name, {})
            jtype = target.get("type", "string")

            try:
                if jtype == "integer":
                    coerced[name] = int(value)
                elif jtype == "number":
                    coerced[name] = float(value)
                elif jtype == "boolean":
                    if isinstance(value, bool):
                        coerced[name] = value
                    elif isinstance(value, str):
                        coerced[name] = value.strip().lower() in ("1", "true", "yes", "y", "on")
                    else:
                        coerced[name] = bool(value)
                elif jtype in ("array", "object"):
                    if isinstance(value, (dict, list)):
                        coerced[name] = value
                    elif isinstance(value, str):
                        try:
                            coerced[name] = json.loads(value)
                        except Exception:
                            coerced[name] = value
                    else:
                        coerced[name] = value
                else:
                    coerced[name] = value
            except Exception:
                coerced[name] = value

        return coerced

    def _extract_text_result(self, result: Any) -> str:
        """
        Convert MCP tool result into a readable string.
        Prefer structuredContent; fallback to text content blocks.
        """
        try:
            if getattr(result, "structuredContent", None) is not None:
                return json.dumps(result.structuredContent, ensure_ascii=False, indent=2)

            content_list = getattr(result, "content", None)
            if not content_list:
                return "No result (empty content)"
            from mcp import types  # type: ignore
            texts: List[str] = []
            for block in content_list:
                if isinstance(block, types.TextContent):
                    texts.append(block.text)
                else:
                    btype = getattr(block, "type", "content")
                    texts.append(f"[{btype}]")
            return "\n".join(texts) if texts else "No result (no text content)"
        except Exception as e:
            return f"Failed to parse MCP result: {e}"

    # ---------------------------
    # Misc helpers
    # ---------------------------

    def _server_key(self, server: dict) -> str:
        """Create a deterministic key for a server config entry."""
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

    def _build_headers(self, server: dict) -> Optional[dict]:
        """Build optional headers for HTTP/SSE transports (Authorization only)."""
        auth = (server.get("authorization") or "").strip()
        headers = {}
        if auth:
            headers["Authorization"] = auth
        return headers or None