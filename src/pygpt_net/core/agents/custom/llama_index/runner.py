# core/agents/runners/llama_workflow.py

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.27 06:00:00                  #
# ================================================== #

from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from time import perf_counter
from pydantic import ValidationError

from agents import TResponseInputItem
from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem

# Shared (reused) components from OpenAI flow core
from ..logging import Logger, NullLogger
from ..schema import FlowSchema, AgentNode, parse_schema
from ..graph import FlowGraph, build_graph
from ..memory import MemoryManager
from ..router import parse_route_output
from ..debug import ellipsize

# LI-specific utils/factory
from .utils import (
    sanitize_input_items,
    NodeRuntime,
    OptionGetter,
    resolve_node_runtime,
    to_li_chat_messages,
    resolve_llm,
    extract_agent_text,
    strip_role_prefixes,
)
from .factory import AgentFactoryLI

# LlamaIndex Workflow primitives + events
from llama_index.core.workflow import Workflow, Context, StartEvent, StopEvent, Event, step
from llama_index.core.agent.workflow import AgentStream

# App-specific event used as visual separator between agents
from pygpt_net.provider.agents.llama_index.workflow.events import StepEvent

# Cooperative cancellation error used by main runner
from workflows.errors import WorkflowCancelledByUser


@dataclass
class DebugConfig:
    """Config values controlled via get_option(..., 'debug', ...)."""
    log_runtime: bool = True
    log_routes: bool = True
    log_inputs: bool = True
    log_outputs: bool = True
    log_tools: bool = True
    log_llm: bool = True
    log_schema: bool = True
    log_memory_dump: bool = True
    preview_chars: int = 280
    step_timeout_sec: int = 0
    timeit_agent_run: bool = True
    event_echo: bool = True


class FlowStartEvent(StartEvent):
    query: str


class FlowTickEvent(Event):
    """Tick event drives one step of the flow loop."""
    pass


class FlowStopEvent(StopEvent):
    final_answer: str = ""


