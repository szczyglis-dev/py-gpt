#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.26 21:15:00                  #
# ================================================== #

from __future__ import annotations

import asyncio
from llama_index.core.agent.workflow import AgentStream, ToolCall, ToolCallResult
from ..autonomy import AgentCheckpoint


class TurnEvents:
    """Forward model output while respecting tool/checkpoint and final-answer boundaries."""

    def __init__(self, runtime, emitter):
        self.runtime = runtime
        self.emitter = emitter
        self.count = 0
        self.types = {}

    async def consume(self, handler):
        runtime = self.runtime
        emitter = self.emitter
        post_tool_stream = False
        async for event in handler.stream_events():
            self.count += 1
            event_name = type(event).__name__
            self.types[event_name] = self.types.get(event_name, 0) + 1
            runtime.debug_event_count = self.count
            runtime.debug_event_types = dict(self.types)
            # In managed modes workflow_finish only validates/arms the final
            # response. The first non-empty AgentStream after that tool result
            # is the real authoritative final answer, so prepare its durable
            # part/UI barrier *before* timeline processing sees the delta.
            if (isinstance(event, AgentStream)
                    and getattr(event, "delta", None)
                    and runtime.workflow.awaiting_final_response
                    and not runtime.workflow.final_stream_started):
                runtime.timeline.begin_final_stream()

            runtime.timeline.consume(event, actor="orchestrator")
            if runtime.is_stopped():
                try:
                    await handler.cancel_run()
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
                break

            # Orchestrator and Swarm modes use workflow_finish as the
            # authoritative finalizer. Primary Agent finalizes from its
            # terminal response instead.
            if runtime.uses_workflow_finish and runtime.finished:
                try:
                    await handler.cancel_run()
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
                break

            if isinstance(event, AgentCheckpoint):
                emitter.mark_block_boundary()
                runtime.timeline.close_segment()
                runtime.timeline.needs_new_part["orchestrator"] = True
                post_tool_stream = True
                continue

            if isinstance(event, ToolCall):
                # A tool call closes the current model pass. Keep normal
                # provider-sized streaming for any prose before the call.
                emitter.mark_block_boundary()
                post_tool_stream = False
                continue

            if isinstance(event, ToolCallResult):
                # The response after a tool result starts a new model pass.
                # Some LlamaIndex/provider combinations expose that pass as
                # one large AgentStream.delta even when streaming is enabled.
                # Arm the emitter's incremental fallback for this segment so
                # it is painted progressively just like a materialized final.
                emitter.mark_block_boundary()
                post_tool_stream = True
                continue

            if isinstance(event, AgentStream) and getattr(event, "delta", None):
                await emitter.append_streamed(
                    event.delta,
                    part_uuid=runtime.timeline.part_uuid("orchestrator"),
                    ensure_incremental=post_tool_stream,
                )

    async def watch_stop(self, handler):
        runtime = self.runtime
        while not runtime.finished:
            if runtime.is_stopped():
                runtime.verbose.log("STOP REQUESTED", {"source": "kernel"})
                for state in list(runtime.workers.states.values()):
                    if state.task and not state.task.done():
                        state.stop_requested = True
                        state.task.cancel()
                try:
                    await handler.cancel_run()
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
                return
            await asyncio.sleep(0.2)

