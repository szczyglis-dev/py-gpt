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


class TurnFinalization:
    """Commit artifacts, diagnostic state and turn totals after execution."""

    def __init__(self, runtime, emitter):
        self.runtime = runtime
        self.emitter = emitter

    async def finish(self, prepared, events, stop_task):
        self._log_execution(events)
        if stop_task is not None:
            stop_task.cancel()
            await asyncio.gather(stop_task, return_exceptions=True)
        self._collect_provider_artifacts(prepared)
        self._capture_debug_snapshot()
        await self.runtime.workers.cleanup()
        self.runtime.tool_history.export()
        self._commit_usage()
        self._finish_emission()

    # ========================================
    # Diagnostics
    # ========================================

    def _log_execution(self, events):
        runtime = self.runtime
        event_count, event_types = events.count, events.types
        runtime.window.core.api.logger.log_output(
            type="llama_index.agent.run",
            provider=str(getattr(runtime.model, "provider", "") or ""),
            output=runtime.final_answer or runtime.timeline.last_output(),
            chunks=event_count,
            chunk_types=event_types,
            model=getattr(runtime.model, "id", None),
            extra={
                "actor": "orchestrator",
                "finished": runtime.finished,
                "stopped": runtime.is_stopped(),
                "agent_mode": runtime.agent_mode.value,
            },
        )
        runtime.verbose.log("RUNNER FINALIZE BEGIN", {
            "finished": runtime.finished,
            "stopped": runtime.is_stopped(),
            "agent_mode": runtime.agent_mode.value,
        })

    def _capture_debug_snapshot(self):
        runtime = self.runtime
        # cleanup() intentionally clears live worker/swarm maps. Preserve a
        # debug-only snapshot so the inspector still shows the completed flow.
        runtime.debug_cleanup_snapshot = {
            "finished": bool(runtime.finished),
            "stopped": bool(runtime.is_stopped()),
            "final_answer": str(runtime.final_answer or ""),
            "workers": {
                wid: {
                    **state.public_dict(include_result=True),
                    "instruction": state.instruction,
                    "system_prompt": state.system_prompt,
                    "stop_requested": state.stop_requested,
                    "task_done": bool(state.task.done()) if state.task is not None else None,
                    "task_cancelled": bool(state.task.cancelled()) if state.task is not None else None,
                }
                for wid, state in list(runtime.workers.states.items())
            },
            "swarm_worker_numbers": dict(runtime.workers.numbers),
            "worker_parent_parts": {
                str(k): getattr(v, "uuid", None)
                for k, v in runtime.workers.parent_parts.items()
            },
            "stored_worker_context_runs": list(runtime.workers.stored_context_runs),
        }

    # ========================================
    # Artifacts and usage
    # ========================================

    def _collect_provider_artifacts(self, prepared):
        runtime = self.runtime
        main_agent, llm = prepared.agent, prepared.llm
        # Provider-native hosted tools bypass local plugin CtxItems. Drain
        # both the LLM owned by the workflow agent and the originally created
        # adapter before runtime cleanup. Usually they are the same object; the
        # second call is a no-op after the first drain.
        agent_llm = getattr(main_agent, "llm", None)
        runtime.artifacts.collect_from_llm(agent_llm or llm, actor_id="orchestrator")
        if agent_llm is not None and agent_llm is not llm:
            runtime.artifacts.collect_from_llm(llm, actor_id="orchestrator")

    def _commit_usage(self):
        runtime = self.runtime
        # The footer/status token summary represents one complete Agents v2
        # user turn: user input -> every orchestrator/worker LLM pass -> final
        # response. Commit it only now so no partial/intermediate usage leaks
        # into the UI while the workflow is still running.
        if runtime.finished and str(runtime.final_answer or runtime.timeline.last_output()).strip():
            turn_usage = runtime.usage.apply_to_context()
            runtime.verbose.log("TURN TOKEN USAGE", {
                "input_tokens": turn_usage[0],
                "output_tokens": turn_usage[1],
                "total_tokens": turn_usage[2],
            })

    def _finish_emission(self):
        runtime, emitter = self.runtime, self.emitter
        emitter.clear_status()
        final_part = runtime.timeline.part("orchestrator", create=False)
        final_part_uuid = getattr(final_part, "uuid", None) if final_part is not None else None
        emitter.finish(
            runtime.final_answer,
            part_uuid=final_part_uuid,
            artifacts=runtime.artifacts.pending(),
        )
        runtime.verbose.log("RUNNER FINALIZE END", {
            "final_answer": runtime.final_answer,
            "agent_mode": runtime.agent_mode.value,
        })
