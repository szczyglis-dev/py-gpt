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

import asyncio
import json
import os
import uuid
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from llama_index.core.agent.workflow import AgentStream, FunctionAgent, ReActAgent
from llama_index.core.base.llms.types import ChatMessage, ImageBlock, MessageRole, TextBlock
from llama_index.core.memory import Memory
from llama_index.core.tools import FunctionTool

from pygpt_net.core.types import MODE_AGENT_V2
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import is_image, trans

from .memory import OrchestratorMemoryStore
from .prompts import ORCHESTRATOR_BASE_PROMPT, WORKER_BASE_PROMPT
from .state import WorkerState, WorkerStatus
from .tools import WorkerToolFactory


class AgentsV2Runtime:
    """One isolated orchestration runtime bound to a single user turn."""

    MAX_WORKERS = 16

    # Code-level switch only (not exposed in presets/UI). Set to False to show
    # worker statuses without the "[Agent name]" prefix.
    SHOW_AGENT_NAME_IN_STATUS = False

    def __init__(self, window, context, extra, signals, emitter):
        self.window = window
        self.context = context
        self.extra = extra
        self.signals = signals
        self.emitter = emitter
        self.model = context.model
        self.preset = context.preset
        self.workers: Dict[str, WorkerState] = {}
        self.sequence = 0
        self.finished = False
        self.final_answer = ""
        self.run_id = uuid.uuid4().hex[:12]
        self.status_events: List[Dict[str, Any]] = []
        self._status_seq = 0
        self.memory_store = OrchestratorMemoryStore(window)
        self.allow_local_tools = bool(getattr(self.preset, "agent_v2_allow_local_tools", True))
        self.allow_remote_tools = bool(getattr(self.preset, "agent_v2_allow_remote_tools", True))
        self.index_id = (getattr(self.preset, "idx", None) if self.preset is not None else None) or context.idx
        if self.index_id == "_":
            self.index_id = None

        # PyGPT plugin/provider API wrappers keep mutable state. Workers themselves run
        # concurrently, but shared side-effecting bridges are serialized per runtime.
        self.local_tool_lock = asyncio.Lock()

        self.shared_context_text = self._build_shared_context()
        self.runtime_system_context = self._build_runtime_system_context()
        self.tool_factory = WorkerToolFactory(self)
        self._artifact_seen = {
            "files": set(), "images": set(), "urls": set(), "attachments": set()
        }
        self._seed_artifact_seen()
        self.orchestrator_actor = SimpleNamespace(
            id="orchestrator",
            name="Orchestrator",
            progress="",
            stop_requested=False,
            tool_ctx=self._make_tool_ctx("orchestrator"),
            artifacts={"files": [], "images": [], "urls": [], "attachments": []},
        )
        # Keep the Orchestrator's tool context private. Local PyGPT plugins set
        # ctx.reply/results as part of the legacy chat tool pipeline; using the
        # user-visible CtxItem here would feed a plugin result back through
        # KernelEvent.REPLY_RETURN and accidentally start a second Agents v2 run.
        self.orchestrator_actor.tool_ctx.set_input(
            str(getattr(self.context.ctx, "input", "") or self.context.prompt or ""),
            "orchestrator",
        )
        self.orchestrator_actor.tool_ctx.set_output("", "Orchestrator")

    def is_stopped(self) -> bool:
        return bool(self.window.controller.kernel.stopped())

    def _build_runtime_system_context(self) -> str:
        """Collect dynamic plugin runtime guidance published for Agents v2.

        Some plugin system-prompt additions are generated only at Bridge
        POST_PROMPT_END time. Agents v2 owns a separate Orchestrator/worker
        system prompt, so those additions must be explicitly carried into the
        runtime instead of assuming BridgeContext.system_prompt is consumed.
        """
        ctx = getattr(self.context, "ctx", None)
        extra = getattr(ctx, "extra", None) if ctx is not None else None
        if not isinstance(extra, dict):
            return ""
        value = extra.get("agents_v2_filesystem_context", "")
        return str(value or "").strip()

    def _seed_artifact_seen(self):
        """Do not re-export user inputs that were already attached to the main message."""
        main = self.context.ctx
        if main is None:
            return
        for attr in self._artifact_seen:
            for value in (getattr(main, attr, None) or []):
                try:
                    key = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
                except Exception:
                    key = repr(value)
                self._artifact_seen[attr].add(key)

    @staticmethod
    def _supports_function_calling(llm) -> bool:
        try:
            return bool(llm.metadata.is_function_calling_model)
        except Exception:
            return False

    def get_llm(self, stream: bool = False):
        """Return provider LLM with native remote tools attached when enabled."""
        return self.window.core.idx.llm.get_agent(
            model=self.model,
            stream=stream,
            allow_remote_tools=self.allow_remote_tools,
        )

    def build_agent(self, name: str, description: str, llm, system_prompt: str, tools):
        """Prefer native tool calling and retain ReAct as a compatibility fallback."""
        cls = FunctionAgent if self._supports_function_calling(llm) else ReActAgent
        kwargs = {
            "name": name,
            "description": description,
            "llm": llm,
            "system_prompt": system_prompt,
            "tools": tools,
        }
        # Ollama's native protocol supports parallel tool calls, but FunctionAgent
        # identifies native Ollama calls by tool name because Ollama does not expose
        # OpenAI-style call ids. Sequential calls keep the scratchpad mapping
        # deterministic (and avoid Gemma4 multi-call parser edge cases) while workers
        # themselves can still execute concurrently.
        if cls is FunctionAgent and self.model is not None and self.model.is_ollama():
            kwargs["allow_parallel_tool_calls"] = False
        return cls(**kwargs)

    def _memory_token_limit(self) -> int:
        model_ctx = int(getattr(self.model, "ctx", 0) or 0)
        limit = int(model_ctx * 0.75) if model_ctx > 0 else 40000
        configured = int(self.window.core.config.get("max_total_tokens") or 0)
        if configured > 0:
            limit = min(limit, configured)
        return max(2048, min(limit, 128000))

    def build_user_message(self, text: str) -> ChatMessage:
        """Build the same turn input for orchestrator/workers, including native image blocks when supported."""
        value = str(text or "")
        if self.model is None or not self.model.is_image_input():
            return ChatMessage(role=MessageRole.USER, content=value)

        blocks = [TextBlock(text=value)]
        seen = set()
        for attachment in (self.context.attachments or {}).values():
            path = str(getattr(attachment, "path", "") or "")
            if not path or path in seen or not os.path.isfile(path) or not is_image(path):
                continue
            seen.add(path)
            blocks.append(ImageBlock(path=path))
        return ChatMessage(role=MessageRole.USER, blocks=blocks)

    def _build_shared_context(self) -> str:
        parts: List[str] = []
        ctx = self.context.ctx
        if ctx is not None and ctx.hidden_input:
            parts.append(str(ctx.hidden_input))

        manifest = []
        for key, value in (self.context.attachments or {}).items():
            path = str(getattr(value, "path", "") or "")
            extra = getattr(value, "extra", None) or {}
            manifest.append({
                "id": str(key),
                "name": getattr(value, "name", None) or getattr(value, "filename", None) or str(key),
                "path": path,
                "native": bool(getattr(value, "remote", None) or extra.get("native_files")),
                "image": bool(path and is_image(path)),
            })
        if manifest:
            parts.append("Workflow attachment manifest:\n" + json.dumps(manifest, ensure_ascii=False, indent=2))

        if ctx is not None and ctx.images:
            parts.append("Images associated with this turn: " + ", ".join(map(str, ctx.images)))
        return "\n\n".join(p for p in parts if p).strip()

    def _worker_id(self) -> str:
        self.sequence += 1
        return f"w{self.sequence:02d}_{uuid.uuid4().hex[:6]}"

    def emit_worker_status(self, worker: WorkerState, text: str):
        worker.progress = str(text or "").strip()[:240]
        if worker.progress:
            self._status_seq += 1
            self.status_events.append({
                "seq": self._status_seq,
                "agent_id": worker.id,
                "agent_name": worker.name,
                "status": worker.progress,
            })
            # Bound memory even for very chatty workers. The current state remains
            # available through agent_status, while recent events are returned by agent_wait.
            if len(self.status_events) > 256:
                del self.status_events[:-256]
            display = worker.progress
            if self.SHOW_AGENT_NAME_IN_STATUS and worker.name:
                display = f"[{worker.name}] {display}"
            self.emitter.status(display, source=worker.id)

    @staticmethod
    def translated_status(key: str, **kwargs) -> str:
        """Translate a runtime-generated status and safely interpolate placeholders."""
        value = trans(key)
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return value

    def emit_runtime_status(self, key: str, worker: Optional[WorkerState] = None, **kwargs):
        text = self.translated_status(key, **kwargs)
        if worker is not None:
            self.emit_worker_status(worker, text)
        else:
            self.emitter.status(text, source="orchestrator")

    def collect_llm_artifacts(self, llm, worker: Optional[WorkerState] = None):
        """Drain provider-native artifacts captured by an Agents v2 LLM adapter.

        Hosted/provider-side tools do not run through the local PyGPT plugin
        ``CtxItem``, so their metadata (notably OpenAI web-search source URLs)
        must be bridged explicitly back into the user-visible context.
        """
        if llm is None:
            return
        pop_urls = getattr(llm, "pop_pygpt_urls", None)
        if not callable(pop_urls):
            return
        try:
            urls = pop_urls() or []
        except Exception as exc:
            self.window.core.debug.log(exc)
            return
        if not urls:
            return

        actor = worker if worker is not None else self.orchestrator_actor
        source_ctx = getattr(actor, "tool_ctx", None)
        if source_ctx is None:
            return
        if not isinstance(source_ctx.urls, list):
            source_ctx.urls = []
        seen = set(source_ctx.urls)
        for url in urls:
            value = str(url or "").strip()
            if not value or value in seen:
                continue
            source_ctx.urls.append(value)
            seen.add(value)
        self.collect_artifacts(source_ctx, worker)

    def collect_artifacts(self, source_ctx: CtxItem, worker: Optional[WorkerState] = None):
        """Merge worker artifacts into the user-visible context and worker status payload."""
        main = self.context.ctx
        if source_ctx is None or main is None or source_ctx is main:
            return
        # Raw plugin `results` are model-facing tool responses, not user artifacts.
        # Propagating them into the main CtxItem can make the regular renderer treat
        # an Agents v2 turn like a legacy tool-reply chain. Only durable artifacts
        # are exported to the user-visible context.
        for attr in ("files", "images", "urls", "attachments"):
            values = getattr(source_ctx, attr, None) or []
            target = getattr(main, attr, None)
            if target is None:
                target = []
                setattr(main, attr, target)
            for value in values:
                try:
                    key = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
                except Exception:
                    key = repr(value)
                if key in self._artifact_seen[attr]:
                    continue
                self._artifact_seen[attr].add(key)
                target.append(value)
                if worker is not None:
                    worker.artifacts[attr].append(value)
        try:
            self.window.core.ctx.update_item(main)
        except Exception:
            pass

    @staticmethod
    def _result_text(result: Any) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return result.strip()
        response = getattr(result, "response", None)
        if response is not None:
            content = getattr(response, "content", None)
            if content:
                return str(content).strip()
            if isinstance(response, str):
                return response.strip()
        content = getattr(result, "content", None)
        if content:
            return str(content).strip()
        return str(result).strip()

    def _make_tool_ctx(self, actor_id: str) -> CtxItem:
        """Create an isolated plugin/tool context for an Agents v2 actor.

        PyGPT plugins are built around CtxItem and may set `reply`, `results`,
        `extra.tool_output`, etc.  Those fields must never mutate the main chat
        CtxItem, otherwise the legacy reply pipeline can schedule INPUT_SYSTEM
        and create another user-visible Agents v2 turn from a tool result.
        """
        parent = self.context.ctx
        ctx = CtxItem(MODE_AGENT_V2)
        ctx.meta = parent.meta if parent else None
        ctx.meta_id = getattr(parent, "meta_id", None)
        ctx.model = getattr(parent, "model", None)
        if parent is not None:
            ctx.images = list(parent.images or [])
            ctx.attachments = list(parent.attachments or [])
            ctx.additional_ctx = list(parent.additional_ctx or [])
            ctx.doc_ids = list(parent.doc_ids or [])
            ctx.hidden_input = parent.hidden_input
        ctx.agent_call = True
        ctx.async_disabled = False
        ctx.internal = True
        ctx.hidden = True
        ctx.current = False
        ctx.extra = {
            "agents_v2_actor": actor_id,
            "run_id": self.run_id,
            # Let normal PyGPT plugins use their own QRunnable workers. The agent
            # awaits the result through the Agents v2 completion bridge instead
            # of forcing the plugin to execute synchronously on the Qt GUI thread.
            "agents_v2_async_tool": True,
        }
        return ctx

    def _make_worker_ctx(self, worker_id: str) -> CtxItem:
        ctx = self._make_tool_ctx(worker_id)
        ctx.extra["agents_v2_worker"] = worker_id
        return ctx

    def _worker_prompt(self, name: str, instruction: str, language: str, system_prompt: str) -> str:
        return "\n\n".join(filter(None, [
            WORKER_BASE_PROMPT,
            f"<workflow_language>\n{language}\n</workflow_language>",
            f"<worker_identity>\nname={name}\nrole_instruction={instruction}\n</worker_identity>",
            (
                f"<runtime_environment>\n{self.runtime_system_context}\n</runtime_environment>"
                if self.runtime_system_context else ""
            ),
            (
                f"<orchestrator_system_instruction>\n{system_prompt}\n</orchestrator_system_instruction>"
                if system_prompt else ""
            ),
        ])).strip()

    async def create_worker(
            self,
            name: str,
            instruction: str,
            language: str,
            system_prompt: str = "",
            task: str = "",
    ) -> str:
        if len(self.workers) >= self.MAX_WORKERS:
            return json.dumps({"error": f"Maximum workers reached ({self.MAX_WORKERS})."})
        wid = self._worker_id()
        name = (name or "Worker").strip()[:80]
        instruction = (instruction or "General specialist").strip()
        language = str(language or "").strip()
        if not language:
            return json.dumps({
                "error": "Worker language is required.",
                "action": "Pass the language of the current end-user request (for example: Polish, English, German).",
            }, ensure_ascii=False)
        state = WorkerState(
            id=wid,
            name=name,
            instruction=instruction,
            language=language[:80],
            system_prompt=system_prompt or "",
            agent=None,
            memory=Memory.from_defaults(
                session_id=f"agents_v2_{self.run_id}_{wid}",
                token_limit=self._memory_token_limit(),
            ),
            tool_ctx=self._make_worker_ctx(wid),
        )
        llm = self.get_llm(stream=False)
        state.agent = self.build_agent(
            name=name,
            description=instruction[:512],
            llm=llm,
            system_prompt=self._worker_prompt(name, instruction, state.language, system_prompt or ""),
            tools=self.tool_factory.build(state),
        )
        self.workers[wid] = state
        if task:
            await self.start_worker(wid, task)
        return json.dumps(state.public_dict(), ensure_ascii=False, default=str)

    async def update_worker(
            self,
            agent_id: str,
            name: Optional[str] = None,
            instruction: Optional[str] = None,
            language: Optional[str] = None,
            system_prompt: Optional[str] = None,
    ) -> str:
        state = self.workers.get(agent_id)
        if state is None or state.status == WorkerStatus.REMOVED:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        if state.busy:
            return json.dumps({"error": "Worker is running; stop/wait before updating it.", "id": agent_id})
        if name is not None and name.strip():
            state.name = name.strip()[:80]
        if instruction is not None and instruction.strip():
            state.instruction = instruction.strip()
        if language is not None and language.strip():
            state.language = language.strip()[:80]
        if system_prompt is not None:
            state.system_prompt = system_prompt.strip()

        # Rebuild the agent definition while deliberately preserving Memory.
        llm = self.get_llm(stream=False)
        state.agent = self.build_agent(
            name=state.name,
            description=state.instruction[:512],
            llm=llm,
            system_prompt=self._worker_prompt(state.name, state.instruction, state.language, state.system_prompt),
            tools=self.tool_factory.build(state),
        )
        state.status = WorkerStatus.CREATED
        state.progress = ""
        state.error = ""
        return json.dumps(state.public_dict(), ensure_ascii=False, default=str)

    async def start_worker(self, agent_id: str, task: str) -> str:
        state = self.workers.get(agent_id)
        if state is None or state.status == WorkerStatus.REMOVED:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        if state.busy:
            return json.dumps({"error": "Worker is already running", "id": agent_id})
        state.current_task = str(task or "").strip()
        if not state.current_task:
            return json.dumps({"error": "Task is empty", "id": agent_id})
        state.stop_requested = False
        state.status = WorkerStatus.RUNNING
        state.progress = ""
        # Keep the worker-local tool context aligned with the current assignment.
        # Some PyGPT plugins inspect ctx.input/output even when invoked as tools.
        state.tool_ctx.set_input(state.current_task, "orchestrator")
        state.tool_ctx.set_output("", state.name)
        state.error = ""
        state.last_result = ""
        state.generation += 1
        self.emit_runtime_status("status.agent_v2.starting", worker=state)
        state.task = asyncio.create_task(
            self._worker_loop(state, state.current_task),
            name=f"agents-v2:{agent_id}",
        )
        return json.dumps(state.public_dict(include_result=False), ensure_ascii=False, default=str)

    async def _worker_loop(self, state: WorkerState, task: str):
        handler = None
        try:
            shared_hint = ""
            if self.shared_context_text:
                shared_hint = (
                    "\n\nThis workflow has shared user attachments/context. Use shared_context for extracted text/manifest; "
                    "image inputs from the current turn are also attached to this task when the selected model supports them."
                )
            handler = state.agent.run(
                user_msg=self.build_user_message(f"Task from Orchestrator:\n{task}{shared_hint}"),
                memory=state.memory,
                max_iterations=24,
                early_stopping_method="generate",
            )
            async for event in handler.stream_events():
                if self.is_stopped() or state.stop_requested:
                    state.status = WorkerStatus.STOPPING
                    try:
                        await handler.cancel_run()
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        pass
                    raise asyncio.CancelledError()
                # Worker answer text is private. Progress reaches the UI through report_status.
                if isinstance(event, AgentStream):
                    continue
            result = await handler
            state.last_result = self._result_text(result)
            state.status = WorkerStatus.COMPLETED
            self.emit_runtime_status("status.agent_v2.completed", worker=state)
            self.collect_artifacts(state.tool_ctx, state)
            return state.last_result
        except asyncio.CancelledError:
            if handler is not None:
                try:
                    await handler.cancel_run()
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
            state.status = WorkerStatus.STOPPED
            self.emit_runtime_status("status.agent_v2.stopped", worker=state)
            return ""
        except Exception as exc:
            state.status = WorkerStatus.FAILED
            state.error = str(exc)
            self.emit_runtime_status("status.agent_v2.failed", worker=state)
            self.window.core.debug.log(exc)
            return ""
        finally:
            self.collect_llm_artifacts(getattr(state.agent, "llm", None), state)
            self.collect_artifacts(state.tool_ctx, state)

    async def stop_worker(self, agent_id: str) -> str:
        state = self.workers.get(agent_id)
        if state is None:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        state.stop_requested = True
        if state.task and not state.task.done():
            state.status = WorkerStatus.STOPPING
            state.task.cancel()
            await asyncio.gather(state.task, return_exceptions=True)
        if state.status != WorkerStatus.REMOVED:
            state.status = WorkerStatus.STOPPED
        return json.dumps(state.public_dict(), ensure_ascii=False, default=str)

    async def remove_worker(self, agent_id: str) -> str:
        state = self.workers.get(agent_id)
        if state is None:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        if state.busy:
            await self.stop_worker(agent_id)
        state.status = WorkerStatus.REMOVED
        self.workers.pop(agent_id, None)
        return json.dumps({"id": agent_id, "removed": True})

    async def worker_status(self, agent_id: str) -> str:
        state = self.workers.get(agent_id)
        if state is None:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        return json.dumps(state.public_dict(), ensure_ascii=False, default=str)

    async def worker_list(self) -> str:
        return json.dumps(
            [w.public_dict(include_result=False) for w in self.workers.values()],
            ensure_ascii=False,
            default=str,
        )

    async def wait_workers(self, agent_ids: str = "", wait_for: str = "all", timeout_seconds: int = 60) -> str:
        ids = [x.strip() for x in str(agent_ids or "").split(",") if x.strip()]
        if not ids:
            ids = list(self.workers.keys())
        states = [self.workers[i] for i in ids if i in self.workers]
        missing = [i for i in ids if i not in self.workers]
        if not states:
            return json.dumps({"error": "No matching workers", "missing": missing})

        tasks = [s.task for s in states if s.task is not None and not s.task.done()]
        mode = str(wait_for or "all").lower()
        if mode not in ("all", "any"):
            mode = "all"
        if tasks:
            waiting_names = ", ".join(s.name for s in states if s.task is not None and not s.task.done())
            self.emit_runtime_status("status.agent_v2.waiting", name=waiting_names)
            timeout = max(1, min(int(timeout_seconds or 60), 600))
            try:
                await asyncio.wait(
                    tasks,
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED if mode == "any" else asyncio.ALL_COMPLETED,
                )
            except Exception as exc:
                self.window.core.debug.log(exc)
        selected_ids = {s.id for s in states}
        payload = {
            "workers": [s.public_dict() for s in states],
            "missing": missing,
            "recent_status_events": [
                event for event in self.status_events if event.get("agent_id") in selected_ids
            ][-64:],
        }
        return json.dumps(payload, ensure_ascii=False, default=str)

    async def set_status(self, status: str) -> str:
        self.emitter.status(str(status or "").strip(), source="orchestrator")
        return "Status updated."

    async def finish_workflow(self, final_answer: str) -> str:
        """Finalize only after the orchestration graph has reached a stable state."""
        if self.finished:
            return "Workflow is already finished."

        running = [w for w in self.workers.values() if w.busy]
        never_started = [
            w for w in self.workers.values()
            if w.status == WorkerStatus.CREATED and w.generation == 0
        ]
        if running or never_started:
            payload = {
                "error": "Workflow cannot finish while workers are still running or were created but never started.",
                "running": [w.public_dict(include_result=False) for w in running],
                "never_started": [w.public_dict(include_result=False) for w in never_started],
                "action": "Wait for/stop running workers and run or remove unused workers, then call workflow_finish again.",
            }
            return json.dumps(payload, ensure_ascii=False, default=str)

        answer = str(final_answer or "").strip()
        if not answer:
            return json.dumps({
                "error": "final_answer is empty.",
                "action": "Provide the complete user-facing final answer to workflow_finish.",
            }, ensure_ascii=False)

        self.finished = True
        self.final_answer = answer
        self.emitter.clear_status()
        tail = self.emitter.text.rstrip()
        if not tail.endswith(self.final_answer):
            self.emitter.mark_block_boundary()
            self.emitter.append(self.final_answer)
        return "Workflow marked as finished. The runtime will stop the orchestrator now."

    def orchestrator_tools(self) -> List[FunctionTool]:
        tools: List[FunctionTool] = [
            FunctionTool.from_defaults(
                async_fn=self.create_worker,
                name="agent_create",
                description=(
                    "Create a runtime worker. Parameters: name, instruction, language, optional system_prompt, optional task. "
                    "language is REQUIRED and must match the language of the current end-user request. "
                    "When task is provided the worker starts immediately and runs asynchronously."
                ),
            ),
            FunctionTool.from_defaults(
                async_fn=self.update_worker,
                name="agent_update",
                description="Update an idle worker's name/role/language/system prompt while preserving its in-memory history.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.start_worker,
                name="agent_run",
                description="Start/reuse an existing idle/completed worker on a new task. Its in-memory history is retained.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.worker_status,
                name="agent_status",
                description="Return one worker's state, latest progress, result, error and produced artifacts as JSON.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.worker_list,
                name="agent_list",
                description="Return all runtime workers and their states as JSON.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.wait_workers,
                name="agent_wait",
                description=(
                    "Wait asynchronously for comma-separated agent_ids, or all workers when empty. "
                    "wait_for is 'all' or 'any'; timeout_seconds is capped at 600."
                ),
            ),
            FunctionTool.from_defaults(
                async_fn=self.stop_worker,
                name="agent_stop",
                description="Cooperatively stop/cancel a running worker by ID.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.remove_worker,
                name="agent_remove",
                description="Stop if needed and remove a runtime worker by ID.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.set_status,
                name="workflow_status",
                description="Set/replace the single transient user-visible workflow status line.",
            ),
            FunctionTool.from_defaults(
                async_fn=self.finish_workflow,
                name="workflow_finish",
                description=(
                    "Finalize the whole user task. Pass the complete final_answer. Call exactly once after all required "
                    "work and verification are complete. Calling it terminates the orchestrator loop."
                ),
            ),
        ]
        # Orchestrator remains a full PyGPT actor; delegation is a strategy, not a capability boundary.
        tools.extend(self.tool_factory.build_orchestrator(self.orchestrator_actor))
        return tools

    def orchestrator_prompt(self) -> str:
        additional = ""
        if self.preset is not None:
            additional = str(getattr(self.preset, "prompt", "") or "").strip()
        capabilities = [
            f"selected_model={getattr(self.model, 'id', '')}",
            f"allow_local_tools={self.allow_local_tools}",
            f"rag_index={self.index_id or 'none'}",
            f"shared_attachment_context={'yes' if self.shared_context_text else 'no'}",
            f"max_parallel_workers={self.MAX_WORKERS}",
        ]
        runtime_environment = ""
        if self.runtime_system_context:
            runtime_environment = (
                "\n\n<runtime_environment>\n"
                + self.runtime_system_context
                + "\n</runtime_environment>"
            )
        return (
            ORCHESTRATOR_BASE_PROMPT
            + "\n\n<runtime_capabilities>\n" + "\n".join(capabilities) + "\n</runtime_capabilities>"
            + runtime_environment
            + "\n\n<additional_instruction>\n" + additional + "\n</additional_instruction>"
        )

    async def cleanup(self):
        for state in list(self.workers.values()):
            if state.task and not state.task.done():
                state.stop_requested = True
                state.task.cancel()
        pending = [s.task for s in self.workers.values() if s.task is not None and not s.task.done()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        self.workers.clear()
