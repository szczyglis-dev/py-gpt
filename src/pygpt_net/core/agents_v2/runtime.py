#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.17 13:20:00                  #
# ================================================== #

from __future__ import annotations

import asyncio
import sys
import uuid
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.tools import FunctionTool

from pygpt_net.item.ctx import CtxItem

from .artifacts import RuntimeArtifacts
from .context import RuntimeContext
from .contracts import RuntimeInput, RuntimeOutput
from .delegation import AgentDelegateBridge
from .memory import AgentsV2MemoryStore
from .mode import AGENT_MODE, AGENT_MODE_CONFIG_DEFAULT, AGENT_MODE_CONFIG_KEY, AgentMode
from .prompt_builder import RuntimePromptBuilder
from .state import WorkerState
from .status import RuntimeStatus
from .strategy import get_agent_strategy
from .timeline import RuntimeTimeline
from .tools import WorkerToolFactory
from .tool_history import RuntimeToolHistory
from .toolset import RuntimeToolset
from .usage import RuntimeUsage
from .utils import effective_iteration_limit
from .verbose import AgentsV2VerboseLogger
from .workers import WorkerRuntime


class AgentsV2Runtime:
    """Facade for one isolated Agents v2 user turn.

    Shared state stays here for compatibility; domain behavior lives in explicit
    collaborators for timeline, tool history, context, status, artifacts, worker
    lifecycle, tool surfaces and prompt composition.
    """

    MAX_WORKERS_DEFAULT = 16

    # Code-level switch only (not exposed in presets/UI). Swarm mode always
    # prefixes worker statuses with the numbered agent identity; other modes use
    # this fallback switch.
    SHOW_AGENT_NAME_IN_STATUS = False

    # Automatic aggregate Swarm status cadence. Individual worker updates may
    # trigger an earlier aggregate refresh, but the reporter never emits more
    # often than this interval unless explicitly requested through swarm_status.
    SWARM_STATUS_INTERVAL = 4.0

    # Keep the aggregate Swarm row readable when single-live-status mode is used.
    # This is a UI-only hold: execution continues and newer statuses are coalesced
    # by RuntimeEmitter until the visibility window expires.
    SWARM_STATUS_MIN_VISIBLE = 2.5

    # Fallback default for the Settings option ``agent.v2.show_tool_chain``.
    # When enabled, normal tool calls made anywhere in the Agents v2 flow are
    # exported to the main conversation CtxItem under ``ctx.extra["tool_calls"]``
    # for durable UI inspection. Orchestration/worker-management plumbing is
    # deliberately excluded.
    RETURN_TOOL_CALLS_TO_MAIN_CTX = False

    # Iteration limits are user-configurable in Settings -> Agents -> Chat with Agents.
    # LlamaIndex treats max_iterations=0 as a falsy value and replaces it with its
    # own default, so PyGPT maps 0 to sys.maxsize to provide the documented
    # "unlimited" behavior while keeping the upstream API contract unchanged.
    MAIN_MAX_ITERATIONS_DEFAULT = 48
    SWARM_MAX_ITERATIONS_DEFAULT = 4096
    WORKER_MAX_ITERATIONS_DEFAULT = 24
    UNLIMITED_MAX_ITERATIONS = sys.maxsize

    _STATUS_ONLY_TOOLS = {"report_status", "workflow_status", "swarm_status"}

    def _show_tool_status(self, tool_name: str) -> bool:
        """Return whether Agents v2 should expose a raw per-tool status row.

        Chat with Agents intentionally keeps implementation-level tool names off
        the user-facing progress surface. The model reports semantic activity via
        ``workflow_status`` (top-level actor) or ``report_status`` (workers), where
        one status may cover many tool calls, retries, edits and checks. Structured
        tool call blocks remain independently available through the normal tool-call
        display/storage settings; only the transient ``Using tool: <name>`` row is
        suppressed here.
        """
        return False

    def __init__(self, window, context, extra, signals, emitter):
        self.window = window
        self.context = context
        self.extra = extra
        self.signals = signals
        self.emitter = emitter

        # Runtime is a facade. Domain work lives in explicit collaborators so
        # execution modes can evolve independently without growing this class.
        self.timeline = RuntimeTimeline(self)
        self.tool_history = RuntimeToolHistory(self)
        self.context_api = RuntimeContext(self)
        self.status_api = RuntimeStatus(self)
        self.artifact_api = RuntimeArtifacts(self)
        self.usage_api = RuntimeUsage(self)
        self.worker_api = WorkerRuntime(self)
        self.toolset_api = RuntimeToolset(self)
        self.prompt_api = RuntimePromptBuilder(self)
        requested_mode = None
        if isinstance(extra, dict):
            requested_mode = extra.get("agent_v2_mode")
        if requested_mode in (None, ""):
            requested_mode = getattr(context, "agent_v2_mode", None)
        if requested_mode in (None, ""):
            requested_mode = self.window.core.config.get(
                AGENT_MODE_CONFIG_KEY,
                AGENT_MODE_CONFIG_DEFAULT,
            )
        self.agent_id, self.agent_mode, self.agent_definition = (
            self.window.core.agents_v2.editor.resolve_selection(requested_mode or AGENT_MODE)
        )
        self.strategy = get_agent_strategy(self.agent_mode)
        self.model = context.model
        self.preset = context.preset
        self.workers: Dict[str, WorkerState] = {}
        self.sequence = 0
        self.finished = False
        self.final_answer = ""
        # Orchestrator/Swarm finalization is deliberately two-phase.
        # workflow_finish validates the workflow and arms the next ordinary LLM
        # pass as the authoritative final response; that pass can then be streamed
        # natively token-by-token through AgentStream.
        self.workflow_final_requested = False
        self.workflow_final_stream_started = False
        self.workflow_final_hint = ""
        self.run_id = uuid.uuid4().hex[:12]
        self.verbose = AgentsV2VerboseLogger(window, self.run_id, agent_mode=self.agent_mode)
        self.status_events: List[Dict[str, Any]] = []
        self._status_seq = 0
        self.swarm_expected_workers: Optional[int] = None
        self.swarm_created_workers = 0
        self.swarm_launched_workers = 0
        self._swarm_worker_numbers: Dict[str, int] = {}
        self._swarm_reporter_task: Optional[asyncio.Task] = None
        self._last_swarm_status_at = 0.0
        self._main_tool_calls: List[Dict[str, Any]] = []
        self._main_tool_call_seq = 0
        self._local_plugin_tool_names = set()
        self._actor_parts = {}
        self._actor_needs_new_part = {}
        self._actor_part_seq = {}
        # Keep a runtime-side copy of Primary Agent prose boundaries. Durable
        # CtxItemPart rows are updated on the Qt thread, so they are not a safe
        # source for deciding which streamed LLM pass is the final answer while
        # the run is still active. Provider-native hosted tools (OpenAI/xAI
        # web/file search, code interpreter, etc.) also bypass LlamaIndex
        # ToolCall/ToolCallResult events, so the adapter reports those boundaries
        # explicitly through note_provider_tool_activity().
        self._primary_stream_current = ""
        self._primary_stream_completed: List[str] = []
        self._primary_tool_activity_seen = False
        self._persisted_tool_tasks = {}
        # Workers keep their own agent Memory strictly in RAM. For persistence
        # we only remember which orchestrator partial launched the current worker
        # run, so worker tool tasks/output can be attached there without creating
        # worker CtxItemPart rows.
        self._worker_parent_parts = {}
        self._stored_worker_context_runs = set()
        self.return_tool_calls_to_main_ctx = bool(
            self.window.core.config.get(
                "agent.v2.show_tool_chain",
                self.RETURN_TOOL_CALLS_TO_MAIN_CTX,
            )
        )
        self.memory_store = AgentsV2MemoryStore(window)
        self.allow_local_tools = bool(getattr(self.preset, "agent_v2_allow_local_tools", True))
        self.allow_remote_tools = bool(getattr(self.preset, "agent_v2_allow_remote_tools", True))
        self.index_id = (getattr(self.preset, "idx", None) if self.preset is not None else None) or context.idx
        if self.index_id == "_":
            self.index_id = None
        self.rag_context_text = ""

        # PyGPT plugin/provider API wrappers keep mutable state. Workers themselves run
        # concurrently, but shared side-effecting bridges are serialized per runtime.
        self.local_tool_lock = asyncio.Lock()
        # Keep the exact provider adapter used by every actor. Besides final buffer
        # draining this lets streamed AgentStream/AgentOutput raw metadata be merged
        # into the same artifact path even if LlamaIndex serializes a response.
        self._actor_llms: Dict[str, Any] = {}

        # Native image input in Agents v2 uses ImageBlock directly, outside the
        # normal LlamaIndex Context.append_images() path. Persist the same image
        # references on the main CtxItem so they survive reload and are rendered
        # with the conversation item just like images sent in Chat/Chat with Files.
        self._persist_input_images()
        self.shared_context_text = self._build_shared_context()
        self.runtime_system_context = self._build_runtime_system_context()
        # Project rules are loaded lazily by main_agent_prompt(), immediately
        # before the first top-level agent input. Keeping the cache here avoids
        # touching AGENTS.md in runtimes (for example Experts) that reuse this
        # backend but do not use the Chat with Agents main prompt.
        self.project_rules_text = ""
        self.project_rules_loaded = False
        # BridgeWorker has already executed POST_PROMPT_END before Agents v2 is
        # started. Consume that final prompt verbatim so every enabled plugin
        # (Real Time, Files I/O, Extra Prompt, Vision, etc.) contributes exactly
        # the same system-prompt additions as it does in Chat.
        self.bridge_system_prompt = str(getattr(context, "system_prompt", "") or "").strip()
        # Older builds persisted this runtime-only value. Strip it from the live
        # item so any subsequent context update also removes it from storage.
        main_ctx = getattr(context, "ctx", None)
        if main_ctx is not None and isinstance(getattr(main_ctx, "extra", None), dict):
            main_ctx.extra.pop("agents_v2_filesystem_context", None)
        self.tool_factory = WorkerToolFactory(self)
        # Primary Agent exposes this bridge as delegate_task(); Orchestrator keeps
        # the explicit worker lifecycle tools. The worker runtime itself is shared.
        self.delegate_bridge = AgentDelegateBridge(self)
        self._artifact_seen = {
            "files": set(), "images": set(), "urls": set(), "attachments": set()
        }
        # Cross-channel identity set: a file-like artifact may arrive as a file,
        # image or attachment from different actors/tools, but is delivered once.
        self._artifact_delivery_seen = set()
        self._pending_artifacts = {
            "files": [], "images": [], "urls": [], "attachments": []
        }
        self._seed_artifact_seen()
        self.primary_actor = SimpleNamespace(
            # Keep the historical actor id for persisted-part/UI compatibility.
            id="orchestrator",
            name=self.main_agent_name,
            progress="",
            stop_requested=False,
            tool_ctx=self._make_tool_ctx("orchestrator"),
            artifacts={"files": [], "images": [], "urls": [], "attachments": []},
        )
        # Compatibility alias for integrations written against the pre-2.8.x
        # manager/orchestrator runtime surface.
        self.orchestrator_actor = self.primary_actor
        # Keep the Primary Agent's tool context private. Local PyGPT plugins set
        # ctx.reply/results as part of the legacy chat tool pipeline; using the
        # user-visible CtxItem here would feed a plugin result back through
        # KernelEvent.REPLY_RETURN and accidentally start a second Agents v2 run.
        self.orchestrator_actor.tool_ctx.set_input(
            str(getattr(self.context.ctx, "final_input", None) or self.context.prompt or ""),
            "orchestrator",
        )
        self.orchestrator_actor.tool_ctx.set_output("", self.main_agent_name)
        self.verbose.log("RUNTIME INIT", {
            "agent_mode": self.agent_mode.value,
            "agent_id": self.agent_id,
            "agent_name": self.main_agent_name,
            "model": getattr(self.model, "id", None),
            "provider": getattr(self.model, "provider", None) if self.model is not None else None,
            "preset": getattr(self.preset, "name", None) or getattr(self.preset, "id", None),
            "allow_local_tools": self.allow_local_tools,
            "allow_remote_tools": self.allow_remote_tools,
            "show_tool_chain": self.return_tool_calls_to_main_ctx,
            "index_id": self.index_id,
            "shared_context": self.shared_context_text,
            "runtime_system_context": self.runtime_system_context,
            "bridge_system_prompt": self.bridge_system_prompt,
            "max_workers": (
                "user_defined" if self.is_swarm_mode
                else (self.max_workers_configured or "unlimited")
            ),
            "main_max_iterations": self.main_max_iterations_configured or "unlimited",
            "worker_max_iterations": self.worker_max_iterations_configured or "unlimited",
        })
    @classmethod
    def from_input(cls, data: RuntimeInput) -> "AgentsV2Runtime":
        """Create a runtime from the stable high-level input contract."""
        return cls(data.window, data.context, data.extra, data.signals, data.emitter)

    def output(self) -> RuntimeOutput:
        """Return a compact snapshot for callers that do not need runtime internals."""
        return RuntimeOutput(
            run_id=self.run_id,
            agent_mode=self.agent_mode,
            finished=bool(self.finished),
            final_answer=str(self.final_answer or ""),
        )

    @property
    def is_orchestrator_mode(self) -> bool:
        return self.agent_mode == AgentMode.ORCHESTRATOR

    @property
    def is_primary_agent_mode(self) -> bool:
        return self.agent_mode == AgentMode.PRIMARY_AGENT

    def _configured_iteration_limit(self, key: str, default: int) -> int:
        """Return a validated iteration limit from config (0 means unlimited)."""
        try:
            value = int(self.window.core.config.get(key, default))
        except (TypeError, ValueError):
            value = int(default)
        if value < 0:
            value = 0
        return value

    @property
    def main_max_iterations_configured(self) -> int:
        default = int(getattr(self, self.strategy.main_iterations_default_attr))
        return self._configured_iteration_limit(
            self.strategy.main_iterations_key,
            default,
        )

    @property
    def main_max_iterations(self) -> int:
        return effective_iteration_limit(self.main_max_iterations_configured)

    @property
    def max_workers_configured(self) -> int:
        """Maximum workers for Chat/Orchestrator modes (0 means unlimited)."""
        return self._configured_iteration_limit(
            "agent.v2.max_workers",
            self.MAX_WORKERS_DEFAULT,
        )

    @property
    def worker_max_iterations_configured(self) -> int:
        return self._configured_iteration_limit(
            "agent.v2.worker.max_iterations",
            self.WORKER_MAX_ITERATIONS_DEFAULT,
        )

    @property
    def worker_max_iterations(self) -> int:
        return effective_iteration_limit(self.worker_max_iterations_configured)

    @property
    def is_swarm_mode(self) -> bool:
        return self.agent_mode == AgentMode.SWARM

    @property
    def uses_workflow_finish(self) -> bool:
        return self.strategy.uses_workflow_finish

    @property
    def awaiting_workflow_final_response(self) -> bool:
        """True after workflow_finish accepted and before the final pass ends."""
        return bool(self.workflow_final_requested and not self.finished)

    @property
    def main_agent_name(self) -> str:
        if self.agent_definition is not None:
            return str(self.agent_definition.get("name") or "Custom Agent")
        return self.strategy.main_name

    @property
    def main_agent_description(self) -> str:
        if self.agent_definition is not None:
            return "Custom Chat with Agents workflow"
        return self.strategy.main_description

    def main_event(self, suffix: str) -> str:
        return f"{self.strategy.event_prefix} {str(suffix or '').strip()}".strip()

    def verbose_log(self, event: str, data: Any = None, actor: str = "orchestrator"):
        self.verbose.log(event, data, actor=actor)

    def verbose_text(self, event: str, text: Any, actor: str = "orchestrator"):
        self.verbose.text(event, text, actor=actor)

    def is_stopped(self) -> bool:
        return bool(self.window.controller.kernel.stopped())

    # TIMELINE / STREAM API ---------------------------------------------------

    def _close_primary_stream_segment(self):
        return self.timeline._close_primary_stream_segment()

    def note_provider_tool_activity(
            self,
            tool_name: str,
            actor: str = "orchestrator",
            call_id: str = "",
    ):
        return self.timeline.note_provider_tool_activity(tool_name, actor, call_id)

    def primary_stream_final_output(self) -> str:
        return self.timeline.primary_stream_final_output()

    def verbose_event(self, event: Any, actor: str = "orchestrator"):
        return self.timeline.verbose_event(event, actor)

    # TOOL REGISTRY ----------------------------------------------------------

    def register_local_plugin_tool(self, name: str):
        return self.tool_history.register_local_plugin_tool(name)

    # ACTOR PARTS API ---------------------------------------------------------

    def _actor_metadata(self, actor: str):
        return self.timeline._actor_metadata(actor)

    def _actor_part(self, actor: str, create: bool = True):
        return self.timeline._actor_part(actor, create)

    def _begin_actor_part(
            self,
            actor: str,
            reuse_initial: bool = False,
            extra: Optional[dict] = None,
            joiner: str = "",
    ):
        return self.timeline._begin_actor_part(actor, reuse_initial, extra, joiner)

    def _prepare_actor_response_part(self, actor: str):
        return self.timeline._prepare_actor_response_part(actor)

    def actor_part_uuid(self, actor: str = "orchestrator", prepare_response: bool = False) -> Optional[str]:
        return self.timeline.actor_part_uuid(actor, prepare_response)

    # TOOL HISTORY API -------------------------------------------------------

    def _new_tool_call_id(self, call_id: Any = None) -> str:
        return self.tool_history._new_tool_call_id(call_id)

    def _persist_tool_call(self, name: str, args: Any, actor: str, call_id: Any = None) -> str:
        return self.tool_history._persist_tool_call(name, args, actor, call_id)

    def _persist_tool_result(
            self, result: Any, actor: str, name: str = "", call_id: Any = None
    ) -> bool:
        return self.tool_history._persist_tool_result(result, actor, name, call_id)

    def _promote_part_tasks(self, part):
        return self.tool_history._promote_part_tasks(part)

    def _promote_actor_tasks(self, actor: str):
        return self.tool_history._promote_actor_tasks(actor)

    def _promote_all_tasks(self):
        return self.tool_history._promote_all_tasks()

    def _append_main_tool_call(self, name: str, args: Any, actor: str, call_id: Any = None) -> Optional[str]:
        return self.tool_history._append_main_tool_call(name, args, actor, call_id)

    def _set_main_tool_result(
            self,
            result: Any,
            actor: str,
            name: str = "",
            call_id: Any = None,
    ) -> bool:
        return self.tool_history._set_main_tool_result(result, actor, name, call_id)

    def record_local_plugin_tool_call(
            self, name: str, args: Any, actor: str = "orchestrator"
    ) -> Optional[str]:
        return self.tool_history.record_local_plugin_tool_call(name, args, actor)

    def record_local_plugin_tool_result(
            self, call_id: Any, name: str, result: Any, actor: str = "orchestrator"
    ):
        return self.tool_history.record_local_plugin_tool_result(call_id, name, result, actor)

    def record_tool_call(self, event: Any, actor: str = "orchestrator"):
        return self.tool_history.record_tool_call(event, actor)

    def record_tool_result(self, event: Any, actor: str = "orchestrator"):
        return self.tool_history.record_tool_result(event, actor)

    def export_tool_calls_to_main_ctx(self):
        return self.tool_history.export_tool_calls_to_main_ctx()

    # CONTEXT / RAG / LLM API -----------------------------------------------

    def has_rag_index(self) -> bool:
        return self.context_api.has_rag_index()

    def prefetch_rag_context(self, query: str) -> str:
        return self.context_api.prefetch_rag_context(query)

    def _rag_prompt_context(self) -> str:
        return self.context_api._rag_prompt_context()

    def _build_runtime_system_context(self) -> str:
        return self.context_api._build_runtime_system_context()

    def _seed_artifact_seen(self):
        return self.artifact_api._seed_artifact_seen()

    def get_llm(
            self,
            stream: bool = False,
            actor_id: str = "orchestrator",
            allow_remote_tools: bool | None = None,
    ):
        return self.context_api.get_llm(stream, actor_id, allow_remote_tools)

    def build_agent(self, name: str, description: str, llm, system_prompt: str, tools):
        return self.context_api.build_agent(name, description, llm, system_prompt, tools)

    def _memory_token_limit(self) -> int:
        return self.context_api._memory_token_limit()

    def _input_image_paths(self) -> List[str]:
        return self.context_api._input_image_paths()

    def _persist_input_images(self):
        return self.context_api._persist_input_images()

    def build_user_message(self, text: str) -> ChatMessage:
        return self.context_api.build_user_message(text)

    def _build_shared_context(self) -> str:
        return self.context_api._build_shared_context()

    # STATUS / SWARM PROJECTION API -----------------------------------------

    def _worker_id(self) -> str:
        return self.status_api._worker_id()

    def _swarm_worker_name(self, name: str, number: int) -> str:
        return self.status_api._swarm_worker_name(name, number)

    def _swarm_worker_number(self, worker_id: str) -> int:
        return self.status_api._swarm_worker_number(worker_id)

    def _swarm_snapshot(self) -> Dict[str, Any]:
        return self.status_api._swarm_snapshot()

    def _swarm_status_text(self) -> str:
        return self.status_api._swarm_status_text()

    def _emit_swarm_status(self, force: bool = False):
        return self.status_api._emit_swarm_status(force)

    def _ensure_swarm_reporter(self):
        return self.status_api._ensure_swarm_reporter()

    async def _swarm_reporter_loop(self):
        return await self.status_api._swarm_reporter_loop()

    def emit_worker_status(self, worker: WorkerState, text: str):
        return self.status_api.emit_worker_status(worker, text)

    def emit_runtime_status(self, key: str, worker: Optional[WorkerState] = None, **kwargs):
        return self.status_api.emit_runtime_status(key, worker, **kwargs)

    # ARTIFACT / ACTOR CONTEXT API ------------------------------------------

    def _provider_id(self) -> str:
        return self.artifact_api._provider_id()

    def collect_llm_artifacts(
            self,
            llm=None,
            worker: Optional[WorkerState] = None,
            response: Any = None,
            actor_id: Optional[str] = None,
    ):
        return self.artifact_api.collect_llm_artifacts(llm, worker, response, actor_id)

    def record_token_usage(self, response: Any, actor_id: str = "orchestrator") -> bool:
        """Add provider-reported usage from one completed LLM request to this turn."""
        return self.usage_api.capture(response, actor_id=actor_id)

    def apply_token_usage(self) -> tuple[int, int, int]:
        """Commit aggregate usage only after the whole Agents v2 turn is complete."""
        return self.usage_api.apply_to_context()

    def collect_artifacts(self, source_ctx: CtxItem, worker: Optional[WorkerState] = None):
        return self.artifact_api.collect_artifacts(source_ctx, worker)

    def register_delivery_files(self, files, worker: Optional[WorkerState] = None):
        return self.artifact_api.register_delivery_files(files, worker)

    def pending_artifacts(self) -> dict:
        return self.artifact_api.pending_artifacts()

    def _make_tool_ctx(self, actor_id: str) -> CtxItem:
        return self.artifact_api._make_tool_ctx(actor_id)

    def _make_worker_ctx(self, worker_id: str) -> CtxItem:
        return self.artifact_api._make_worker_ctx(worker_id)

    # WORKER LIFECYCLE API ---------------------------------------------------

    def _worker_prompt(self, name: str, instruction: str, language: str, system_prompt: str) -> str:
        return self.worker_api._worker_prompt(name, instruction, language, system_prompt)

    async def create_worker(
            self,
            name: str,
            instruction: str,
            language: str,
            system_prompt: str = "",
            task: str = "",
    ) -> str:
        return await self.worker_api.create_worker(name, instruction, language, system_prompt, task)

    async def update_worker(
            self,
            agent_id: str,
            name: Optional[str] = None,
            instruction: Optional[str] = None,
            language: Optional[str] = None,
            system_prompt: Optional[str] = None,
    ) -> str:
        return await self.worker_api.update_worker(agent_id, name, instruction, language, system_prompt)

    async def start_worker(self, agent_id: str, task: str) -> str:
        return await self.worker_api.start_worker(agent_id, task)

    async def _worker_loop(self, state: WorkerState, task: str):
        return await self.worker_api._worker_loop(state, task)

    def _store_worker_output(self, state: WorkerState):
        return self.worker_api._store_worker_output(state)

    # FINAL OUTPUT / MEMORY API ---------------------------------------------

    def _prepare_final_part(self):
        return self.timeline._prepare_final_part()

    def begin_workflow_final_stream(self):
        """Prepare the durable final part and UI barrier for native final deltas."""
        if not self.awaiting_workflow_final_response:
            return self._actor_part("orchestrator", create=False)
        if self.workflow_final_stream_started:
            return self._actor_part("orchestrator", create=False)
        part = self._prepare_final_part()
        self.workflow_final_stream_started = True
        self.emitter.begin_final_stream()
        return part

    def last_orchestrator_output(self) -> str:
        return self.timeline.last_orchestrator_output()

    def primary_response_boundary_pending(self) -> bool:
        return self.timeline.primary_response_boundary_pending()

    def _primary_prose_outputs(self) -> list[str]:
        return self.timeline._primary_prose_outputs()

    def _strip_primary_prose_prefix(self, terminal_text: str) -> str:
        return self.timeline._strip_primary_prose_prefix(terminal_text)

    def resolve_primary_final_output(self, terminal_text: str = "") -> str:
        return self.timeline.resolve_primary_final_output(terminal_text)

    def detach_primary_final_suffix(self, final_answer: str) -> bool:
        return self.timeline.detach_primary_final_suffix(final_answer)

    def mark_current_part_final(self):
        return self.timeline.mark_current_part_final()

    def orchestrator_memory_output(self, final_answer: str = "") -> str:
        return self.timeline.orchestrator_memory_output(final_answer)

    # WORKER CONTROL / WORKFLOW API -----------------------------------------

    async def stop_worker(self, agent_id: str) -> str:
        return await self.worker_api.stop_worker(agent_id)

    async def remove_worker(self, agent_id: str) -> str:
        return await self.worker_api.remove_worker(agent_id)

    async def worker_status(self, agent_id: str) -> str:
        return await self.worker_api.worker_status(agent_id)

    async def worker_list(self) -> str:
        return await self.worker_api.worker_list()

    async def wait_workers(self, agent_ids: str = "", wait_for: str = "all", timeout_seconds: int = 60) -> str:
        return await self.worker_api.wait_workers(agent_ids, wait_for, timeout_seconds)

    async def set_status(self, status: str) -> str:
        return await self.worker_api.set_status(status)

    async def request_workflow_finish(self) -> str:
        """Tool-facing no-argument finalization gate used by managed modes."""
        return await self.worker_api.finish_workflow("")

    async def finish_workflow(self, final_answer: str = "") -> str:
        """Compatibility API for callers/tests that still pass a final hint."""
        return await self.worker_api.finish_workflow(final_answer)

    async def start_swarm(self, agent_count: int) -> str:
        return await self.worker_api.start_swarm(agent_count)

    async def swarm_status(self) -> str:
        return await self.worker_api.swarm_status()

    async def delegate_task(
            self,
            task: str,
            name: str = "Specialist",
            instruction: str = "",
            system_prompt: str = "",
            language: str = "",
    ) -> str:
        return await self.worker_api.delegate_task(task, name, instruction, system_prompt, language)

    # MAIN AGENT TOOL SURFACE API -------------------------------------------

    def primary_agent_tools(self) -> List[FunctionTool]:
        return self.toolset_api.primary_agent_tools()

    def orchestrator_tools(self) -> List[FunctionTool]:
        return self.toolset_api.orchestrator_tools()

    def swarm_tools(self) -> List[FunctionTool]:
        return self.toolset_api.swarm_tools()

    def main_agent_tools(self) -> List[FunctionTool]:
        return self.toolset_api.main_agent_tools()

    # PROMPT API -------------------------------------------------------------

    def compose_agent_system_prompt(
            self,
            base_prompt: str = "",
            additional_system_prompt: Optional[str] = None,
    ) -> str:
        return self.prompt_api.compose_agent_system_prompt(base_prompt, additional_system_prompt)

    def _compose_main_agent_prompt(self, base_prompt: str) -> str:
        return self.prompt_api._compose_main_agent_prompt(base_prompt)

    def primary_agent_prompt(self) -> str:
        return self.prompt_api.primary_agent_prompt()

    def orchestrator_prompt(self) -> str:
        return self.prompt_api.orchestrator_prompt()

    def swarm_prompt(self) -> str:
        return self.prompt_api.swarm_prompt()

    def main_agent_prompt(self) -> str:
        return self.prompt_api.main_agent_prompt()

    async def cleanup(self):
        return await self.worker_api.cleanup()
