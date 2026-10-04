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
import json
import uuid
from typing import Optional


from .state import WorkerState, WorkerStatus
from .communication import WorkerCommunication
from .worker_definition import WorkerDefinition
from .worker_history import WorkerHistory
from .execution.worker import WorkerExecution


class WorkerRuntime:
    """Worker lifecycle and delegation runtime shared by all top-level modes."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.expected_count = None
        self.created_count = 0
        self.launched_count = 0
        self.numbers = {}
        # Attach worker output to the primary partial that launched the run.
        self.parent_parts = {}
        self.stored_context_runs = set()
        self.sequence = 0
        self.states = {}
        self.communication = WorkerCommunication(runtime)
        self.definition = WorkerDefinition(runtime, self.communication)
        self.history = WorkerHistory(runtime)
        self.execution = WorkerExecution(runtime, self.history.save)

    # ========================================
    # Worker identity
    # ========================================

    def next_id(self) -> str:
        self.sequence += 1
        return f"w{self.sequence:02d}_{uuid.uuid4().hex[:6]}"

    def number(self, worker_id: str) -> int:
        if worker_id in self.numbers:
            return self.numbers[worker_id]
        value = str(worker_id or "")
        head = value.split("_", 1)[0]
        if head.startswith("w"):
            try:
                return max(1, int(head[1:]))
            except (TypeError, ValueError):
                pass
        return 1

    # ========================================
    # Worker definitions
    # ========================================

    async def create(
            self,
            name: str,
            instruction: str,
            language: str,
            system_prompt: str = "",
            task: str = "",
    ) -> str:
        if self.runtime.is_stopped() or self.runtime.finished or self.runtime.workflow.final_requested:
            return json.dumps({"error": "Workflow is stopping or finalizing."})
        self.runtime.verbose.log("AGENT CREATE REQUEST", {
            "name": name,
            "instruction": instruction,
            "language": language,
            "system_prompt": system_prompt,
            "task": task,
        })
        if self.runtime.is_swarm_mode:
            if self.expected_count is None:
                result = json.dumps({
                    "error": "Swarm size is not declared.",
                    "action": "Call swarm_start(agent_count=N) before creating workers.",
                }, ensure_ascii=False)
                self.runtime.verbose.log("AGENT CREATE REJECTED", result)
                return result
            if self.created_count >= self.expected_count:
                result = json.dumps({
                    "error": "Declared swarm size has already been reached.",
                    "declared": self.expected_count,
                    "created": self.created_count,
                }, ensure_ascii=False)
                self.runtime.verbose.log("AGENT CREATE REJECTED", result)
                return result
        else:
            max_workers = self.runtime.max_workers_configured
            if max_workers > 0 and len(self.states) >= max_workers:
                result = json.dumps({"error": f"Maximum workers reached ({max_workers})."})
                self.runtime.verbose.log("AGENT CREATE REJECTED", result)
                return result
        raw_name = (name or "Worker").strip()[:80]
        instruction = (instruction or "General specialist").strip()
        language = str(language or "").strip()
        if not language:
            return json.dumps({
                "error": "Worker language is required.",
                "action": "Pass the language of the current end-user request (for example: Polish, English, German).",
            }, ensure_ascii=False)
        state, swarm_number = self.definition.create(name=raw_name, instruction=instruction,
                                                     language=language, system_prompt=system_prompt)
        wid = state.id
        self.states[wid] = state
        if self.runtime.is_swarm_mode:
            self.numbers[wid] = swarm_number
            self.created_count += 1
            self.runtime.status.emit_swarm(force=self.created_count == self.expected_count)
        self.runtime.verbose.log("AGENT CREATED", state.public_dict(), actor=wid)
        if task:
            await self.start(wid, task)
        result = json.dumps(state.public_dict(), ensure_ascii=False, default=str)
        self.runtime.verbose.log("AGENT CREATE RESULT", state.public_dict(), actor=wid)
        return result

    async def update(
            self,
            agent_id: str,
            name: Optional[str] = None,
            instruction: Optional[str] = None,
            language: Optional[str] = None,
            system_prompt: Optional[str] = None,
    ) -> str:
        self.runtime.verbose.log("AGENT UPDATE REQUEST", {
            "agent_id": agent_id,
            "name": name,
            "instruction": instruction,
            "language": language,
            "system_prompt": system_prompt,
        }, actor=agent_id)
        state = self.states.get(agent_id)
        if state is None or state.status == WorkerStatus.REMOVED:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        if state.busy:
            return json.dumps({"error": "Worker is running; stop/wait before updating it.", "id": agent_id})
        self.definition.update(state, name, instruction, language, system_prompt)
        state.status = WorkerStatus.CREATED
        state.progress = ""
        state.error = ""
        result = state.public_dict()
        self.runtime.verbose.log("AGENT UPDATED", result, actor=agent_id)
        return json.dumps(result, ensure_ascii=False, default=str)

    # ========================================
    # Worker execution
    # ========================================

    async def start(self, agent_id: str, task: str) -> str:
        if self.runtime.is_stopped() or self.runtime.finished or self.runtime.workflow.final_requested:
            return json.dumps({"error": "Workflow is stopping or finalizing."})
        self.runtime.verbose.log("AGENT RUN REQUEST", {"agent_id": agent_id, "task": task}, actor=agent_id)
        state = self.states.get(agent_id)
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
        if self.runtime.is_swarm_mode and state.generation == 0:
            self.launched_count += 1
        state.generation += 1
        # Worker conversation state remains in-memory only. Remember the current
        # orchestrator partial as the durable origin for this run; worker tool
        # task rows and the final worker_context record are attached there.
        self.parent_parts[state.id] = self.runtime.timeline.part("orchestrator", create=True)
        self.runtime.status.emit("status.agent_v2.starting", worker=state)
        if self.runtime.is_swarm_mode:
            self.runtime.status.start_reporter()
            self.runtime.status.emit_swarm(force=False)
        self.runtime.verbose.log("AGENT RUNNING", state.public_dict(include_result=False), actor=agent_id)
        state.task = asyncio.create_task(
            self.execution.run(state, state.current_task),
            name=f"agents-v2:{agent_id}",
        )
        result = state.public_dict(include_result=False)
        self.runtime.verbose.log("AGENT RUN RESULT", result, actor=agent_id)
        return json.dumps(result, ensure_ascii=False, default=str)

    async def stop(self, agent_id: str) -> str:
        self.runtime.verbose.log("AGENT STOP REQUEST", {"agent_id": agent_id}, actor=agent_id)
        state = self.states.get(agent_id)
        if state is None:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        state.stop_requested = True
        if state.task and not state.task.done():
            state.status = WorkerStatus.STOPPING
            state.task.cancel()
            await asyncio.gather(state.task, return_exceptions=True)
        if state.status != WorkerStatus.REMOVED:
            state.status = WorkerStatus.STOPPED
        result = state.public_dict()
        self.runtime.verbose.log("AGENT STOPPED", result, actor=agent_id)
        return json.dumps(result, ensure_ascii=False, default=str)

    async def remove(self, agent_id: str) -> str:
        self.runtime.verbose.log("AGENT REMOVE REQUEST", {"agent_id": agent_id}, actor=agent_id)
        state = self.states.get(agent_id)
        if state is None:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        if state.busy:
            await self.stop(agent_id)
        if self.runtime.is_swarm_mode and state.generation == 0 and self.created_count > 0:
            # An unlaunched slot can be replaced while still honoring the exact
            # user-requested swarm size. Launched agents always count permanently.
            self.created_count -= 1
        state.status = WorkerStatus.REMOVED
        self.communication.remove_peer(agent_id)
        self.states.pop(agent_id, None)
        self.numbers.pop(agent_id, None)
        self.parent_parts.pop(agent_id, None)
        result = {"id": agent_id, "removed": True}
        self.runtime.verbose.log("AGENT REMOVED", result, actor=agent_id)
        return json.dumps(result)

    # ========================================
    # Worker status and waiting
    # ========================================

    async def status(self, agent_id: str) -> str:
        state = self.states.get(agent_id)
        if state is None:
            return json.dumps({"error": "Worker not found", "id": agent_id})
        result = state.public_dict()
        self.runtime.verbose.log("AGENT STATUS", result, actor=agent_id)
        return json.dumps(result, ensure_ascii=False, default=str)

    async def list(self) -> str:
        result = [w.public_dict(include_result=False) for w in self.states.values()]
        self.runtime.verbose.log("AGENT LIST", result)
        return json.dumps(result, ensure_ascii=False, default=str)

    async def wait(self, agent_ids: str = "", wait_for: str = "all", timeout_seconds: int = 60) -> str:
        self.runtime.verbose.log("AGENT WAIT REQUEST", {
            "agent_ids": agent_ids,
            "wait_for": wait_for,
            "timeout_seconds": timeout_seconds,
        })
        ids = [x.strip() for x in str(agent_ids or "").split(",") if x.strip()]
        if not ids:
            ids = list(self.states.keys())
        states = [self.states[i] for i in ids if i in self.states]
        missing = [i for i in ids if i not in self.states]
        if not states:
            return json.dumps({"error": "No matching workers", "missing": missing})

        tasks = [s.task for s in states if s.task is not None and not s.task.done()]
        mode = str(wait_for or "all").lower()
        if mode not in ("all", "any"):
            mode = "all"
        if tasks:
            waiting_names = ", ".join(s.name for s in states if s.task is not None and not s.task.done())
            self.runtime.status.emit("status.agent_v2.waiting", name=waiting_names)
            timeout = max(1, min(int(timeout_seconds or 60), 600))
            try:
                await asyncio.wait(
                    tasks,
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED if mode == "any" else asyncio.ALL_COMPLETED,
                )
            except Exception as exc:
                self.runtime.window.core.debug.log(exc)
        selected_ids = {s.id for s in states}
        payload = {
            "workers": [s.public_dict() for s in states],
            "missing": missing,
            "recent_status_events": [
                event for event in self.runtime.status.events if event.get("agent_id") in selected_ids
            ][-64:],
        }
        self.runtime.verbose.log("AGENT WAIT RESULT", payload)
        return json.dumps(payload, ensure_ascii=False, default=str)

    # ========================================
    # Cleanup
    # ========================================

    async def cleanup(self):
        self.runtime.verbose.log("CLEANUP BEGIN", [w.public_dict() for w in self.states.values()])
        await self.runtime.status.stop_reporter()
        for state in list(self.states.values()):
            if state.task and not state.task.done():
                state.stop_requested = True
                state.task.cancel()
        pending = [s.task for s in self.states.values() if s.task is not None and not s.task.done()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        self.communication.clear()
        self.states.clear()
        self.numbers.clear()
        self.parent_parts.clear()
        self.stored_context_runs.clear()
        self.runtime.verbose.log("CLEANUP END", {"workers": 0, "finished": self.runtime.finished})
