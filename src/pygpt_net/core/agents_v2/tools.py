#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 11:00:00                  #
# ================================================== #

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from llama_index.core.base.llms.types import DocumentBlock, ImageBlock, TextBlock
from llama_index.core.tools import BaseTool, FunctionTool, QueryEngineTool, ToolMetadata

from pygpt_net.core.types import TOOL_QUERY_ENGINE_DESCRIPTION
from pygpt_net.core.command.tool_schema import JsonSchemaToolMetadata
from pygpt_net.utils import is_image


class SchemaToolMetadata(JsonSchemaToolMetadata):
    """Agents v2 plugin metadata using PyGPT JSON schemas verbatim."""

class WorkerToolFactory:
    """Build tools bound to one actor/runtime instead of legacy global agent state."""

    RESERVED = {
        "agent_create", "agent_update", "agent_run", "agent_status", "agent_list",
        "agent_wait", "agent_stop", "agent_remove", "workflow_status", "workflow_finish",
        "delegate_task", "report_status", "shared_context", "query_index", "swarm_start", "swarm_status",
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
                f"Report a short INTERMEDIATE activity/progress status to the {self.runtime.main_agent_name} "
                "and the user's transient status line. Use this before meaningful or potentially long phases. "
                "Do not use report_status to announce final completion; when work is complete, return the final "
                "worker response directly."
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
        """Expose normal PyGPT capabilities directly to the selected main agent."""
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
        self.runtime.verbose.log("REPORT STATUS CALL", {"status": status}, actor=getattr(worker, "id", "worker"))
        worker.progress = text
        if text:
            self.runtime.emit_worker_status(worker, text)
        return "Status updated."

    @staticmethod
    def _extract_runtime_attachments(value: Any) -> List[Dict[str, str]]:
        """Collect private runtime-attachment markers returned by plugins."""
        out: List[Dict[str, str]] = []

        def walk(item):
            if isinstance(item, dict):
                marked = item.get("agent_runtime_attachments")
                if isinstance(marked, list):
                    for entry in marked:
                        if isinstance(entry, dict):
                            path = str(entry.get("path") or "").strip()
                            if path:
                                out.append({
                                    "path": path,
                                    "name": str(entry.get("name") or os.path.basename(path)),
                                })
                        elif entry:
                            path = str(entry).strip()
                            if path:
                                out.append({"path": path, "name": os.path.basename(path)})
                for key, child in item.items():
                    if key != "agent_runtime_attachments":
                        walk(child)
            elif isinstance(item, list):
                for child in item:
                    walk(child)

        walk(value)
        unique: List[Dict[str, str]] = []
        seen = set()
        for entry in out:
            path = entry["path"]
            if path in seen:
                continue
            seen.add(path)
            unique.append(entry)
        return unique

    @staticmethod
    def _strip_runtime_attachment_markers(value: Any) -> Any:
        """Remove transport-only marker data from the visible/persisted tool result."""
        if isinstance(value, dict):
            return {
                key: WorkerToolFactory._strip_runtime_attachment_markers(child)
                for key, child in value.items()
                if key != "agent_runtime_attachments"
            }
        if isinstance(value, list):
            return [WorkerToolFactory._strip_runtime_attachment_markers(child) for child in value]
        return value

    @staticmethod
    def _response_text(response: Any) -> str:
        if isinstance(response, (dict, list)):
            return json.dumps(response, ensure_ascii=False, indent=2, default=str)
        return str(response)

    def _drain_transport_images(self, tool_ctx) -> List[Dict[str, str]]:
        """Drain screenshots/images produced only for the current tool/model round."""
        values = list(getattr(tool_ctx, "transport_images", None) or [])
        if not values:
            return []

        # Actor CtxItems are reused across tool rounds. Once the current result
        # has received these images as blocks, do not accidentally re-attach a
        # stale screenshot to the next unrelated tool call.
        tool_ctx.transport_images = []
        out = []
        filesystem = self.window.core.filesystem
        for value in values:
            raw = str(value or "").strip()
            if not raw:
                continue
            try:
                path = filesystem.to_workdir(raw, auto_prefix=False)
            except Exception:
                path = raw
            if os.path.isfile(path):
                out.append({"path": path, "name": os.path.basename(path)})
        return out

    def _runtime_attachment_blocks(
            self,
            response: Any,
            attachments: List[Dict[str, str]],
    ) -> List[Any]:
        """Convert plugin runtime attachments into LlamaIndex multimodal tool-output blocks."""
        blocks: List[Any] = [TextBlock(text=self._response_text(response))]
        model = self.runtime.model
        attached = []
        skipped = []

        for entry in attachments:
            path = str(entry.get("path") or "")
            name = str(entry.get("name") or os.path.basename(path))
            if not path or not os.path.isfile(path):
                skipped.append(name or path)
                continue

            if is_image(path):
                if model is not None and not model.is_image_input():
                    skipped.append(name)
                    continue
                blocks.append(ImageBlock(path=path))
            else:
                blocks.append(DocumentBlock(path=path, title=name))
            attached.append(path)

        if attached:
            self.runtime.verbose.log("RUNTIME ATTACHMENTS", {
                "attached": attached,
                "skipped": skipped,
            })
        if skipped:
            blocks[0] = TextBlock(text=(
                self._response_text(response)
                + "\nRuntime attachment skipped by the current model/provider: "
                + ", ".join(skipped)
            ))
        return blocks

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
                        actor_id = getattr(worker, "id", "worker")
                        self.runtime.verbose.log("LOCAL TOOL CALL", {
                            "tool": tool_name,
                            "raw_arguments": kwargs,
                        }, actor=actor_id)
                        if self.runtime.is_stopped() or worker.stop_requested:
                            self.runtime.verbose.log("LOCAL TOOL CANCELLED", {"tool": tool_name}, actor=actor_id)
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
                            error = {
                                "error": "Missing required tool parameter(s).",
                                "tool": tool_name,
                                "missing": missing,
                                "required": required,
                                "received": sorted(call_args.keys()),
                            }
                            self.runtime.verbose.log("LOCAL TOOL REJECTED", error, actor=actor_id)
                            return json.dumps(error, ensure_ascii=False)

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
                        self.runtime.verbose.log("LOCAL TOOL REQUEST", cmd, actor=actor_id)
                        self.runtime.emit_runtime_status(
                            "status.agent_v2.tool",
                            worker=worker if getattr(worker, "id", "") != "orchestrator" else None,
                            tool=tool_name,
                        )
                        # Plugin controller/API objects are shared with the rest of PyGPT.
                        # Keep their side effects serialized, while the worker LLM loops remain concurrent.
                        async with self.runtime.local_tool_lock:
                            # Persist the call in the exact order in which it reaches
                            # the serialized plugin dispatcher, with normalized params.
                            display_call_id = self.runtime.record_local_plugin_tool_call(
                                tool_name, call_args, actor=actor_id
                            )
                            # Only command dispatch touches the Qt thread. Long-running plugin
                            # work uses the plugin's normal QRunnable path; this coroutine
                            # awaits its reply without blocking the GUI event loop.
                            try:
                                response = await self.runtime.emitter.execute_plugin(
                                    tool_ctx,
                                    [cmd],
                                    self.runtime.is_stopped,
                                )
                            except Exception as exc:
                                # Keep failed executions inspectable as a completed
                                # request/response pair, then preserve the original
                                # exception semantics for the agent workflow.
                                self.runtime.record_local_plugin_tool_result(
                                    display_call_id,
                                    tool_name,
                                    {"error": str(exc)},
                                    actor=actor_id,
                                )
                                raise
                            runtime_attachments = self._extract_runtime_attachments(response)
                            runtime_attachments.extend(self._drain_transport_images(tool_ctx))
                            if runtime_attachments:
                                unique = []
                                seen_paths = set()
                                for entry in runtime_attachments:
                                    path = str(entry.get("path") or "")
                                    if not path or path in seen_paths:
                                        continue
                                    seen_paths.add(path)
                                    unique.append(entry)
                                runtime_attachments = unique
                            display_response = (
                                self._strip_runtime_attachment_markers(response)
                                if runtime_attachments else response
                            )
                            self.runtime.record_local_plugin_tool_result(
                                display_call_id,
                                tool_name,
                                display_response,
                                actor=actor_id,
                            )

                        self.runtime.verbose.log("LOCAL TOOL RESPONSE", {
                            "tool": tool_name,
                            "response": response,
                            "ctx_results": getattr(tool_ctx, "results", None),
                            "ctx_extra": getattr(tool_ctx, "extra", None),
                        }, actor=actor_id)
                        self.runtime.collect_artifacts(tool_ctx, worker)
                        # `reply` is a legacy chat-loop flag. It is useful while a plugin
                        # builds its response, but must not survive on a reusable actor ctx.
                        tool_ctx.reply = False

                        if runtime_attachments:
                            return self._runtime_attachment_blocks(display_response, runtime_attachments)
                        return self._response_text(response)
                    fn.__name__ = tool_name
                    return fn

                self.runtime.register_local_plugin_tool(name)
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
