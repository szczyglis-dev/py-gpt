#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.06 00:00:00                  #
# ================================================== #

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from llama_index.core.tools import BaseTool, FunctionTool, QueryEngineTool, ToolMetadata

from pygpt_net.core.types import TOOL_QUERY_ENGINE_DESCRIPTION
from pygpt_net.core.command.tool_schema import JsonSchemaToolMetadata


class SchemaToolMetadata(JsonSchemaToolMetadata):
    """Agents v2 plugin metadata using PyGPT JSON schemas verbatim."""

class WorkerToolFactory:
    """Build tools bound to one actor/runtime instead of legacy global agent state."""

    RESERVED = {
        "agent_create", "agent_update", "agent_run", "agent_status", "agent_list",
        "agent_wait", "agent_stop", "agent_remove", "workflow_status", "workflow_finish",
        "report_status", "shared_context", "query_index",
    }

    def __init__(self, runtime):
        self.runtime = runtime
        self.window = runtime.window

    def build(self, worker) -> List[BaseTool]:
        tools: List[BaseTool] = []
        if self.runtime.allow_local_tools and self.window.core.command.is_cmd(inline=False):
            tools.extend(self._plugin_tools(worker))

        async def report_status(status: str) -> str:
            return await self._report_status(worker, status)

        async def shared_context() -> str:
            return self.runtime.shared_context_text or "No shared attachment context is available."

        tools.append(FunctionTool.from_defaults(
            async_fn=report_status,
            name="report_status",
            description=(
                "Report a short current activity/progress status to the Orchestrator and the user's transient status line. "
                "Use this before meaningful or potentially long phases."
            ),
        ))
        tools.append(FunctionTool.from_defaults(
            async_fn=shared_context,
            name="shared_context",
            description=(
                "Return extracted user attachment context plus the current attachment manifest. "
                "Use it instead of guessing about files supplied by the user."
            ),
        ))

        rag = self._rag_tool()
        if rag is not None:
            tools.append(rag)

        return tools

    def build_orchestrator(self, actor) -> List[BaseTool]:
        """Expose normal PyGPT capabilities to the orchestrator; delegation remains optional."""
        tools: List[BaseTool] = []
        if self.runtime.allow_local_tools and self.window.core.command.is_cmd(inline=False):
            tools.extend(self._plugin_tools(actor))
        async def shared_context() -> str:
            return self.runtime.shared_context_text or "No shared attachment context is available."

        tools.append(FunctionTool.from_defaults(
            async_fn=shared_context,
            name="shared_context",
            description="Return extracted/shared user attachment context and the current attachment manifest.",
        ))
        rag = self._rag_tool()
        if rag is not None:
            tools.append(rag)
        return tools

    async def _report_status(self, worker, status: str) -> str:
        text = str(status or "").strip()[:240]
        worker.progress = text
        if text:
            self.runtime.emit_worker_status(worker, text)
        return "Status updated."

    def _plugin_tools(self, worker) -> List[BaseTool]:
        out: List[BaseTool] = []
        for item in self.window.core.command.get_functions(force=True):
            try:
                name = str(item.get("name") or "").strip()
                if not name or name in self.RESERVED:
                    continue
                description = str(item.get("desc") or name)
                schema = json.loads(item.get("params") or "{}")

                def make_async_fn(tool_name: str, tool_schema: dict):
                    async def fn(**kwargs):
                        if self.runtime.is_stopped() or worker.stop_requested:
                            return "Execution cancelled."

                        # Some providers may wrap function arguments once more in
                        # ``params``/``arguments`` even though the advertised JSON
                        # schema is already the parameter object. Normalize that
                        # harmless shape before validating the call.
                        call_args = dict(kwargs or {})
                        for wrapper in ("params", "arguments"):
                            wrapped = call_args.get(wrapper)
                            if (isinstance(wrapped, dict) and len(call_args) == 1):
                                call_args = dict(wrapped)
                                break

                        required = list((tool_schema or {}).get("required") or [])
                        missing = [
                            key for key in required
                            if key not in call_args or call_args.get(key) is None
                        ]
                        if missing:
                            return json.dumps({
                                "error": "Missing required tool parameter(s).",
                                "tool": tool_name,
                                "missing": missing,
                                "required": required,
                                "received": sorted(call_args.keys()),
                            }, ensure_ascii=False)

                        # Every Agents v2 actor must use a private CtxItem.  Keep these
                        # flags explicit before each call because legacy plugins mutate
                        # reply/results while producing their response.
                        tool_ctx = worker.tool_ctx
                        tool_ctx.agent_call = True
                        tool_ctx.async_disabled = False
                        tool_ctx.internal = True
                        tool_ctx.hidden = True
                        tool_ctx.reply = False

                        cmd = {"cmd": tool_name, "params": call_args}
                        self.runtime.emit_runtime_status(
                            "status.agent_v2.tool",
                            worker=worker if getattr(worker, "id", "") != "orchestrator" else None,
                            tool=tool_name,
                        )
                        # Plugin controller/API objects are shared with the rest of PyGPT.
                        # Keep their side effects serialized, while the worker LLM loops remain concurrent.
                        async with self.runtime.local_tool_lock:
                            # Only command dispatch touches the Qt thread. Long-running plugin
                            # work uses the plugin's normal QRunnable path; this coroutine
                            # awaits its reply without blocking the GUI event loop.
                            response = await self.runtime.emitter.execute_plugin(
                                tool_ctx,
                                [cmd],
                                self.runtime.is_stopped,
                            )

                        self.runtime.collect_artifacts(tool_ctx, worker)
                        # `reply` is a legacy chat-loop flag. It is useful while a plugin
                        # builds its response, but must not survive on a reusable actor ctx.
                        tool_ctx.reply = False

                        if isinstance(response, (dict, list)):
                            return json.dumps(response, ensure_ascii=False, indent=2, default=str)
                        return str(response)
                    fn.__name__ = tool_name
                    return fn

                metadata = SchemaToolMetadata(name, description, schema)
                out.append(FunctionTool(async_fn=make_async_fn(name, schema), metadata=metadata))
            except Exception as exc:
                self.window.core.debug.log(exc)
        return out

    def _rag_tool(self) -> Optional[BaseTool]:
        idx = self.runtime.index_id
        core = self.window.core
        if not idx or not core.idx.is_valid(idx):
            return None
        try:
            # Reuse Chat with Files index loading so virtual project RAG and empty-index
            # fallback follow the same lifecycle as the rest of PyGPT.
            index, _llm = core.idx.chat.get_index(idx, self.runtime.model, stream=False)
            if index is None:
                return None
            query_engine = index.as_query_engine(similarity_top_k=3)
            return QueryEngineTool(
                query_engine=query_engine,
                metadata=ToolMetadata(
                    name="query_index",
                    description=TOOL_QUERY_ENGINE_DESCRIPTION + f" Selected index: {idx}",
                ),
            )
        except Exception as exc:
            core.debug.log(exc)
            return None
