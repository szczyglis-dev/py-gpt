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

import json
from .state import WorkerStatus


class WorkflowControl:
    """Declare swarm scope and validate readiness for the final assistant pass."""

    def __init__(self, runtime):
        self.runtime = runtime
        # Completion first arms an ordinary LLM pass, then streams its answer.
        self.final_requested = False
        self.final_stream_started = False
        self.final_hint = ""

    @property
    def awaiting_final_response(self) -> bool:
        """True between accepted workflow completion and the final LLM pass."""
        return bool(self.final_requested and not self.runtime.finished)

    # ========================================
    # Workflow and swarm control
    # ========================================

    async def request_finish(self, outcome: str = "completed", evidence: str = "") -> str:
        """Validate completion without materializing the answer in a tool call."""
        return await self.finish("", outcome=outcome, evidence=evidence)

    async def finish(self, final_answer: str = "", outcome: str = "completed", evidence: str = "") -> str:
        """Legacy compatibility finalizer; not exposed to the Primary Agent."""
        self.runtime.verbose.text("WORKFLOW FINISH REQUEST", final_answer)
        rejection = self._check_finalization_state()
        if rejection is not None:
            return rejection

        if outcome not in {"completed", "blocked", "needs_input"}:
            return json.dumps({"error": "Invalid outcome; use completed, blocked or needs_input."})
        if outcome != "completed":
            if not evidence.strip():
                return json.dumps({"error": "Explain the blocker or required user decision in evidence."})
            for worker in list(self.runtime.workers.states.values()):
                if worker.busy:
                    await self.runtime.workers.stop(worker.id)

        rejection = self._check_swarm_completion(outcome)
        if rejection is not None:
            return rejection
        rejection = self._check_worker_completion(outcome)
        if rejection is not None:
            return rejection

        # Do not finalize from a tool argument. A function/tool call is only
        # dispatched after its complete JSON payload has been generated, which
        # necessarily turns a long final_answer argument into a non-streamed wait.
        # Instead this tool only validates/arms finalization; the next ordinary
        # assistant pass is the authoritative answer and arrives as native
        # AgentStream deltas. Keep an optional legacy hint so older/custom prompts
        # that still pass final_answer can recover if the final pass is empty.
        self.runtime.workflow_outcome = outcome
        self.runtime.workflow_evidence = evidence
        self.final_requested = True
        self.final_stream_started = False
        self.final_hint = str(final_answer or "").strip()
        self.runtime.verbose.log("WORKFLOW FINAL RESPONSE ARMED", {
            "legacy_hint_chars": len(self.final_hint),
        })
        self.runtime.emitter.clear_status()
        return (
            "Finalization accepted. Return the complete user-facing final answer now as normal assistant text. "
            "Do not call workflow_finish again and do not call any other tool."
        )

    async def declare_swarm(self, agent_count: int) -> str:
        """Declare the exact user-requested Swarm size before worker creation."""
        if not self.runtime.is_swarm_mode:
            return json.dumps({"error": "swarm_start is available only in Swarm mode."})
        try:
            count = int(agent_count)
        except (TypeError, ValueError):
            count = 0
        if count < 1:
            return json.dumps({
                "error": "agent_count must be a positive integer.",
                "action": "Ask the user for a concrete swarm size if it was not specified.",
            }, ensure_ascii=False)
        if self.runtime.workers.created_count:
            return json.dumps({
                "error": "Swarm size must be declared before creating workers.",
                "created": self.runtime.workers.created_count,
            }, ensure_ascii=False)
        if self.runtime.workers.expected_count is not None and self.runtime.workers.expected_count != count:
            return json.dumps({
                "error": "Swarm size is already declared for this run.",
                "declared": self.runtime.workers.expected_count,
                "requested": count,
            }, ensure_ascii=False)
        self.runtime.workers.expected_count = count
        self.runtime.verbose.log("SWARM START", {"agent_count": count})
        self.runtime.status.start_reporter()
        self.runtime.status.emit_swarm(force=True)
        return json.dumps({
            "mode": "swarm",
            "declared": count,
            "created": self.runtime.workers.created_count,
            "launched": self.runtime.workers.launched_count,
            "message": f"Swarm declared with {count} agents. Create and start exactly {count} numbered workers.",
        }, ensure_ascii=False)

    async def status(self) -> str:
        """Emit and return the current aggregate Swarm snapshot."""
        if not self.runtime.is_swarm_mode:
            return json.dumps({"error": "swarm_status is available only in Swarm mode."})
        payload = self.runtime.status.snapshot()
        self.runtime.status.emit_swarm(force=True)
        self.runtime.verbose.log("SWARM STATUS", payload)
        return json.dumps(payload, ensure_ascii=False, default=str)

    # ========================================
    # Completion gates
    # ========================================

    def _check_finalization_state(self):
        if self.runtime.finished:
            self.runtime.verbose.log("WORKFLOW FINISH REJECTED", "Workflow is already finished.")
            return "Workflow is already finished."
        if self.final_requested:
            payload = {
                "error": "Workflow finalization is already accepted.",
                "action": "Return the complete final answer now as normal assistant text without calling any more tools.",
            }
            self.runtime.verbose.log("WORKFLOW FINISH REJECTED", payload)
            return json.dumps(payload, ensure_ascii=False)


    def _check_swarm_completion(self, outcome):
        if self.runtime.is_swarm_mode and outcome == "completed":
            if self.runtime.workers.expected_count is None:
                payload = {
                    "error": "Swarm workflow cannot finish before its size is declared.",
                    "action": "Call swarm_start(agent_count=N), launch exactly N workers, then finish the workflow.",
                }
                self.runtime.verbose.log("WORKFLOW FINISH REJECTED", payload)
                return json.dumps(payload, ensure_ascii=False)
            if self.runtime.workers.created_count != self.runtime.workers.expected_count:
                payload = {
                    "error": "Swarm workflow cannot finish before the declared number of workers has been launched.",
                    "declared": self.runtime.workers.expected_count,
                    "created": self.runtime.workers.created_count,
                    "remaining": max(0, self.runtime.workers.expected_count - self.runtime.workers.created_count),
                    "action": "Create/start the remaining workers before calling workflow_finish again.",
                }
                self.runtime.verbose.log("WORKFLOW FINISH REJECTED", payload)
                return json.dumps(payload, ensure_ascii=False)
            if self.runtime.workers.launched_count != self.runtime.workers.expected_count:
                payload = {
                    "error": "Swarm workflow cannot finish before every declared worker has actually been started.",
                    "declared": self.runtime.workers.expected_count,
                    "launched": self.runtime.workers.launched_count,
                    "remaining": max(0, self.runtime.workers.expected_count - self.runtime.workers.launched_count),
                    "action": "Start the remaining created workers before calling workflow_finish again.",
                }
                self.runtime.verbose.log("WORKFLOW FINISH REJECTED", payload)
                return json.dumps(payload, ensure_ascii=False)


    def _check_worker_completion(self, outcome):
        running = [w for w in self.runtime.workers.states.values() if w.busy]
        never_started = [
            w for w in self.runtime.workers.states.values()
            if w.status == WorkerStatus.CREATED and w.generation == 0
        ]
        if outcome == "completed" and (running or never_started):
            payload = {
                "error": "Workflow cannot finish while workers are still running or were created but never started.",
                "running": [w.public_dict(include_result=False) for w in running],
                "never_started": [w.public_dict(include_result=False) for w in never_started],
                "action": "Wait for/stop running workers and run or remove unused workers, then call workflow_finish again.",
            }
            self.runtime.verbose.log("WORKFLOW FINISH REJECTED", payload)
            return json.dumps(payload, ensure_ascii=False, default=str)

