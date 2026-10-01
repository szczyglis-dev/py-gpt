#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.25 18:32:00                  #
# ================================================== #

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional


class AgentWorkflowBridge:
    """Translate legacy agent-runtime events into the shared Agent Workflow state.

    The monitor itself intentionally understands one compact event vocabulary
    (the same vocabulary used by Agents v2).  Legacy LlamaIndex/OpenAI runners
    feed this bridge with their native events; the bridge translates them and
    delegates to ``window.core.agent_workflow``.  This keeps all state limits,
    tool-row merging, timers and rendering behavior in one implementation.
    """

    _SENSITIVE_KEYS = {
        "api_key", "apikey", "api-key", "authorization", "password",
        "passwd", "secret", "access_token", "refresh_token", "token",
        "client_secret",
    }

    @classmethod
    def _is_sensitive_key(cls, key: Any) -> bool:
        value = str(key or "").strip().lower()
        if value in cls._SENSITIVE_KEYS:
            return True
        return any(
            marker in value
            for marker in (
                "api_key", "apikey", "authorization", "password", "secret",
                "access_token", "refresh_token",
            )
        )

    def __init__(
            self,
            window=None,
            *,
            source: str,
            root_name: str,
            model: Any = None,
            preset: Any = None,
            system_prompt: str = "",
            prompt: str = "",
    ):
        self.window = window
        self.source = str(source or "agent")
        self.root_name = str(root_name or "Agent")
        self.model = model
        self.preset = preset
        self.system_prompt = str(system_prompt or "")
        self.prompt = str(prompt or "")
        self.run_id = f"legacy-{self.source}-{uuid.uuid4().hex}"
        self.current_actor = "orchestrator"
        self._started = False
        self._finished = False
        self._actors: Dict[str, str] = {}
        self._tool_names: Dict[str, str] = {}
        self._last_tool_by_actor: Dict[str, str] = {}

    @staticmethod
    def _field(value: Any, *keys: str, default=None):
        if isinstance(value, dict):
            for key in keys:
                item = value.get(key)
                if item not in (None, ""):
                    return item
            return default
        for key in keys:
            item = getattr(value, key, None)
            if item not in (None, ""):
                return item
        return default

    @classmethod
    def _safe(cls, value: Any, depth: int = 0):
        """Convert SDK/runtime objects to a small JSON-safe monitor payload."""
        if depth > 6:
            return str(value)
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, bytes):
            return f"<bytes:{len(value)}>"
        if isinstance(value, dict):
            return {
                str(k): ("<redacted>" if cls._is_sensitive_key(k) else cls._safe(v, depth + 1))
                for k, v in value.items()
            }
        if isinstance(value, (list, tuple, set)):
            return [cls._safe(v, depth + 1) for v in value]
        dump = getattr(value, "model_dump", None)
        if callable(dump):
            try:
                return cls._safe(dump(), depth + 1)
            except Exception:
                pass
        data = getattr(value, "__dict__", None)
        if isinstance(data, dict):
            public = {
                str(k): v for k, v in data.items()
                if not str(k).startswith("_") and not callable(v)
            }
            if public:
                return cls._safe(public, depth + 1)
        return str(value)

    @staticmethod
    def _model_id(model: Any) -> str:
        if model is None:
            return ""
        return str(getattr(model, "id", None) or model or "")

    @staticmethod
    def _model_provider(model: Any) -> str:
        if model is None:
            return ""
        return str(getattr(model, "provider", None) or "")

    @staticmethod
    def _preset_name(preset: Any) -> str:
        if preset is None:
            return ""
        return str(getattr(preset, "name", None) or getattr(preset, "id", None) or "")

    def _workflow(self):
        return getattr(getattr(self.window, "core", None), "agent_workflow", None)

    def _visible(self) -> bool:
        try:
            controller = getattr(getattr(self.window, "controller", None), "agent_workflow", None)
            check = getattr(controller, "is_visible", None)
            return bool(check()) if callable(check) else True
        except Exception:
            return False

    def _emit(
            self,
            event: str,
            data: Any = None,
            *,
            actor: Optional[str] = None,
            text: bool = False,
            boundary: bool = False,
    ):
        workflow = self._workflow()
        if workflow is None:
            return
        # Match Agents v2 behavior: retain only lightweight run boundaries while
        # the monitor is hidden. Detailed payloads are runtime/UI diagnostics and
        # must not be accumulated in the background.
        if not boundary and not self._visible():
            return
        try:
            workflow.ingest(
                event,
                data,
                actor=actor or self.current_actor,
                run_id=self.run_id,
                text=text,
            )
        except Exception:
            # Monitoring must never affect the agent run.
            pass

    def start(self):
        if self._started:
            return
        self._started = True
        self._emit(
            "RUNTIME INIT",
            {
                "agent_mode": self.source,
                "agent_name": self.root_name,
                "model": self._model_id(self.model),
                "provider": self._model_provider(self.model),
                "preset": self._preset_name(self.preset),
            },
            actor="orchestrator",
            boundary=True,
        )
        try:
            controller = getattr(getattr(self.window, "controller", None), "agent_workflow", None)
            callback = getattr(controller, "on_run_started", None)
            if callable(callback):
                callback()
        except Exception:
            pass
        # Onboarding may have made the workflow tab visible. Capture the useful
        # request details after that transition, not before it.
        if self._visible():
            if self.system_prompt:
                self._emit("SYSTEM PROMPT", self.system_prompt, actor="orchestrator", text=True)
            if self.prompt:
                self._emit("USER INPUT", self.prompt, actor="orchestrator", text=True)

    def _actor(self, name: Any) -> str:
        text = str(name or "").strip()
        if not text:
            return self.current_actor
        if text.casefold() == self.root_name.casefold():
            return "orchestrator"
        key = text.casefold()
        actor = self._actors.get(key)
        if actor:
            return actor
        actor = f"legacy-agent-{len(self._actors) + 1}"
        self._actors[key] = actor
        self._emit(
            "AGENT CREATED",
            {"id": actor, "name": text, "status": "created", "generation": 1},
            actor=text,
        )
        return actor

    def agent_running(self, name: Any, *, task: str = "") -> str:
        actor = self._actor(name)
        if actor == self.current_actor:
            if task:
                self.status(task, actor=actor)
            return actor
        if self.current_actor != "orchestrator":
            self._emit(
                "WORKER STATUS",
                {"state": "completed", "progress": "completed"},
                actor=self.current_actor,
            )
        self.current_actor = actor
        if actor == "orchestrator":
            self._emit(
                "WORKFLOW STATUS",
                {"state": "running", "progress": task or "running_task"},
                actor=actor,
            )
        else:
            self._emit(
                "AGENT RUNNING",
                {"name": str(name or actor), "generation": 1, "current_task": task},
                actor=actor,
            )
        return actor

    def step(self, name: Any, *, index: Any = None, total: Any = None, meta: Optional[Dict[str, Any]] = None):
        meta = meta or {}
        agent_name = self._field(meta, "agent_name", "agent", "name", default="")
        if agent_name:
            self.agent_running(agent_name)
        label = str(name or "step")
        if index not in (None, ""):
            label += f" {index}"
            if total not in (None, ""):
                label += f"/{total}"
        event = "WORKFLOW STATUS" if self.current_actor == "orchestrator" else "WORKER STATUS"
        self._emit(
            event,
            {"state": "running", "progress": label},
            actor=self.current_actor,
        )

    def tool_call(self, name: Any, args: Any = None, *, call_id: Any = "", actor: Optional[str] = None):
        tool = str(name or "tool")
        actor_id = actor or self.current_actor
        call_id = str(call_id or "")
        if call_id:
            self._tool_names[call_id] = tool
        self._last_tool_by_actor[actor_id] = tool
        self._emit(
            "TOOL CALL",
            {
                "tool_name": tool,
                "tool_args": self._safe(args),
                "tool_call_id": call_id,
            },
            actor=actor_id,
        )

    def tool_result(
            self,
            name: Any = "",
            output: Any = None,
            *,
            call_id: Any = "",
            actor: Optional[str] = None,
    ):
        actor_id = actor or self.current_actor
        call_id = str(call_id or "")
        tool = str(name or "")
        if not tool and call_id:
            tool = self._tool_names.get(call_id, "")
        if not tool:
            tool = self._last_tool_by_actor.get(actor_id, "tool")
        self._emit(
            "TOOL RESULT",
            {
                "tool_name": tool,
                "tool_output": self._safe(output),
                "tool_call_id": call_id,
            },
            actor=actor_id,
        )
        if call_id:
            self._tool_names.pop(call_id, None)

    def status(self, message: Any, *, state: str = "running", actor: Optional[str] = None):
        actor_id = actor or self.current_actor
        event = "WORKFLOW STATUS" if actor_id == "orchestrator" else "WORKER STATUS"
        self._emit(
            event,
            {"state": str(state or "running"), "progress": str(message or "")},
            actor=actor_id,
        )

    def finish(self, output: Any = None):
        if self._finished:
            return
        self._finished = True
        if self.current_actor != "orchestrator":
            self._emit(
                "WORKER STATUS",
                {"state": "completed", "progress": "completed"},
                actor=self.current_actor,
            )
        if self._visible() and output not in (None, ""):
            self._emit("FINAL ANSWER", str(output), actor="orchestrator", text=True)
        self._emit("RUNNER FINALIZE END", None, actor="orchestrator", boundary=True)

    def fail(self, error: Any):
        if self._finished:
            return
        self._finished = True
        self._emit(
            "AGENT FAILED",
            {"error": str(error or "failed")},
            actor=self.current_actor,
            boundary=True,
        )
        self._emit("RUNNER FINALIZE END", None, actor="orchestrator", boundary=True)

    def stop(self):
        if self._finished:
            return
        self._finished = True
        self._emit("AGENT STOPPED", None, actor=self.current_actor, boundary=True)
        self._emit("RUNNER FINALIZE END", None, actor="orchestrator", boundary=True)

    # ------------------------------------------------------------------
    # Native runtime adapters
    # ------------------------------------------------------------------

    def llama_event(self, event: Any):
        """Translate one LlamaIndex workflow event without importing SDK types."""
        cls_name = event.__class__.__name__
        if cls_name == "StepEvent":
            self.step(
                self._field(event, "name", default="step"),
                index=self._field(event, "index"),
                total=self._field(event, "total"),
                meta=self._field(event, "meta", default={}) or {},
            )
            return
        if cls_name == "ToolCall":
            self.tool_call(
                self._field(event, "tool_name", "name", default="tool"),
                self._field(event, "tool_kwargs", "tool_args", "arguments", default={}),
                call_id=self._field(event, "tool_id", "tool_call_id", "call_id", "id", default=""),
            )
            return
        if cls_name == "ToolCallResult":
            output = self._field(event, "tool_output", "output", "result", default="")
            self.tool_result(
                self._field(event, "tool_name", "name", default=""),
                output,
                call_id=self._field(event, "tool_id", "tool_call_id", "call_id", "id", default=""),
            )
            return
        if cls_name in {"AgentStream", "AgentOutput"}:
            name = self._field(event, "current_agent_name", "agent_name", default="")
            if name:
                self.agent_running(name)

    def openai_event(self, event: Any, ctx: Any = None):
        """Translate one OpenAI Agents SDK stream event using duck typing."""
        event_type = str(self._field(event, "type", default="") or "")

        if event_type == "agent_updated_stream_event":
            new_agent = self._field(event, "new_agent")
            name = self._field(new_agent, "name", default="")
            if name:
                self.agent_running(name)
            return

        if event_type != "run_item_stream_event":
            return

        event_name = str(self._field(event, "name", default="") or "")
        item = self._field(event, "item")
        raw = self._field(item, "raw_item", default=None)

        if event_name in {"handoff_occured", "handoff_occurred"}:
            target = self._field(item, "target_agent", default=None)
            name = self._field(target, "name", default="")
            if name:
                self.agent_running(name)
            return

        if event_name in {"tool_called", "tool_search_called"}:
            raw_type = str(self._field(raw, "type", default="") or "")
            name = self._field(raw, "name", "tool_name", default="")
            if not name:
                name = raw_type[:-5] if raw_type.endswith("_call") else (raw_type or "tool")
            args = self._field(raw, "arguments", "input", "action", "actions", "code", default={})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    pass
            call_id = self._field(raw, "call_id", "id", default="")
            self.tool_call(name, args, call_id=call_id)
            return

        if event_name in {"tool_output", "tool_search_output_created"}:
            call_id = self._field(raw, "call_id", "id", default="")
            output = self._field(item, "output", default=None)
            if output is None:
                output = self._field(raw, "output", default="")
            self.tool_result("", output, call_id=call_id)
