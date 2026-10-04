#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.17 15:58:00                  #
# ================================================== #

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from llama_index.core.agent.workflow import AgentStream
from ..state import WorkerState, WorkerStatus
from ..utils import result_text


@dataclass
class WorkerEvents:
    count: int = 0
    types: dict = field(default_factory=dict)


class WorkerExecution:
    """Execute a specialist task without exposing its private answer stream."""

    def __init__(self, runtime, store_output):
        self.runtime = runtime
        self.store_output = store_output

    async def run(self, state: WorkerState, task: str):
        handler = None
        counts = WorkerEvents()
        try:
            run_kwargs = self._prepare_input(state, task)
            handler = state.agent.run(**run_kwargs)
            await self._consume_events(state, handler, counts)
            return await self._complete(state, handler)
        except asyncio.CancelledError:
            if handler is not None:
                try:
                    await handler.cancel_run()
                except asyncio.CancelledError:
                    pass
                except Exception:
                    pass
            state.status = WorkerStatus.STOPPED
            self.runtime.verbose.log("WORKER CANCELLED", state.public_dict(), actor=state.id)
            self.runtime.status.emit("status.agent_v2.stopped", worker=state)
            return ""
        except Exception as exc:
            state.status = WorkerStatus.FAILED
            state.error = str(exc)
            self.runtime.verbose.log("WORKER ERROR", {"error": str(exc), "state": state.public_dict()}, actor=state.id)
            self.runtime.status.emit("status.agent_v2.failed", worker=state)
            self.runtime.window.core.debug.log(exc)
            return ""
        finally:
            self._finalize(state, counts)

    # ========================================
    # Input and model events
    # ========================================

    def _prepare_input(self, state, task):
        shared_hint = ""
        if self.runtime.shared_context_text:
            shared_hint = (
                "\n\nThis workflow has shared user attachments/context. Use shared_context for extracted text/manifest; "
                "image inputs from the current turn are also attached to this task when the selected model supports them."
            )
        worker_input = self.runtime.inputs.message(f"Task from {self.runtime.main_agent_name}:\n{task}{shared_hint}")
        self.runtime.verbose.log("WORKER INPUT", worker_input, actor=state.id)
        run_kwargs = {
            "user_msg": worker_input,
            "memory": state.memory,
            "max_iterations": self.runtime.worker_max_iterations,
            "early_stopping_method": "generate",
        }
        self.runtime.window.core.api.logger.log_input(
            type="llama_index.agent.run",
            provider=str(getattr(self.runtime.model, "provider", "") or ""),
            kwargs=run_kwargs,
            input=worker_input,
            model=getattr(self.runtime.model, "id", None),
            path="worker_agent.run",
            extra={"actor": state.id, "worker_name": state.name},
        )
        return run_kwargs

    async def _consume_events(self, state, handler, counts):
        async for event in handler.stream_events():
            counts.count += 1
            event_name = type(event).__name__
            counts.types[event_name] = counts.types.get(event_name, 0) + 1
            self.runtime.timeline.consume(event, actor=state.id)
            if self.runtime.is_stopped() or state.stop_requested:
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

    # ========================================
    # Result and persistence
    # ========================================

    async def _complete(self, state, handler):
        result = await handler
        self.runtime.artifacts.collect_from_llm(
            getattr(state.agent, "llm", None),
            state,
            response=result,
            actor_id=state.id,
        )
        state.last_result = result_text(result)
        self.runtime.verbose.text("WORKER OUTPUT", state.last_result, actor=state.id)
        if getattr(state.agent, "iteration_limit_reached", False) is True:
            state.status = WorkerStatus.FAILED
            state.error = "Worker iteration limit reached; result may be incomplete."
        elif getattr(state.agent, "stalled", False) is True:
            state.status = WorkerStatus.FAILED
            state.error = "Worker repeated an unchanged checkpoint; task is incomplete."
        elif getattr(state.agent, "completion_outcome", "") in {"blocked", "needs_input"}:
            state.status = WorkerStatus.FAILED
            state.error = "Worker requires assistance: " + state.last_result
        else:
            state.status = WorkerStatus.COMPLETED
        self.runtime.status.emit(
            "status.agent_v2.completed" if state.status == WorkerStatus.COMPLETED else "status.agent_v2.failed",
            worker=state,
        )
        self.runtime.artifacts.collect(state.tool_ctx, state)
        return state.last_result
    def _finalize(self, state, counts):
        event_count, event_types = counts.count, counts.types
        self.runtime.window.core.api.logger.log_output(
            type="llama_index.agent.run",
            provider=str(getattr(self.runtime.model, "provider", "") or ""),
            output=state.last_result,
            chunks=event_count,
            chunk_types=event_types,
            error=state.error or None,
            model=getattr(self.runtime.model, "id", None),
            extra={"actor": state.id, "worker_name": state.name, "status": state.status.value},
        )
        self.runtime.artifacts.collect_from_llm(getattr(state.agent, "llm", None), state)
        self.runtime.artifacts.collect(state.tool_ctx, state)
        self.store_output(state)

