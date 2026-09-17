#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.17 23:05:00                  #
# ================================================== #

from __future__ import annotations

import copy
import json
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


class AgentWorkflow:
    """Runtime-only, human-readable Agents v2 workflow state.

    The verbose logger feeds this component with already-redacted, JSON-safe
    events.  It deliberately keeps no database state: every top-level Agents v2
    run starts with a clean view and Clear view only affects this live monitor.
    """

    ROOT_ID = "orchestrator"
    MAX_EVENTS_PER_AGENT = 500
    MAX_EVENTS_TOTAL = 1000
    MAX_TEXT_CHARS = 16 * 1024
    SEMANTIC_TOOLS = {
        "agent_create", "agent_run", "agent_stop", "agent_remove",
        "workflow_status", "workflow_finish", "report_status", "task_complete",
    }

    def __init__(self, window=None):
        self.window = window
        self._lock = threading.RLock()
        self._event_seq = 0
        self._aliases: Dict[str, str] = {}
        self._pending_agents: Dict[str, Dict[str, Any]] = {}
        self._tool_events: Dict[Tuple[str, str], int] = {}
        self._tool_events_by_name: Dict[Tuple[str, str], int] = {}
        self._state = self._empty_state()

    @staticmethod
    def _time() -> str:
        return datetime.now().strftime("%H:%M:%S")

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    @classmethod
    def _text(cls, value: Any) -> str:
        """Bound monitor previews without altering actual tool results or logs."""
        if value is None:
            return ""
        if isinstance(value, str):
            text = value[:cls.MAX_TEXT_CHARS + 1]
        else:
            # Stop encoding structured results once the preview budget is filled.
            chunks = []
            size = 0
            try:
                for chunk in json.JSONEncoder(ensure_ascii=False, default=str).iterencode(value):
                    chunk = chunk[:max(0, cls.MAX_TEXT_CHARS + 1 - size)]
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > cls.MAX_TEXT_CHARS:
                        break
                text = "".join(chunks)
            except Exception:
                text = str(value)[:cls.MAX_TEXT_CHARS + 1]
        if len(text) > cls.MAX_TEXT_CHARS:
            return text[:cls.MAX_TEXT_CHARS] + "\n[… preview truncated …]"
        return text

    @staticmethod
    def _get(data: Any, *keys: str, default=None):
        if not isinstance(data, dict):
            return default
        for key in keys:
            if key in data and data[key] not in (None, ""):
                return data[key]
        return default

    @classmethod
    def _tool_name(cls, data: Any) -> str:
        return str(cls._get(data, "tool_name", "name", "tool", "cmd", default="tool") or "tool")

    @classmethod
    def _tool_args(cls, data: Any):
        if isinstance(data, dict) and "params" in data and "cmd" in data:
            return data.get("params")
        return cls._get(
            data,
            "tool_kwargs", "tool_args", "arguments", "kwargs", "args", "raw_arguments",
            default={},
        )

    @classmethod
    def _tool_output(cls, data: Any):
        value = cls._get(data, "tool_output", "output", "result", "response", "ctx_results", default="")
        if isinstance(value, dict) and "content" in value:
            return value.get("content")
        return value

    @classmethod
    def _call_id(cls, data: Any) -> str:
        return str(cls._get(data, "tool_id", "tool_call_id", "call_id", "id", default="") or "")

    def _empty_state(self) -> Dict[str, Any]:
        return {
            "run_id": "",
            "started_at": "",
            "mode": "",
            "model": "",
            "provider": "",
            "preset": "",
            "root_id": self.ROOT_ID,
            "order": [],
            "agents": {},
        }

    def clear(self):
        with self._lock:
            self._event_seq = 0
            self._aliases.clear()
            self._pending_agents.clear()
            self._tool_events.clear()
            self._tool_events_by_name.clear()
            self._state = self._empty_state()
        self._publish()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state)

    def _publish(self):
        controller = getattr(getattr(self.window, "controller", None), "agent_workflow", None)
        if controller is None:
            return
        try:
            is_visible = getattr(controller, "is_visible", None)
            if callable(is_visible) and not is_visible():
                return
            controller.publish()
        except Exception:
            pass

    def _resolve_actor(self, actor: Any) -> str:
        raw = str(actor or self.ROOT_ID).strip()
        key = raw.casefold()
        if key in self._aliases:
            return self._aliases[key]
        if raw in self._state["agents"]:
            return raw
        if key in {"orchestrator", "primary agent", "primary_agent", "swarm"}:
            return self.ROOT_ID
        return raw

    def _register_alias(self, alias: Any, agent_id: str):
        text = str(alias or "").strip()
        if text:
            self._aliases[text.casefold()] = agent_id

    def _ensure_agent(
            self,
            agent_id: str,
            name: str = "",
            parent_id: Optional[str] = None,
            role: str = "worker",
    ) -> Dict[str, Any]:
        agent_id = str(agent_id or self.ROOT_ID)
        agent = self._state["agents"].get(agent_id)
        if agent is None:
            agent = {
                "id": agent_id,
                "name": str(name or agent_id),
                "parent_id": parent_id,
                "role": role,
                "status": "created",
                "turn": 1 if agent_id == self.ROOT_ID else 0,
                "elapsed_ms": 0,
                "active_since_ms": None,
                "ended_at_ms": None,
                "details": {
                    "system_prompt": "",
                    "input": "",
                    "instruction": "",
                    "task": "",
                    "language": "",
                    "description": "",
                },
                "events": [],
            }
            self._state["agents"][agent_id] = agent
            self._state["order"].append(agent_id)
        elif name:
            agent["name"] = str(name)
        if parent_id is not None:
            agent["parent_id"] = parent_id
        if role:
            agent["role"] = role
        self._register_alias(agent_id, agent_id)
        self._register_alias(agent.get("name"), agent_id)
        return agent

    def _start_timer(self, agent: Dict[str, Any]):
        """Start or resume one agent wall-clock timer."""
        if agent.get("active_since_ms") is None:
            agent["active_since_ms"] = self._now_ms()
        agent["ended_at_ms"] = None

    def _stop_timer(self, agent: Dict[str, Any]):
        """Freeze one agent timer while preserving elapsed time across reruns."""
        now = self._now_ms()
        active_since = agent.get("active_since_ms")
        if active_since is not None:
            try:
                delta = max(0, now - int(active_since))
            except (TypeError, ValueError):
                delta = 0
            try:
                elapsed = max(0, int(agent.get("elapsed_ms") or 0))
            except (TypeError, ValueError):
                elapsed = 0
            agent["elapsed_ms"] = elapsed + delta
            agent["active_since_ms"] = None
            agent["ended_at_ms"] = now
        elif agent.get("ended_at_ms") is None:
            agent["ended_at_ms"] = now

    def _sync_timer(self, agent: Dict[str, Any], status: str):
        state = str(status or "").strip().lower()
        if state == "running":
            self._start_timer(agent)
        elif state in {"completed", "failed", "stopped", "removed", "cancelled"}:
            self._stop_timer(agent)

    def _begin_run(self, run_id: str, data: Any):
        self._event_seq = 0
        self._aliases.clear()
        self._pending_agents.clear()
        self._tool_events.clear()
        self._tool_events_by_name.clear()
        self._state = self._empty_state()
        self._state.update({
            "run_id": str(run_id or ""),
            "started_at": self._time(),
            "mode": str(self._get(data, "agent_mode", default="") or ""),
            "model": str(self._get(data, "model", default="") or ""),
            "provider": str(self._get(data, "provider", default="") or ""),
            "preset": str(self._get(data, "preset", default="") or ""),
        })
        root_name = str(self._get(data, "agent_name", default="") or "")
        if not root_name:
            mode = self._state["mode"]
            root_name = "Orchestrator" if mode in {"orchestrator", "swarm"} else "Primary Agent"
        role = "orchestrator" if self._state["mode"] in {"orchestrator", "swarm"} else "primary"
        root = self._ensure_agent(self.ROOT_ID, root_name, parent_id=None, role=role)
        root["status"] = "running"
        root["turn"] = 1
        self._start_timer(root)
        root["details"]["description"] = str(self._get(data, "agent_mode", default="") or "")
        self._register_alias(root_name, self.ROOT_ID)
        self._register_alias("Primary Agent", self.ROOT_ID)
        self._register_alias("Orchestrator", self.ROOT_ID)

    def _ensure_actor(self, actor_id: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Ensure an event actor without overwriting its resolved display name/role."""
        actor_id = str(actor_id or self.ROOT_ID)
        existing = self._state["agents"].get(actor_id)
        if existing is not None:
            return existing
        if actor_id == self.ROOT_ID:
            return self._ensure_agent(actor_id, parent_id=None, role="orchestrator")
        return self._ensure_agent(
            actor_id,
            parent_id=parent_id if parent_id is not None else self.ROOT_ID,
            role="worker",
        )

    def _next_event_id(self) -> int:
        self._event_seq += 1
        return self._event_seq

    def _add_event(
            self,
            actor_id: str,
            kind: str,
            message: str,
            *,
            turn: Optional[int] = None,
            data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        agent = self._ensure_actor(actor_id)
        if turn is None:
            turn = max(1, int(agent.get("turn") or 0))
        event = {
            "id": self._next_event_id(),
            "time": self._time(),
            "turn": max(1, int(turn or 1)),
            "kind": str(kind or "event"),
            "message": self._text(message),
        }
        if data:
            event.update(data)
        agent["events"].append(event)
        if len(agent["events"]) > self.MAX_EVENTS_PER_AGENT:
            del agent["events"][:-self.MAX_EVENTS_PER_AGENT]
        agents = self._state["agents"].values()
        excess = sum(len(a["events"]) for a in agents) - self.MAX_EVENTS_TOTAL
        if excess > 0:
            cutoff = sorted(e["id"] for a in agents for e in a["events"])[excess - 1]
            for a in agents:
                a["events"][:] = [e for e in a["events"] if e["id"] > cutoff]
        # Call lookup tables must expire together with the retained timeline.
        retained = {e["id"] for a in agents for e in a["events"]}
        for index in (self._tool_events, self._tool_events_by_name):
            for key, value in list(index.items()):
                if value not in retained:
                    del index[key]
        return event

    def _find_event(self, actor_id: str, event_id: int) -> Optional[Dict[str, Any]]:
        agent = self._state["agents"].get(actor_id)
        if not agent:
            return None
        for event in reversed(agent["events"]):
            if int(event.get("id") or 0) == int(event_id or 0):
                return event
        return None

    def _tool_call(self, actor_id: str, data: Any, local: bool = False):
        tool = self._tool_name(data)
        call_id = self._call_id(data)
        event = self._add_event(
            actor_id,
            "tool",
            tool,
            data={
                "tool": tool,
                "tool_input": self._text(self._tool_args(data)),
                "tool_output": "",
                "tool_state": "running",
                "local": bool(local),
            },
        )
        if call_id:
            self._tool_events[(actor_id, call_id)] = event["id"]
        self._tool_events_by_name[(actor_id, tool)] = event["id"]

    def _tool_result(self, actor_id: str, data: Any, state: str = "completed"):
        tool = self._tool_name(data)
        call_id = self._call_id(data)
        event_id = self._tool_events.get((actor_id, call_id)) if call_id else None
        if event_id is None:
            event_id = self._tool_events_by_name.get((actor_id, tool))
        event = self._find_event(actor_id, event_id) if event_id is not None else None
        if event is None:
            event = self._add_event(
                actor_id,
                "tool",
                tool,
                data={
                    "tool": tool,
                    "tool_input": "",
                    "tool_output": "",
                    "tool_state": state,
                    "local": False,
                },
            )
        event["tool_state"] = state
        output = self._tool_output(data)
        if output not in (None, ""):
            event["tool_output"] = self._text(output)

    def ingest(self, event: str, data: Any = None, actor: str = "orchestrator", run_id: str = "", text: bool = False):
        """Consume one redacted Agents v2 diagnostic event."""
        name = str(event or "").strip().upper()
        changed = False
        with self._lock:
            if (
                    name != "RUNTIME INIT"
                    and run_id
                    and self._state.get("run_id")
                    and str(run_id) != str(self._state.get("run_id"))
            ):
                return
            if name == "RUNTIME INIT":
                self._begin_run(run_id, data)
                changed = True
            elif not self._state.get("run_id"):
                # Defensive path for tests/custom runtimes that publish before init.
                self._begin_run(run_id, {})
                changed = True

            actor_id = self._resolve_actor(actor)
            root = self._state["agents"].get(self.ROOT_ID)

            if name == "USER INPUT":
                if root is not None:
                    root["details"]["input"] = self._text(data)
                    root["status"] = "running"
                    self._start_timer(root)
                self._add_event(self.ROOT_ID, "running", "running_task")
                changed = True

            elif name == "SYSTEM PROMPT":
                target = self._state["agents"].get(actor_id)
                if target is not None:
                    target["details"]["system_prompt"] = self._text(data)
                else:
                    pending = self._pending_agents.setdefault(str(actor), {})
                    pending["system_prompt"] = self._text(data)
                changed = True

            elif name == "AGENT BUILD":
                built_name = str(self._get(data, "name", default=actor) or actor)
                resolved = self._resolve_actor(built_name)
                target = self._state["agents"].get(resolved)
                if target is not None:
                    target["details"]["description"] = str(self._get(data, "description", default="") or "")
                    self._register_alias(built_name, resolved)
                else:
                    description = str(self._get(data, "description", default="") or "")
                    pending = self._pending_agents.get(built_name)
                    if pending is None and description:
                        # Worker names can be normalized/truncated and swarm mode adds
                        # its ordinal prefix after AGENT CREATE REQUEST. Re-key the
                        # matching pending request by its instruction/description so
                        # details survive that rename.
                        for pending_name, candidate in reversed(list(self._pending_agents.items())):
                            instruction = str(candidate.get("instruction") or "")
                            if instruction and description == instruction[:512]:
                                pending = self._pending_agents.pop(pending_name)
                                self._pending_agents[built_name] = pending
                                break
                    if pending is None:
                        pending = self._pending_agents.setdefault(built_name, {})
                    pending["name"] = built_name
                    pending["description"] = description
                changed = True

            elif name == "AGENT CREATE REQUEST":
                worker_name = str(self._get(data, "name", default="Worker") or "Worker")
                pending = {
                    key: self._text(self._get(data, key, default=""))
                    for key in ("name", "instruction", "system_prompt", "task", "language", "description")
                }
                self._pending_agents[worker_name] = pending
                self._add_event(
                    self.ROOT_ID,
                    "agent_create",
                    worker_name,
                    data={
                        "agent_name": worker_name,
                        "instruction": self._text(self._get(data, "instruction", default="")),
                        "system_prompt": self._text(self._get(data, "system_prompt", default="")),
                        "task": self._text(self._get(data, "task", default="")),
                    },
                )
                changed = True

            elif name in {"AGENT CREATED", "AGENT CREATE RESULT"}:
                worker_id = str(self._get(data, "id", default=actor_id) or actor_id)
                worker_name = str(self._get(data, "name", default=actor) or actor)
                pending = self._pending_agents.pop(worker_name, {})
                worker = self._ensure_agent(worker_id, worker_name, parent_id=self.ROOT_ID, role="worker")
                worker["status"] = str(self._get(data, "status", default="created") or "created")
                self._sync_timer(worker, worker["status"])
                worker["turn"] = int(self._get(data, "generation", default=worker.get("turn", 0)) or 0)
                details = worker["details"]
                details["instruction"] = self._text(pending.get("instruction", details.get("instruction", "")))
                details["system_prompt"] = self._text(pending.get("system_prompt", details.get("system_prompt", "")))
                details["task"] = self._text(pending.get("task", self._get(data, "current_task", default="")))
                details["language"] = self._text(pending.get("language", self._get(data, "language", default="")))
                if pending.get("description"):
                    details["description"] = self._text(pending.get("description"))
                self._register_alias(worker_name, worker_id)
                # Only AGENT CREATED adds the lifecycle row; CREATE RESULT is a duplicate summary.
                if name == "AGENT CREATED":
                    self._add_event(worker_id, "created", "agent_created", turn=max(1, worker["turn"] or 1))
                changed = True

            elif name == "AGENT RUNNING":
                worker = self._ensure_agent(actor_id, str(self._get(data, "name", default=actor_id) or actor_id), self.ROOT_ID)
                worker["status"] = "running"
                self._start_timer(worker)
                generation = int(self._get(data, "generation", default=worker.get("turn", 0) or 1) or 1)
                worker["turn"] = max(1, generation)
                task = self._text(self._get(data, "current_task", default=""))
                if task:
                    worker["details"]["task"] = task
                self._add_event(actor_id, "running", "running_task", turn=worker["turn"])
                changed = True

            elif name == "WORKER INPUT":
                worker = self._ensure_actor(actor_id, self.ROOT_ID)
                worker["details"]["input"] = self._text(data)
                changed = True

            elif name in {"WORKER STATUS", "WORKFLOW STATUS", "PRIMARY AGENT STATUS", "ORCHESTRATOR STATUS", "SWARM STATUS"}:
                status = self._get(data, "progress", "status", default="")
                agent = self._ensure_actor(actor_id, self.ROOT_ID if actor_id != self.ROOT_ID else None)
                state = str(self._get(data, "state", default="") or "").strip().lower()
                if state:
                    agent["status"] = state
                    self._sync_timer(agent, state)
                generation = self._get(data, "generation", default=None)
                if generation not in (None, ""):
                    try:
                        agent["turn"] = max(1, int(generation))
                    except (TypeError, ValueError):
                        pass
                if status:
                    kind = "completed" if state == "completed" else ("failed" if state == "failed" else "status")
                    self._add_event(actor_id, kind, self._text(status), turn=max(1, int(agent.get("turn") or 1)))
                if status or state:
                    changed = True

            elif name in {"TOOL CALL", "LOCAL TOOL CALL", "LOCAL TOOL REQUEST"}:
                # LlamaIndex emits TOOL CALL for wrapped local plugins, and the local
                # bridge additionally emits LOCAL TOOL CALL/REQUEST. Merge those
                # boundaries into one visible row while preserving genuinely parallel
                # same-name calls when provider call ids differ.
                tool = self._tool_name(data)
                if tool in self.SEMANTIC_TOOLS:
                    return
                call_id = self._call_id(data)
                existing = None
                if call_id:
                    event_id = self._tool_events.get((actor_id, call_id))
                    existing = self._find_event(actor_id, event_id) if event_id else None
                by_name_id = self._tool_events_by_name.get((actor_id, tool))
                by_name = self._find_event(actor_id, by_name_id) if by_name_id else None
                if existing is None and by_name is not None and by_name.get("tool_state") == "running":
                    if not call_id or by_name.get("local"):
                        existing = by_name
                        if call_id:
                            self._tool_events[(actor_id, call_id)] = existing["id"]
                if existing is not None and existing.get("tool_state") == "running":
                    args = self._tool_args(data)
                    if args not in (None, "", {}):
                        existing["tool_input"] = self._text(args)
                    if name.startswith("LOCAL TOOL"):
                        existing["local"] = True
                else:
                    self._tool_call(actor_id, data, local=name.startswith("LOCAL TOOL"))
                changed = True

            elif name in {"TOOL RESULT", "LOCAL TOOL RESPONSE"}:
                if self._tool_name(data) in self.SEMANTIC_TOOLS:
                    return
                self._tool_result(actor_id, data, "completed")
                changed = True

            elif name in {"LOCAL TOOL CANCELLED", "LOCAL TOOL REJECTED"}:
                if self._tool_name(data) in self.SEMANTIC_TOOLS:
                    return
                self._tool_result(actor_id, data, "cancelled" if name.endswith("CANCELLED") else "failed")
                changed = True

            elif name == "PROVIDER TOOL ACTIVITY":
                self._tool_call(actor_id, data, local=False)
                # Hosted providers expose only the boundary, not a separate result.
                event_id = self._tool_events_by_name.get((actor_id, self._tool_name(data)))
                event_row = self._find_event(actor_id, event_id) if event_id else None
                if event_row is not None:
                    event_row["tool_state"] = "provider"
                changed = True

            elif name in {"WORKER ERROR", "AGENT FAILED"}:
                agent = self._ensure_actor(actor_id, self.ROOT_ID)
                agent["status"] = "failed"
                self._stop_timer(agent)
                message = self._text(self._get(data, "error", default=data))
                self._add_event(actor_id, "failed", message or "failed")
                changed = True

            elif name in {"WORKER CANCELLED", "AGENT STOPPED"}:
                agent = self._ensure_actor(actor_id, self.ROOT_ID)
                agent["status"] = "stopped"
                self._stop_timer(agent)
                self._add_event(actor_id, "stopped", "stopped")
                changed = True

            elif name in {"AGENT REMOVED"}:
                agent = self._ensure_actor(actor_id, self.ROOT_ID)
                agent["status"] = "removed"
                self._stop_timer(agent)
                self._add_event(actor_id, "stopped", "removed")
                changed = True

            elif name in {"WORKFLOW FINAL RESPONSE ARMED", "RUNNER FINALIZE BEGIN"}:
                self._add_event(self.ROOT_ID, "finalizing", "finalizing")
                changed = True

            elif name in {"PRIMARY AGENT FINAL TEXT", "ORCHESTRATOR FINAL TEXT", "FINAL ANSWER", "RUNNER FINALIZE END"}:
                if root is not None:
                    root["status"] = "completed"
                    self._stop_timer(root)
                if name == "RUNNER FINALIZE END":
                    self._add_event(self.ROOT_ID, "completed", "completed")
                changed = True

        if changed:
            self._publish()