class DynamicFlowWorkflowLI(Workflow):
    """
    LlamaIndex Workflow mirroring OpenAI dynamic flow:
    - Emits AgentStream header + AgentStream content per step (no token-by-token from single LI agents).
    - Emits StepEvent between agents (your runner uses it to separate UI blocks).
    - Routing via JSON {route, content} (UI sees only content; JSON never leaks).
    - Memory/no-memory with baton policy:
        * first agent w/o memory: initial messages (or query),
        * next w/o memory: only last displayed content as single user message,
        * agent with memory: if empty -> seed from last output (fallback initial); else use its history.
      After step, memory is updated with [user baton, assistant content].
    - Per-agent model/prompt/allow_* via get_option(node_id, ...).
    """

    def __init__(
        self,
        *,
        window,
        logger: Optional[Logger],
        schema: List[Dict[str, Any]],
        initial_messages: Optional[List[TResponseInputItem]],
        preset: Optional[PresetItem],
        default_model: ModelItem,
        option_get: OptionGetter,
        router_stream_mode: str,
        allow_local_tools_default: bool,
        allow_remote_tools_default: bool,
        max_iterations: int,
        llm: Any,
        tools: List[Any],
        stream: bool,
        base_prompt: Optional[str],
        timeout: int = 120,
        verbose: bool = True,
    ):
        super().__init__(timeout=timeout, verbose=verbose)
        self.window = window
        self.logger = logger or NullLogger()

        # Graph/schema
        self.fs: FlowSchema = parse_schema(schema or [])
        self.g: FlowGraph = build_graph(self.fs)
        self.mem = MemoryManager()
        self.factory = AgentFactoryLI(window, self.logger)

        # Options
        self.preset = preset
        self.default_model = default_model
        self.option_get = option_get
        self.router_stream_mode = (router_stream_mode or "off").lower()  # LI: agents don't token-stream
        self.allow_local_tools_default = allow_local_tools_default
        self.allow_remote_tools_default = allow_remote_tools_default
        self.max_iterations = int(max_iterations or 20)

        # Base LLM/tools from app (per-node model override via resolve_llm)
        self.llm_base = llm
        self.tools_base = tools or []
        self.stream = bool(stream)  # kept for symmetry with OpenAI; LI agents don't stream tokens
        self.base_prompt = base_prompt or ""

        # Runtime
        self._on_stop = None
        self._cancelled = False
        self._current_ids: List[str] = []
        self._steps = 0
        self._first_dispatch_done = False
        self._last_plain_output = ""
        self._initial_items = sanitize_input_items(initial_messages or [])
        self._initial_chat = []  # List[ChatMessage]

        # Debug config (read once)
        self.dbg = DebugConfig(
            log_runtime=bool(self.option_get("debug", "log_runtime", True)),
            log_routes=bool(self.option_get("debug", "log_routes", True)),
            log_inputs=bool(self.option_get("debug", "log_inputs", True)),
            log_outputs=bool(self.option_get("debug", "log_outputs", True)),
            log_tools=bool(self.option_get("debug", "log_tools", True)),
            log_llm=bool(self.option_get("debug", "log_llm", True)),
            log_schema=bool(self.option_get("debug", "log_schema", True)),
            log_memory_dump=bool(self.option_get("debug", "log_memory_dump", True)),
            preview_chars=int(self.option_get("debug", "preview_chars", 280)),
            step_timeout_sec=int(self.option_get("debug", "step_timeout_sec", 0)),
            timeit_agent_run=bool(self.option_get("debug", "timeit_agent_run", True)),
            event_echo=bool(self.option_get("debug", "event_echo", True)),
        )

        # One-shot schema/graph dump
        if self.dbg.log_schema:
            try:
                self._dump_schema_debug()
            except Exception as e:
                self.logger.error(f"[debug] schema dump failed: {e}")

    # ============== Debug helpers ==============

    def _dump_schema_debug(self):
        self.logger.info("[debug] ===== Schema/Graph =====")
        self.logger.info(f"[debug] agents={len(self.fs.agents)} memories={len(self.fs.memories)} "
                         f"starts={len(self.fs.starts)} ends={len(self.fs.ends)}")
        self.logger.info(f"[debug] start_targets={self.g.start_targets} end_nodes={self.g.end_nodes}")
        for nid, outs in self.g.adjacency.items():
            self.logger.info(f"[debug] edge {nid} -> {outs}")
        for aid, mem_id in self.g.agent_to_memory.items():
            self.logger.info(f"[debug] agent_to_memory {aid} -> {mem_id}")
        self.logger.info("[debug] ========================")

    def _tool_names(self, tools: List[Any]) -> List[str]:
        names = []
        for t in tools or []:
            n = getattr(getattr(t, "metadata", None), "name", None) or getattr(t, "name", None) or t.__class__.__name__
            names.append(str(n))
        return names

    # ============== Internal helpers ==============

    def _is_stopped(self) -> bool:
        if self._cancelled:
            return True
        if callable(self._on_stop):
            try:
                return bool(self._on_stop())
            except Exception:
                return False
        return False

    async def _emit(self, ctx: Context, ev: Any):
        if self.dbg.event_echo:
            self.logger.debug(f"[event] emit {ev.__class__.__name__}")
        ctx.write_event_to_stream(ev)

    async def _emit_agent_text(self, ctx: Context, text: str, agent_name: str = "Agent"):
        """
        Emit AgentStream(delta=text) robustly. If env requires extra fields,
        fall back to extended AgentStream.
        """
        try:
            if self.dbg.event_echo:
                self.logger.debug(f"[event] AgentStream delta len={len(text or '')}")
            ctx.write_event_to_stream(AgentStream(delta=text or ""))
        except ValidationError:
            if self.dbg.event_echo:
                self.logger.debug("[event] AgentStream ValidationError -> using extended fields")
            ctx.write_event_to_stream(
                AgentStream(
                    delta=text or "",
                    response=text or "",
                    current_agent_name=agent_name or "Agent",
                    tool_calls=[],
                    raw={},
                )
            )

    async def _emit_header(self, ctx: Context, name: str):
        # Lightweight header to ensure agent name is known before tokens.
        await self._emit_agent_text(ctx, "", agent_name=name)

    async def _emit_step_sep(self, ctx: Context, node_id: str):
        try:
            a = self.fs.agents.get(node_id)
            friendly_name = (a.name if a and a.name else node_id)
            await self._emit(
                ctx,
                StepEvent(
                    name="next",
                    index=self._steps,
                    total=self.max_iterations,
                    meta={
                        "node": node_id,
                        "agent_name": friendly_name,  # pass current agent display name
                    },
                ),
            )
        except Exception as e:
            self.logger.error(f"[event] StepEvent emit failed: {e}")

    def _resolve_node_runtime(self, node: AgentNode) -> NodeRuntime:
        return resolve_node_runtime(
            window=self.window,
            node=node,
            option_get=self.option_get,
            default_model=self.default_model,
            base_prompt=self.base_prompt,
            schema_allow_local=node.allow_local_tools,
            schema_allow_remote=node.allow_remote_tools,
            default_allow_local=self.allow_local_tools_default,
            default_allow_remote=self.allow_remote_tools_default,
        )

    def _build_input_for_node(self, node_id: str) -> tuple[str, list, str]:
        """
        Return (user_msg_text, chat_history_msgs, source_tag) using baton/memory policy.
        """
        mem_id = self.g.agent_to_memory.get(node_id)
        mem_state = self.mem.get(mem_id) if mem_id else None

        # memory with history
        if mem_state and mem_state.items:
            base_items = list(mem_state.items[:-1]) if len(mem_state.items) >= 1 else []
            if self._last_plain_output.strip():
                user_msg_text = self._last_plain_output
            else:
                last_ass = mem_state.items[-1] if isinstance(mem_state.items[-1], dict) else {}
                if isinstance(last_ass.get("content"), str):
                    user_msg_text = last_ass.get("content", "")
                elif isinstance(last_ass.get("content"), list) and last_ass["content"]:
                    user_msg_text = last_ass["content"][0].get("text", "")
                else:
                    user_msg_text = ""
            chat_history_msgs = to_li_chat_messages(base_items)
            return user_msg_text, chat_history_msgs, "memory:existing_to_user_baton"

        # memory empty
        if mem_state:
            if self._last_plain_output.strip():
                return self._last_plain_output, [], "memory:seed_from_last_output"
            else:
                chat_hist = self._initial_chat[:-1] if self._initial_chat else []
                user_msg = self._initial_chat[-1].content if self._initial_chat else ""
                return user_msg, chat_hist, "memory:seed_from_initial"

        # no memory
        if not self._first_dispatch_done:
            chat_hist = self._initial_chat[:-1] if self._initial_chat else []
            user_msg = self._initial_chat[-1].content if self._initial_chat else ""
            return user_msg, chat_hist, "no-mem:first_initial"
        else:
            user_msg = self._last_plain_output if self._last_plain_output.strip() else (
                self._initial_chat[-1].content if self._initial_chat else ""
            )
            return user_msg, [], "no-mem:last_output"

    async def _update_memory_after_step(self, node_id: str, user_msg_text: str, display_text: str):
        """
        Update per-node memory after a step, storing baton user message and assistant output.
        """
        mem_id = self.g.agent_to_memory.get(node_id)
        mem_state = self.mem.get(mem_id) if mem_id else None
        if not mem_state:
            if self.dbg.log_memory_dump:
                self.logger.debug(f"[memory] no memory for {node_id}; skip update.")
            return
        before_len = len(mem_state.items)
        base_items = list(mem_state.items[:-1]) if mem_state.items else []
        new_mem = (base_items or []) + [
            {"role": "user", "content": user_msg_text},
            {"role": "assistant", "content": [{"type": "output_text", "text": display_text}]},
        ]
        mem_state.set_from(new_mem, None)
        after_len = len(mem_state.items)
        if self.dbg.log_memory_dump:
            self.logger.debug(
                f"[memory] {node_id} updated mem_id={mem_id} len {before_len} -> {after_len} "
                f"user='{ellipsize(user_msg_text, self.dbg.preview_chars)}' "
                f"assist='{ellipsize(display_text, self.dbg.preview_chars)}'"
            )

    # ============== Workflow steps ==============

    def run(self, query: str, ctx: Optional[Context] = None, memory: Any = None, verbose: bool = False, on_stop=None):
        """Entry point used by LlamaWorkflow runner."""
        self._on_stop = on_stop

        # Build initial chat once
        if self._initial_items:
            self._initial_chat = to_li_chat_messages(self._initial_items)
            if self.dbg.log_inputs:
                prev = ellipsize(str(self._initial_items), self.dbg.preview_chars)
                self.logger.debug(f"[debug] initial_items count={len(self._initial_items)} preview={prev}")
        else:
            from llama_index.core.llms import ChatMessage, MessageRole
            self._initial_chat = [ChatMessage(role=MessageRole.USER, content=query or "")]
            if self.dbg.log_inputs:
                self.logger.debug(f"[debug] initial from query='{ellipsize(query, self.dbg.preview_chars)}'")

        # Pick START
        if self.g.start_targets:
            self._current_ids = [self.g.start_targets[0]]
            self.logger.info(f"[step] START -> {self._current_ids[0]}")
        else:
            default_agent = self.g.pick_default_start_agent()
            if default_agent is None:
                self.logger.error("[step] No START and no agents in schema.")
                return super().run(ctx=ctx, start_event=FlowStartEvent(query=query or ""))
            self._current_ids = [default_agent]
            self.logger.info(f"[step] START (auto lowest-id) -> {default_agent}")

        self._steps = 0
        self._first_dispatch_done = False
        self._last_plain_output = ""

        return super().run(ctx=ctx, start_event=FlowStartEvent(query=query or ""))

    @step
    async def start_step(self, ctx: Context, ev: FlowStartEvent) -> FlowTickEvent | FlowStopEvent:
        self.logger.debug("[step] start_step")
        if not self._current_ids:
            await self._emit_agent_text(ctx, "Flow has no start and no agents.\n", agent_name="Flow")
            return FlowStopEvent(final_answer="")
        return FlowTickEvent()

    @step
    async def loop_step(self, ctx: Context, ev: FlowTickEvent) -> FlowTickEvent | FlowStopEvent:
        # Cooperative stop
        if self._is_stopped():
            self.logger.info("[step] loop_step: stopped() -> cancelling")
            raise WorkflowCancelledByUser()

        # Termination conditions
        if not self._current_ids or (self._steps >= self.max_iterations > 0):
            self.logger.info(f"[step] loop_step: done (ids={self._current_ids}, steps={self._steps})")
            return FlowStopEvent(final_answer=self._last_plain_output or "")

        current_id = self._current_ids[0]
        self._steps += 1
        self.logger.debug(f"[step] loop_step#{self._steps} current_id={current_id}")

        # Reached END?
        if current_id in self.fs.ends:
            self.logger.info(f"[step] loop_step: reached END {current_id}")
            return FlowStopEvent(final_answer=self._last_plain_output or "")

        # If unknown id: jump to END if any
        if current_id not in self.fs.agents:
            self.logger.warning(f"[step] loop_step: {current_id} not an agent; jumping to END if any.")
            end_id = self.g.end_nodes[0] if self.g.end_nodes else None
            self._current_ids = [end_id] if end_id else []
            return FlowTickEvent() if self._current_ids else FlowStopEvent(final_answer=self._last_plain_output or "")

        node: AgentNode = self.fs.agents[current_id]

        # IMPORTANT: emit StepEvent also for the very first agent step.
        await self._emit_step_sep(ctx, current_id)
        await self._emit_header(ctx, node.name or current_id)

        # Resolve runtime + per-node LLM/tools
        node_rt = self._resolve_node_runtime(node)
        if self.dbg.log_runtime:
            self.logger.debug(
                f"[runtime] model={getattr(node_rt.model,'name',str(node_rt.model))} "
                f"allow_local={node_rt.allow_local_tools} allow_remote={node_rt.allow_remote_tools} "
                f"instructions='{ellipsize(node_rt.instructions, self.dbg.preview_chars)}'"
                f" role='{ellipsize(node_rt.role or '', self.dbg.preview_chars)}'"
            )

        llm_node = resolve_llm(self.window, node_rt.model, self.llm_base, self.stream)
        if self.dbg.log_llm:
            self.logger.debug(f"[llm] using={llm_node.__class__.__name__} id={getattr(llm_node,'model',None) or getattr(llm_node,'_model',None)}")

        tools_node = self.tools_base if (node_rt.allow_local_tools or node_rt.allow_remote_tools) else []
        if self.dbg.log_tools:
            self.logger.debug(f"[tools] count={len(tools_node)} names={self._tool_names(tools_node)}")

        # Build input (baton/memory)
        user_msg_text, chat_history_msgs, src = self._build_input_for_node(current_id)
        if self.dbg.log_inputs:
            self.logger.debug(
                f"[input] src={src} chat_hist={len(chat_history_msgs)} "
                f"user='{ellipsize(user_msg_text, self.dbg.preview_chars)}'"
            )

        # Build agent
        allowed_routes_now = list(node.outputs or [])
        friendly_map = {rid: self.fs.agents.get(rid).name or rid for rid in allowed_routes_now if rid in self.fs.agents}

        built = self.factory.build(
            node=node,
            node_runtime=node_rt,
            llm=llm_node,
            tools=tools_node,
            friendly_map=friendly_map,
            chat_history=chat_history_msgs,
            max_iterations=self.max_iterations,
        )
        agent = built.instance
        multi_output = built.multi_output
        allowed_routes = built.allowed_routes

        if self.dbg.log_routes:
            self.logger.debug(f"[routing] multi_output={multi_output} routes={allowed_routes} mode={self.router_stream_mode}")

        display_text = ""
        next_id: Optional[str] = None

        # Execute (single LI agent doesn't token-stream; Workflow emits blocks)
        try:
            t0 = perf_counter()
            if self.dbg.step_timeout_sec > 0:
                ret = await asyncio.wait_for(agent.run(user_msg=user_msg_text), timeout=self.dbg.step_timeout_sec)
            else:
                ret = await agent.run(user_msg=user_msg_text)
            dt_ms = (perf_counter() - t0) * 1000.0
            if self.dbg.timeit_agent_run:
                self.logger.debug(f"[time] agent.run took {dt_ms:.1f} ms")
        except asyncio.TimeoutError:
            self.logger.error(f"[error] agent.run timeout after {self.dbg.step_timeout_sec}s on node={current_id}")
            ret = None
        except Exception as e:
            self.logger.error(f"[error] agent.run failed on node={current_id}: {e}")
            ret = None

        # Extract and sanitize text
        raw_text = extract_agent_text(ret) if ret is not None else ""
        raw_text_clean = strip_role_prefixes(raw_text)

        if self.dbg.log_outputs:
            self.logger.debug(f"[out.raw] len={len(raw_text)} preview='{ellipsize(raw_text, self.dbg.preview_chars)}'")
            self.logger.debug(f"[out.cln] len={len(raw_text_clean)} preview='{ellipsize(raw_text_clean, self.dbg.preview_chars)}'")

        if multi_output:
            decision = parse_route_output(raw_text_clean or "", allowed_routes)
            display_text = decision.content or ""
            if display_text:
                await self._emit_agent_text(ctx, display_text, agent_name=(node.name or current_id))
            await self._update_memory_after_step(current_id, user_msg_text, display_text)
            next_id = decision.route if decision.valid else (allowed_routes[0] if allowed_routes else None)
            if self.dbg.log_routes:
                self.logger.debug(
                    f"[route] node={current_id} valid={decision.valid} next={next_id} content_len={len(display_text)}"
                )
        else:
            display_text = raw_text_clean or ""
            if display_text:
                await self._emit_agent_text(ctx, display_text, agent_name=(node.name or current_id))
            await self._update_memory_after_step(current_id, user_msg_text, display_text)
            outs = self.g.get_next(current_id)
            next_id = outs[0] if outs else self.g.first_connected_end(current_id)
            if self.dbg.log_routes:
                self.logger.debug(f"[route] node={current_id} next={next_id} (first edge or END)")

        if self.dbg.log_outputs:
            self.logger.debug(f"[output] preview='{ellipsize(display_text, self.dbg.preview_chars)}'")

        # Update baton and next
        self._first_dispatch_done = True
        self._last_plain_output = display_text

        if isinstance(next_id, str) and next_id.lower() == "end":
            end_id = self.g.first_connected_end(current_id) or (self.g.end_nodes[0] if self.g.end_nodes else None)
            self._current_ids = [end_id] if end_id else []
            if not self._current_ids:
                self.logger.info("[step] next=END (no concrete END node); stopping now.")
                return FlowStopEvent(final_answer=self._last_plain_output or "")
        elif next_id:
            self._current_ids = [next_id]
        else:
            end_id = self.g.first_connected_end(current_id)
            if end_id:
                self._current_ids = [end_id]
            else:
                self._current_ids = []
                self.logger.info("[step] no next, no END; stopping.")
                return FlowStopEvent(final_answer=self._last_plain_output or "")

        return FlowTickEvent()