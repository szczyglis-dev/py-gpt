#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.26 17:00:00                  #
# ================================================== #

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from time import perf_counter

from agents import Runner, TResponseInputItem
from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem
from pygpt_net.provider.api.openai.agents.response import StreamHandler

from .logging import Logger, NullLogger
from .schema import FlowSchema, AgentNode, parse_schema
from .graph import FlowGraph, build_graph
from .memory import MemoryManager
from .factory import AgentFactory
from .router import parse_route_output
from .utils import (
    sanitize_input_items,
    extract_text_output,
    patch_last_assistant_output,
    OptionGetter,
    resolve_node_runtime,
)
from .router_streamer import DelayedRouterStreamer, RealtimeRouterStreamer
from .debug import items_preview, ellipsize


@dataclass
class FlowResult:
    ctx: CtxItem
    final_output: str
    last_response_id: Optional[str]


@dataclass
class DebugConfig:
    log_runtime: bool = True
    log_routes: bool = True
    log_inputs: bool = False
    log_outputs: bool = False
    preview_chars: int = 280


class FlowOrchestrator:
    """
    Orchestrates dynamic multi-agent flow based on NodeEditor schema.
    UI semantics follow "bot-to-bot" and supports router stream modes: off/delayed/realtime.
    Memory/no-memory input policy:
      - First agent (in the whole flow) gets full initial messages from the app.
      - Next agent WITHOUT memory gets only last step's displayed content as a single 'user' message.
      - Agent WITH memory:
          * if memory has items -> use them;
          * if memory empty -> seed input from last displayed content (or initial messages as fallback).
    """
    def __init__(self, window, logger: Optional[Logger] = None) -> None:
        self.window = window
        self.logger = logger or NullLogger()

    async def run_flow(
        self,
        schema: List[Dict[str, Any]],
        messages: List[TResponseInputItem],
        ctx: CtxItem,
        bridge: ConnectionContext,
        agent_kwargs: Dict[str, Any],
        preset: Optional[PresetItem],
        model: ModelItem,
        stream: bool,
        use_partial_ctx: bool,
        base_prompt: Optional[str],
        allow_local_tools_default: bool,
        allow_remote_tools_default: bool,
        function_tools: List[dict],
        trace_id: Optional[str],
        max_iterations: int = 20,
        router_stream_mode: str = "off",  # "off" | "delayed" | "realtime"
        option_get: Optional[OptionGetter] = None,
    ) -> FlowResult:
        fs: FlowSchema = parse_schema(schema)
        g: FlowGraph = build_graph(fs)
        mem = MemoryManager()
        factory = AgentFactory(self.window, self.logger)
        option_get = option_get or (lambda s, k, d=None: d)

        # Debug config
        dbg = DebugConfig(
            log_runtime=bool(option_get("debug", "log_runtime", True)),
            log_routes=bool(option_get("debug", "log_routes", True)),
            log_inputs=bool(option_get("debug", "log_inputs", True)),
            log_outputs=bool(option_get("debug", "log_outputs", True)),
            preview_chars=int(option_get("debug", "preview_chars", 280)),
        )

        # Entry
        if g.start_targets:
            current_ids: List[str] = [g.start_targets[0]]
            self.logger.info(f"Using explicit START -> {current_ids[0]}")
        else:
            default_agent = g.pick_default_start_agent()
            if default_agent is None:
                self.logger.error("No START and no agents in schema.")
                return FlowResult(ctx=ctx, final_output="", last_response_id=None)
            current_ids = [default_agent]
            self.logger.info(f"No START found, using lowest-id agent: {default_agent}")

        # State
        final_output = ""
        last_response_id: Optional[str] = None

        # Initial messages for the very first agent in flow
        initial_messages: List[TResponseInputItem] = sanitize_input_items(list(messages or []))
        first_dispatch_done: bool = False
        last_plain_output: str = ""  # what was displayed to UI in the previous step

        steps = 0

        # Shared stream handler (bot-to-bot style)
        handler = StreamHandler(self.window, bridge)
        begin = True

        while current_ids and (steps < max_iterations or max_iterations == 0) and not bridge.stopped():
            step_start = perf_counter()
            current_id = current_ids[0]
            steps += 1

            # END node
            if current_id in fs.ends:
                self.logger.info(f"Reached END node: {current_id}")
                break

            # Validate agent
            if current_id not in fs.agents:
                self.logger.warning(f"Next id {current_id} is not an agent; stopping or jumping to END.")
                if g.end_nodes:
                    current_ids = [g.end_nodes[0]]
                    continue
                break

            node: AgentNode = fs.agents[current_id]
            self.logger.debug(f"[step {steps}] agent_id={node.id} name={node.name} outs={node.outputs}")

            # Resolve per-node runtime
            node_rt = resolve_node_runtime(
                window=self.window,
                node=node,
                option_get=option_get,
                default_model=model,
                base_prompt=base_prompt,
                schema_allow_local=node.allow_local_tools,
                schema_allow_remote=node.allow_remote_tools,
                default_allow_local=allow_local_tools_default,
                default_allow_remote=allow_remote_tools_default,
            )

            if dbg.log_runtime:
                instr_preview = ellipsize(node_rt.instructions, dbg.preview_chars)
                self.logger.debug(
                    f"[runtime] model={getattr(node_rt.model,'name',str(node_rt.model))} "
                    f"allow_local={node_rt.allow_local_tools} allow_remote={node_rt.allow_remote_tools} "
                    f"instructions='{instr_preview}'"
                    f" role='{node_rt.role}'"
                )

            # Memory selection and INPUT BUILD (memory-first policy)
            mem_id = g.agent_to_memory.get(current_id)
            mem_state = mem.get(mem_id) if mem_id else None
            if dbg.log_runtime:
                mem_info = f"{mem_id} (len={len(mem_state.items)})" if mem_state and mem_state.items else (mem_id or "-")
                self.logger.debug(f"[memory] attached={bool(mem_id)} mem_id={mem_info}")

            input_items: List[TResponseInputItem]
            input_source = ""

            if mem_state and not mem_state.is_empty():
                # memory present and already has history
                input_items = list(mem_state.items)
                input_source = "memory:existing"
            elif mem_state:
                # memory present but empty -> seed from last output or initial messages
                if last_plain_output and last_plain_output.strip():
                    input_items = [{"role": "user", "content": last_plain_output}]
                    input_source = "memory:seeded_from_last"
                else:
                    input_items = list(initial_messages)
                    input_source = "memory:seeded_from_initial"
            else:
                # no memory -> first agent gets initial messages; others get only last output
                if not first_dispatch_done:
                    input_items = list(initial_messages)
                    input_source = "no-mem:initial"
                else:
                    if last_plain_output and last_plain_output.strip():
                        input_items = [{"role": "user", "content": last_plain_output}]
                        input_source = "no-mem:last_output"
                    else:
                        input_items = list(initial_messages)
                        input_source = "no-mem:fallback_initial"

            prepared_items = sanitize_input_items(input_items)

            if dbg.log_inputs:
                self.logger.debug(f"[input] source={input_source} items={len(prepared_items)} "
                                  f"preview={items_preview(prepared_items, dbg.preview_chars)}")

            # Build agent with per-node runtime
            built = factory.build(
                node=node,
                node_runtime=node_rt,
                preset=preset,
                function_tools=function_tools,
                force_router=False,  # auto on multi-output
                friendly_map={aid: a.name or aid for aid, a in fs.agents.items()},
                handoffs_enabled=True,
                context=agent_kwargs.get("context"),
            )
            agent = built.instance
            multi_output = built.multi_output
            allowed_routes = built.allowed_routes

            if dbg.log_runtime and multi_output:
                self.logger.debug(f"[routing] multi_output=True routes={allowed_routes} mode={router_stream_mode}")

            # Prepare run kwargs
            run_kwargs: Dict[str, Any] = {
                "input": prepared_items,
                "max_turns": int(agent_kwargs.get("max_iterations", max_iterations)),
            }
            if trace_id:
                run_kwargs["trace_id"] = trace_id

            # Header for UI
            ctx.set_agent_name(agent.name)
            # title = f"\n\n**{built.name}**\n\n"
            # ctx.stream = title
            bridge.on_step(ctx, begin)
            begin = False
            handler.begin = begin
            # if not use_partial_ctx:
                # handler.to_buffer(title)

            display_text = ""  # what we show to UI for this step
            next_id: Optional[str] = None

            # --- EXECUTION ---
            if stream and not multi_output:
                # Full token streaming (single-output agent)
                result = Runner.run_streamed(agent, **run_kwargs)
                handler.reset()

                async for event in result.stream_events():
                    if bridge.stopped():
                        result.cancel()
                        bridge.on_stop(ctx)
                        break
                    display_text, last_response_id = handler.handle(event, ctx)

                # Prepare next inputs from result for memory update (if any)
                input_items_next = result.to_input_list()
                input_items_next = sanitize_input_items(input_items_next)

                # Update memory only if attached
                if mem_state:
                    mem_state.update_from_result(input_items_next, last_response_id)

                # Route: first edge or END
                outs = g.get_next(current_id)
                next_id = outs[0] if outs else g.first_connected_end(current_id)

            else:
                # Multi-output or non-stream
                if multi_output:
                    mode = (router_stream_mode or "off").lower()
                    if stream and mode == "realtime":
                        # Realtime router streaming: stream content as tokens arrive
                        result = Runner.run_streamed(agent, **run_kwargs)
                        rts = RealtimeRouterStreamer(
                            window=self.window,
                            bridge=bridge,
                            handler=handler if not use_partial_ctx else None,
                            buffer_to_handler=(not use_partial_ctx),
                            logger=self.logger,
                        )
                        rts.reset()

                        async for event in result.stream_events():
                            if bridge.stopped():
                                result.cancel()
                                bridge.on_stop(ctx)
                                break
                            rts.handle_event(event, ctx)
                            if rts.last_response_id:
                                last_response_id = rts.last_response_id

                        raw_text = rts.buffer or ""
                        decision = parse_route_output(raw_text, allowed_routes)
                        display_text = decision.content or ""

                        # Prepare next inputs from streamed result, patch assistant content -> content
                        input_items_next = result.to_input_list()
                        input_items_next = patch_last_assistant_output(input_items_next, decision.content or "")

                        # Update memory if attached
                        if mem_state:
                            mem_state.update_from_result(input_items_next, last_response_id)

                        # Route decision
                        if decision.valid:
                            next_id = decision.route
                        else:
                            if dbg.log_routes:
                                self.logger.warning("[router-realtime] Invalid JSON; fallback to first route.")
                            next_id = allowed_routes[0] if allowed_routes else None

                    elif stream and mode == "delayed":
                        # Delayed router streaming: collect tokens silently, reveal once
                        result = Runner.run_streamed(agent, **run_kwargs)
                        delayed = DelayedRouterStreamer(self.window, bridge)
                        delayed.reset()

                        async for event in result.stream_events():
                            if bridge.stopped():
                                result.cancel()
                                bridge.on_stop(ctx)
                                break
                            _, rid = delayed.handle_event(event, ctx)
                            if rid:
                                last_response_id = rid

                        raw_text = delayed.buffer or ""
                        decision = parse_route_output(raw_text, allowed_routes)
                        display_text = decision.content or ""
                        if display_text:
                            ctx.stream = display_text
                            bridge.on_step(ctx, False)
                            if not use_partial_ctx:
                                handler.to_buffer(display_text)

                        input_items_next = result.to_input_list()
                        input_items_next = patch_last_assistant_output(input_items_next, display_text)

                        if mem_state:
                            mem_state.update_from_result(input_items_next, last_response_id)

                        if decision.valid:
                            next_id = decision.route
                        else:
                            if dbg.log_routes:
                                self.logger.warning(f"[router-delayed] Invalid JSON: {decision.error}; fallback first route.")
                            next_id = allowed_routes[0] if allowed_routes else None
                    else:
                        # No streaming for router: run to completion, then emit only content
                        result = await Runner.run(agent, **run_kwargs)
                        last_response_id = getattr(result, "last_response_id", None)
                        raw_text = extract_text_output(result)
                        decision = parse_route_output(raw_text, allowed_routes)
                        display_text = decision.content or ""
                        if display_text:
                            ctx.stream = display_text
                            bridge.on_step(ctx, False)
                            if not use_partial_ctx:
                                handler.to_buffer(display_text)

                        input_items_next = result.to_input_list()
                        input_items_next = patch_last_assistant_output(input_items_next, display_text)

                        if mem_state:
                            mem_state.update_from_result(input_items_next, last_response_id)

                        if decision.valid:
                            next_id = decision.route
                        else:
                            if dbg.log_routes:
                                self.logger.warning(f"[router-off] Invalid JSON: {decision.error}; fallback first route.")
                            next_id = allowed_routes[0] if allowed_routes else None
                else:
                    # Single-output, non-stream path
                    result = await Runner.run(agent, **run_kwargs)
                    last_response_id = getattr(result, "last_response_id", None)
                    raw_text = extract_text_output(result)
                    display_text = raw_text or ""
                    if display_text:
                        ctx.stream = display_text
                        bridge.on_step(ctx, False)
                        if not use_partial_ctx:
                            handler.to_buffer(display_text)

                    input_items_next = result.to_input_list()
                    input_items_next = sanitize_input_items(input_items_next)

                    if mem_state:
                        mem_state.update_from_result(input_items_next, last_response_id)

                    outs = g.get_next(current_id)
                    next_id = outs[0] if outs else g.first_connected_end(current_id)

            # DEBUG: output + route
            if dbg.log_outputs:
                self.logger.debug(f"[output] preview='{ellipsize(display_text, dbg.preview_chars)}' "
                                  f"last_response_id={last_response_id}")

            if dbg.log_routes:
                self.logger.debug(f"[route] current={current_id} -> next={next_id} "
                                  f"(end_connected={g.first_connected_end(current_id)})")

            # Mark dispatch and remember last plain output (for next no-memory agent)
            first_dispatch_done = True
            last_plain_output = display_text
            final_output = display_text

            # Resolve next id / END
            if isinstance(next_id, str) and next_id.lower() == "end":
                end_id = g.first_connected_end(current_id) or (g.end_nodes[0] if g.end_nodes else None)
                current_ids = [end_id] if end_id else []
            elif next_id:
                current_ids = [next_id]
            else:
                end_id = g.first_connected_end(current_id)
                current_ids = [end_id] if end_id else []

            # UI separation after each agent step
            is_end = True if not current_ids else (current_ids[0] in fs.ends)
            if use_partial_ctx:
                ctx = bridge.on_next_ctx(
                    ctx=ctx,
                    input="",
                    output=display_text,
                    response_id=last_response_id or "",
                    finish=is_end,
                    stream=True,
                )
                handler.new()
            else:
                bridge.on_next(ctx)

            # set next agent name if not at the end
            if current_ids and current_ids[0] in fs.agents:
                ctx.set_agent_name(fs.agents[current_ids[0]].name)

            # Step duration
            dur = perf_counter() - step_start
            self.logger.debug(f"[step {steps}] duration={dur:.3f}s")

        if bridge.stopped():
            bridge.on_stop(ctx)

        self.logger.info(f"Flow finished. steps={steps} final_len={len(final_output)}")
        return FlowResult(ctx=ctx, final_output=final_output, last_response_id=last_response_id)