#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from llama_index.core.tools import BaseTool, FunctionTool, QueryEngineTool, ToolMetadata

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.types import MODE_AGENT_V2, MODE_CHAT, TOOL_QUERY_ENGINE_DESCRIPTION
from pygpt_net.item.ctx import CtxItem


class SchemaToolMetadata(ToolMetadata):
    """Tool metadata that preserves the JSON schema supplied by PyGPT plugins."""

    def __init__(self, name: str, description: str, schema: dict):
        super().__init__(name=name, description=description)
        self.schema = schema or {"type": "object", "properties": {}}

    def get_parameters_dict(self) -> Dict[str, Any]:
        return {
            k: v for k, v in self.schema.items()
            if k in ("type", "properties", "required", "definitions", "$defs")
        }


class WorkerToolFactory:
    """Build tools bound to one actor/runtime instead of legacy global agent state."""

    RESERVED = {
        "agent_create", "agent_update", "agent_run", "agent_status", "agent_list",
        "agent_wait", "agent_stop", "agent_remove", "workflow_status", "workflow_finish",
        "report_status", "shared_context", "remote_task", "query_index",
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

        if self.runtime.allow_remote_tools and self._remote_available():
            async def remote_task(task: str) -> str:
                return await self._remote_task(worker, task)

            tools.append(FunctionTool.from_defaults(
                async_fn=remote_task,
                name="remote_task",
                description=(
                    "Execute a focused subtask through the selected provider using PyGPT's currently enabled provider-side "
                    "remote tools (web search, hosted code execution, file search, MCP, etc., depending on provider/config). "
                    "The current turn attachments are forwarded and generated artifacts are propagated to the main response."
                ),
            ))
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
        if self.runtime.allow_remote_tools and self._remote_available():
            async def remote_task(task: str) -> str:
                return await self._remote_task(actor, task)

            tools.append(FunctionTool.from_defaults(
                async_fn=remote_task,
                name="remote_task",
                description=(
                    "Execute a focused task through the selected provider with PyGPT's enabled provider-side remote tools. "
                    "Current attachments and produced artifacts are preserved."
                ),
            ))
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

                def make_async_fn(tool_name: str):
                    async def fn(**kwargs):
                        if self.runtime.is_stopped() or worker.stop_requested:
                            return "Execution cancelled."

                        # Every Agents v2 actor must use a private CtxItem.  Keep these
                        # flags explicit before each call because legacy plugins mutate
                        # reply/results while producing their response.
                        tool_ctx = worker.tool_ctx
                        tool_ctx.agent_call = True
                        tool_ctx.async_disabled = True
                        tool_ctx.internal = True
                        tool_ctx.hidden = True
                        tool_ctx.reply = False

                        cmd = {"cmd": tool_name, "params": kwargs}
                        # Provide a fallback progress signal only when the actor has
                        # not already supplied a better, user-language status.
                        if getattr(worker, "id", "") == "orchestrator":
                            if not self.runtime.emitter.status_text:
                                self.runtime.emitter.status(
                                    f"Using tool: {tool_name}",
                                    source="orchestrator",
                                )
                        elif not worker.progress or worker.progress == "Starting task":
                            self.runtime.emit_worker_status(worker, f"Using tool: {tool_name}")

                        # Plugin controller/API objects are shared with the rest of PyGPT.
                        # Keep their side effects serialized, while the worker LLM loops remain concurrent.
                        async with self.runtime.local_tool_lock:
                            # Plugin/controller execution touches Qt UI/state. Proxy it to the
                            # main thread and block only this orchestration runtime until the
                            # command result is available.
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
                out.append(FunctionTool(async_fn=make_async_fn(name), metadata=metadata))
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

    def _remote_available(self) -> bool:
        """Ask the selected provider's own remote-tool builder instead of guessing config keys."""
        model = self.runtime.model
        if model is None:
            return False
        provider = model.get_provider()
        cfg = self.window.core.config
        try:
            if provider == "openai":
                tools = self.window.core.api.openai.remote_tools.append_to_tools(
                    mode=MODE_CHAT,
                    model=model,
                    stream=False,
                    is_expert_call=False,
                    tools=[],
                    preset=self.runtime.preset,
                )
                return bool(tools)
            if provider == "google" and cfg.get("api_native_google", False):
                return bool(self.window.core.api.google.remote_tools.build_remote_tools(model))
            if provider == "anthropic" and cfg.get("api_native_anthropic", False):
                return bool(self.window.core.api.anthropic.remote_tools.build_remote_tools(model))
            if provider == "x_ai" and cfg.get("api_native_xai", False):
                modern = self.window.core.api.xai.remote.build_for_chat(model=model, stream=False) or {}
                if modern.get("tools"):
                    return True
                legacy = self.window.core.api.xai.remote.build_remote_tools(model) or {}
                return bool((legacy.get("sdk") or {}).get("enabled") or legacy.get("http"))
        except Exception as exc:
            self.window.core.debug.log(exc)
        return False

    async def _remote_task(self, worker, task: str) -> str:
        if self.runtime.is_stopped() or worker.stop_requested:
            return "Execution cancelled."
        task = str(task or "").strip()
        if not task:
            return "Remote task is empty."
        self.runtime.emit_worker_status(worker, "Using configured remote tools")
        # Native provider wrappers cache mutable clients/token state. Serialize their
        # focused subcalls per orchestration runtime; workers still execute concurrently.
        async with self.runtime.remote_tool_lock:
            # Provider wrappers are part of PyGPT's bridge stack and may share
            # thread-affine/controller state. Keep the call on this BridgeWorker
            # thread instead of asyncio's generic executor.
            return self._remote_task_sync(worker, task)

    def _remote_task_sync(self, worker, task: str) -> str:
        model = self.runtime.model
        tmp = CtxItem(MODE_CHAT)
        tmp.meta = self.runtime.context.ctx.meta
        tmp.meta_id = getattr(self.runtime.context.ctx, "meta_id", None)
        tmp.internal = True
        tmp.hidden = True
        tmp.agent_call = True
        tmp.model = getattr(self.runtime.context.ctx, "model", None)
        tmp.set_input(task, "")
        tmp.set_output(None, "")

        ctx = BridgeContext(
            attachments=self.runtime.context.attachments,
            ctx=tmp,
            file_ids=self.runtime.context.file_ids,
            history=[],
            max_tokens=self.runtime.context.max_tokens,
            mode=MODE_CHAT,
            model=model,
            multimodal_ctx=self.runtime.context.multimodal_ctx,
            parent_mode=MODE_AGENT_V2,
            preset=self.runtime.preset,
            prompt=task,
            stream=False,
            system_prompt=(
                "Execute the requested focused task. Use provider-side remote tools enabled in PyGPT. "
                "Use the supplied current-turn attachments when relevant. Return concrete findings/results and preserve "
                "generated files, images and URLs."
            ),
        )
        extra = {"mode": MODE_CHAT, "internal": True, "agents_v2_remote": True}
        provider = model.get_provider() if model is not None else "openai"
        try:
            if provider == "google" and self.window.core.config.get("api_native_google", False):
                ok = self.window.core.api.google.call(ctx, extra)
            elif provider == "anthropic" and self.window.core.config.get("api_native_anthropic", False):
                ok = self.window.core.api.anthropic.call(ctx, extra)
            elif provider == "x_ai" and self.window.core.config.get("api_native_xai", False):
                ok = self.window.core.api.xai.call(ctx, extra)
            else:
                ok = self.window.core.api.openai.call(ctx, extra)
            self.runtime.collect_artifacts(tmp, worker)
            if not ok:
                return "Remote provider call failed."
            return str(tmp.output or "Remote task completed without textual output.")
        except Exception as exc:
            self.window.core.debug.log(exc)
            return f"Remote tool error: {exc}"
