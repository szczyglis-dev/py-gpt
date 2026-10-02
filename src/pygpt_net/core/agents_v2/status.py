#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.13 15:14:00                  #
# ================================================== #

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from .state import WorkerState, WorkerStatus
from .utils import short_status_text, translated_status


class RuntimeStatus:
    """Status/event projection, including Swarm aggregate reporting."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.events = []
        self.sequence = 0
        self.reporter_task = None
        self.last_report_at = 0.0

    def show_tool(self, tool_name: str) -> bool:
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


    def worker_name(self, name: str, number: int) -> str:
        """Return a stable numbered identity for a Swarm worker."""
        base = str(name or "Worker").strip() or "Worker"
        number = max(1, int(number or 1))
        lowered = base.lower()
        known_prefixes = (
            f"agent {number}", f"agent #{number}", f"#{number}",
            f"worker {number}", f"worker #{number}",
        )
        if lowered.startswith(known_prefixes):
            return base[:80]
        prefix = f"Agent {number} — "
        return (prefix + base)[:80]

    def snapshot(self) -> Dict[str, Any]:
        workers = list(self.runtime.workers.states.values())
        running = [w for w in workers if w.status in (WorkerStatus.RUNNING, WorkerStatus.STOPPING)]
        completed = [w for w in workers if w.status == WorkerStatus.COMPLETED]
        failed = [w for w in workers if w.status == WorkerStatus.FAILED]
        stopped = [w for w in workers if w.status in (WorkerStatus.STOPPED, WorkerStatus.REMOVED)]
        pending = [w for w in workers if w.status == WorkerStatus.CREATED and w.generation == 0]
        activities = []
        for worker in workers:
            activity = worker.progress or worker.current_task or worker.status.value
            activities.append({
                "id": worker.id,
                "name": worker.name,
                "status": worker.status.value,
                "activity": short_status_text(activity, 180),
            })
        return {
            "mode": "swarm",
            "declared": self.runtime.workers.expected_count,
            "created": self.runtime.workers.created_count,
            "launched": self.runtime.workers.launched_count,
            "running": len(running),
            "completed": len(completed),
            "failed": len(failed),
            "stopped": len(stopped),
            "pending": len(pending),
            "activities": activities,
        }

    def _swarm_text(self) -> str:
        snapshot = self.snapshot()
        active = [
            item for item in snapshot["activities"]
            if item.get("status") in (WorkerStatus.RUNNING.value, WorkerStatus.STOPPING.value)
        ]
        shown = active[:6]
        single_live_status = bool(self.runtime.window.core.config.get(
            "agent.v2.single_status.live",
            True,
        ))
        activity_separator = "\n" if single_live_status else "; "
        activity_text = activity_separator.join(
            f"[{item['name']}] {short_status_text(item.get('activity'), 64)}"
            for item in shown
        )
        if len(active) > len(shown):
            activity_text += (activity_separator if activity_text else "") + f"+{len(active) - len(shown)}"
        if activity_text:
            # In single-live-status mode the aggregate remains one replaceable
            # status row, but each active worker is rendered on its own line.
            # The legacy accumulating timeline keeps the old inline `` | `` form.
            activity_text = ("\n\n" if single_live_status else " | ") + activity_text
        template = translated_status(
            "status.agent_v2.swarm.summary",
            declared=snapshot["declared"] or 0,
            created=snapshot["created"],
            launched=snapshot["launched"],
            running=snapshot["running"],
            completed=snapshot["completed"],
            failed=snapshot["failed"],
            stopped=snapshot["stopped"],
            pending=snapshot["pending"],
            activities=activity_text,
        )
        # If the locale does not yet know the new key, keep the status useful.
        if template == "status.agent_v2.swarm.summary":
            template = (
                f"Swarm: {snapshot['running']}/{snapshot['declared'] or 0} running, "
                f"{snapshot['launched']} launched, {snapshot['completed']} completed, "
                f"{snapshot['failed']} failed, {snapshot['stopped']} stopped{activity_text}"
            )
        return template

    def emit_swarm(self, force: bool = False):
        if not self.runtime.is_swarm_mode or self.runtime.workers.expected_count is None:
            return
        now = time.monotonic()
        if not force and now - self.last_report_at < self.runtime.SWARM_STATUS_INTERVAL:
            return
        self.last_report_at = now
        text = self._swarm_text()
        self.runtime.verbose.log("SWARM STATUS AUTO", self.snapshot())
        hold_for = (
            self.runtime.SWARM_STATUS_MIN_VISIBLE
            if bool(self.runtime.window.core.config.get("agent.v2.single_status.live", True))
            else 0.0
        )
        self.runtime.emitter.status(
            text,
            source="orchestrator",
            hold_for=hold_for,
        )

    async def stop_reporter(self):
        """Cancel and await the aggregate reporter before workers are cleared."""
        if self.reporter_task is not None:
            self.reporter_task.cancel()
            await asyncio.gather(self.reporter_task, return_exceptions=True)
            self.reporter_task = None

    def start_reporter(self):
        if not self.runtime.is_swarm_mode or self.runtime.finished:
            return
        if self.reporter_task is not None and not self.reporter_task.done():
            return
        try:
            self.reporter_task = asyncio.create_task(
                self._reporter_loop(),
                name="agents-v2:swarm-status",
            )
        except RuntimeError:
            # No running loop (for example in isolated unit construction). The
            # explicit swarm_status tool still provides the same snapshot.
            self.reporter_task = None

    async def _reporter_loop(self):
        try:
            while self.runtime.is_swarm_mode and not self.runtime.finished and not self.runtime.is_stopped():
                await asyncio.sleep(self.runtime.SWARM_STATUS_INTERVAL)
                if self.runtime.finished or self.runtime.is_stopped():
                    break
                snapshot = self.snapshot()
                if snapshot["running"] or snapshot["created"] < (snapshot["declared"] or 0):
                    self.emit_swarm(force=True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.runtime.window.core.debug.log(exc)

    def worker(self, worker: WorkerState, text: str):
        worker.progress = str(text or "").strip()[:240]
        if worker.progress:
            self.sequence += 1
            self.events.append({
                "seq": self.sequence,
                "agent_id": worker.id,
                "agent_name": worker.name,
                "status": worker.progress,
            })
            # Bound memory even for very chatty workers. The current state remains
            # retained for diagnostics while this delegated specialist is running.
            if len(self.events) > 256:
                del self.events[:-256]
            display = worker.progress
            if (
                    self.runtime.is_orchestrator_mode
                    or self.runtime.is_swarm_mode
                    or self.runtime.SHOW_AGENT_NAME_IN_STATUS
            ) and worker.name:
                display = f"[{worker.name}] {display}"
            self.runtime.verbose.log("WORKER STATUS", {
                "id": worker.id,
                "name": worker.name,
                "state": worker.status.value,
                "progress": worker.progress,
                "generation": worker.generation,
            }, actor=worker.id)
            self.runtime.emitter.status(display, source=worker.id)
            if self.runtime.is_swarm_mode:
                self.emit_swarm(force=worker.terminal)

    def emit(self, key: str, worker: Optional[WorkerState] = None, **kwargs):
        text = translated_status(key, **kwargs)
        if worker is not None:
            self.worker(worker, text)
        else:
            self.runtime.verbose.log(self.runtime.main_event("STATUS"), {"key": key, "status": text, "args": kwargs})
            self.runtime.emitter.status(text, source="orchestrator")

    async def update(self, status: str) -> str:
        value = str(status or "").strip()
        self.runtime.verbose.log("WORKFLOW STATUS", {"status": value})
        self.runtime.emitter.status(value, source="orchestrator")
        return "Status updated."
