#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 11:00:00                  #
# ================================================== #

from __future__ import annotations

import dataclasses
import datetime
import json
import threading
from enum import Enum
from typing import Any, Dict, Iterable


class AgentsV2VerboseLogger:
    """Console diagnostics for Agents v2.

    Two independent modes are supported:
    - agent.v2.log_workflow: compact, human-readable orchestration trace.
    - agent.v2.verbose: complete diagnostic dump of the runtime flow.

    Both modes intentionally bypass PyGPT's global log level and write directly
    to stdout. Logging must never affect orchestration behavior.
    """

    _lock = threading.RLock()
    _sensitive_keys = {
        "api_key", "apikey", "api-key", "authorization", "password",
        "passwd", "secret", "access_token", "refresh_token", "token",
        "client_secret",
    }
    _orchestration_tools = {
        "agent_create", "agent_update", "agent_run", "agent_status", "agent_list",
        "agent_wait", "agent_stop", "agent_remove", "workflow_status", "workflow_finish",
        "delegate_task", "swarm_start", "swarm_status",
    }

    def __init__(self, window=None, run_id: str = "", agent_mode=None):
        self.window = window
        self.run_id = str(run_id or "-")
        self.agent_mode = str(getattr(agent_mode, "value", agent_mode) or "primary_agent").strip().lower()
        self.is_orchestrator_mode = self.agent_mode in ("orchestrator", "swarm")
        self.is_swarm_mode = self.agent_mode == "swarm"
        try:
            config = window.core.config
            self.enabled = bool(config.get("agent.v2.verbose", False))
            self.workflow_enabled = bool(config.get("agent.v2.log_workflow", False))
        except Exception:
            self.enabled = False
            self.workflow_enabled = False
        self._workflow_final_logged = False

    @staticmethod
    def _timestamp() -> str:
        return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

    @classmethod
    def _is_sensitive_key(cls, key: Any) -> bool:
        value = str(key or "").strip().lower()
        if value in cls._sensitive_keys:
            return True
        return any(
            marker in value
            for marker in (
                "api_key", "apikey", "authorization", "password", "secret",
                "access_token", "refresh_token",
            )
        )

    @classmethod
    def _safe_value(cls, value: Any, depth: int = 0) -> Any:
        """Convert arbitrary runtime objects to printable JSON-safe structures."""
        if depth > 8:
            return str(value)
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, bytes):
            return f"<bytes:{len(value)}>"
        if isinstance(value, dict):
            out: Dict[str, Any] = {}
            for key, item in value.items():
                name = str(key)
                out[name] = "<redacted>" if cls._is_sensitive_key(name) else cls._safe_value(item, depth + 1)
            return out
        if isinstance(value, (list, tuple, set)):
            return [cls._safe_value(item, depth + 1) for item in value]
        if dataclasses.is_dataclass(value):
            try:
                return cls._safe_value(dataclasses.asdict(value), depth + 1)
            except Exception:
                pass
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            try:
                return cls._safe_value(model_dump(), depth + 1)
            except Exception:
                pass
        dict_fn = getattr(value, "dict", None)
        if callable(dict_fn):
            try:
                return cls._safe_value(dict_fn(), depth + 1)
            except Exception:
                pass
        public = getattr(value, "__dict__", None)
        if isinstance(public, dict):
            data = {
                key: item for key, item in public.items()
                if not str(key).startswith("_") and not callable(item)
            }
            if data:
                return cls._safe_value(data, depth + 1)
        return str(value)

    @classmethod
    def _json(cls, value: Any) -> str:
        safe = cls._safe_value(value)
        if isinstance(safe, str):
            return safe
        try:
            return json.dumps(safe, ensure_ascii=False, indent=2, default=str)
        except Exception:
            return str(safe)

    @staticmethod
    def _single_line(value: Any, limit: int = 420) -> str:
        if value is None:
            return ""
        text = " ".join(str(value).replace("\x00", "").split())
        if len(text) > limit:
            return text[:max(0, limit - 3)].rstrip() + "..."
        return text

    @classmethod
    def _quote(cls, value: Any, limit: int = 260) -> str:
        text = cls._single_line(value, limit)
        return json.dumps(text, ensure_ascii=False)

    @staticmethod
    def _data_get(data: Any, key: str, default=None):
        if isinstance(data, dict):
            return data.get(key, default)
        return getattr(data, key, default)

    @classmethod
    def _brief_arg(cls, key: str, value: Any) -> str:
        if cls._is_sensitive_key(key):
            return f"{key}=<redacted>"
        if value is None or isinstance(value, (str, int, float, bool)):
            return f"{key}={cls._quote(value, 100)}" if isinstance(value, str) else f"{key}={value}"
        if isinstance(value, dict):
            return f"{key}=<object:{len(value)}>"
        if isinstance(value, (list, tuple, set)):
            return f"{key}=<list:{len(value)}>"
        return f"{key}=<{value.__class__.__name__}>"

    @classmethod
    def _brief_args(cls, value: Any, max_items: int = 4) -> str:
        if not isinstance(value, dict) or not value:
            return ""
        parts = []
        for key, item in list(value.items())[:max_items]:
            parts.append(cls._brief_arg(str(key), item))
        if len(value) > max_items:
            parts.append(f"+{len(value) - max_items} more")
        return ", ".join(parts)

    @classmethod
    def _tool_name(cls, data: Any) -> str:
        for key in ("tool_name", "name", "tool"):
            value = cls._data_get(data, key)
            if value:
                return str(value)
        return "tool"

    @classmethod
    def _tool_args(cls, data: Any) -> Any:
        for key in ("tool_kwargs", "tool_args", "arguments", "kwargs", "args", "raw_arguments"):
            value = cls._data_get(data, key)
            if value not in (None, ""):
                return value
        return None

    @classmethod
    def _tool_output(cls, data: Any) -> Any:
        for key in ("tool_output", "output", "result", "response"):
            value = cls._data_get(data, key)
            if value not in (None, ""):
                content = getattr(value, "content", None)
                return content if content not in (None, "") else value
        return ""

    def _workflow_write(self, message: str, actor: str = "orchestrator"):
        if not self.workflow_enabled:
            return
        actor_name = str(actor or "orchestrator").strip()
        line = self._single_line(message, 1200)
        with self._lock:
            print(
                f"[Agents v2][{self._timestamp()}][run={self.run_id}][{actor_name}] {line}",
                flush=True,
            )

    def _workflow_event(self, event: str, data: Any = None, actor: str = "orchestrator"):
        if not self.workflow_enabled:
            return
        name = str(event or "").strip().upper()
        try:
            if name == "RUNTIME INIT":
                self._workflow_write(
                    "workflow started "
                    f"model={self._data_get(data, 'model') or '-'} "
                    f"provider={self._data_get(data, 'provider') or '-'} "
                    f"preset={self._quote(self._data_get(data, 'preset') or '-', 120)} "
                    f"local_tools={'on' if self._data_get(data, 'allow_local_tools') else 'off'} "
                    f"remote_tools={'on' if self._data_get(data, 'allow_remote_tools') else 'off'} "
                    f"rag={self._data_get(data, 'index_id') or 'off'}",
                    actor,
                )
            elif name == "AGENT BUILD":
                agent_name = self._data_get(data, "name") or actor
                self._workflow_write(
                    f"agent ready name={self._quote(agent_name, 80)} "
                    f"engine={self._data_get(data, 'agent_class') or '-'}",
                    actor,
                )
            elif name == "TOOLS":
                tools = data if isinstance(data, list) else []
                names = [str(item.get("name") or item.get("type") or "tool") for item in tools if isinstance(item, dict)]
                shown = names[:24]
                suffix = f", +{len(names) - len(shown)} more" if len(names) > len(shown) else ""
                self._workflow_write(f"tools available: {', '.join(shown) or 'none'}{suffix}", actor)
            elif name == "RAG PREFETCH REQUEST":
                self._workflow_write(
                    f"retrieving RAG context index={self._data_get(data, 'index_id') or '-'} "
                    f"query={self._quote(self._data_get(data, 'query'), 220)}",
                    actor,
                )
            elif name == "RAG PREFETCH SKIP":
                self._workflow_write(f"RAG skipped: {self._single_line(data, 240)}", actor)
            elif name == "RAG PREFETCH ERROR":
                self._workflow_write(f"RAG error: {self._single_line(data, 320)}", actor)
            elif name == "PRIMARY AGENT INPUT":
                self._workflow_write("running primary agent", actor)
            elif name == "ORCHESTRATOR INPUT":
                self._workflow_write("running orchestrator", actor)
            elif name == "SWARM INPUT":
                self._workflow_write("running swarm orchestrator", actor)
            elif name == "SWARM START":
                self._workflow_write(
                    f"swarm declared agents={self._data_get(data, 'agent_count') or '-'}", actor
                )
            elif name in {"SWARM STATUS", "SWARM STATUS AUTO"}:
                self._workflow_write(
                    "swarm status "
                    f"created={self._data_get(data, 'created') or 0}/"
                    f"{self._data_get(data, 'declared') or 0} "
                    f"running={self._data_get(data, 'running') or 0} "
                    f"completed={self._data_get(data, 'completed') or 0} "
                    f"failed={self._data_get(data, 'failed') or 0}",
                    actor,
                )
            elif name == "DELEGATE TASK REQUEST":
                self._workflow_write(
                    f"delegating to specialist name={self._quote(self._data_get(data, 'name') or 'Specialist', 80)} "
                    f"task={self._quote(self._data_get(data, 'task'), 360)}",
                    actor,
                )
            elif name == "DELEGATE TASK RESULT":
                self._workflow_write(
                    f"specialist result name={self._quote(self._data_get(data, 'name') or actor, 80)} "
                    f"status={self._data_get(data, 'status') or '-'}",
                    actor,
                )
            elif name == "STOP REQUESTED":
                self._workflow_write("stop requested", actor)
            elif name == "TOOL CALL":
                tool = self._tool_name(data)
                if tool in self._orchestration_tools:
                    return
                args = self._brief_args(self._tool_args(data))
                suffix = f" ({args})" if args else ""
                self._workflow_write(f"tool call: {tool}{suffix}", actor)
            elif name == "TOOL RESULT":
                tool = self._tool_name(data)
                if tool in self._orchestration_tools:
                    return
                output = self._single_line(self._tool_output(data), 320)
                suffix = f": {self._quote(output, 320)}" if output else ""
                self._workflow_write(f"tool result: {tool}{suffix}", actor)
            elif name == "LOCAL TOOL CANCELLED":
                self._workflow_write(f"tool cancelled: {self._data_get(data, 'tool') or 'tool'}", actor)
            elif name == "LOCAL TOOL REJECTED":
                self._workflow_write(
                    f"tool rejected: {self._data_get(data, 'tool') or 'tool'} "
                    f"reason={self._quote(self._data_get(data, 'error') or data, 260)}",
                    actor,
                )
            elif name == "REPORT STATUS CALL":
                status = self._data_get(data, "status")
                if status:
                    self._workflow_write(f"status: {self._quote(status, 260)}", actor)
            elif name == "WORKER STATUS":
                status = self._data_get(data, "progress") or self._data_get(data, "status") or self._data_get(data, "text")
                if status:
                    self._workflow_write(f"status: {self._quote(status, 260)}", actor)
            elif name == "AGENT CREATE REQUEST":
                if not self.is_orchestrator_mode:
                    return
                parts = [f"creating agent name={self._quote(self._data_get(data, 'name') or 'Worker', 80)}"]
                instruction = self._data_get(data, "instruction")
                task = self._data_get(data, "task")
                if instruction:
                    parts.append(f"instruction={self._quote(instruction, 260)}")
                if task:
                    parts.append(f"task={self._quote(task, 260)}")
                self._workflow_write(" ".join(parts), actor)
            elif name == "AGENT CREATE REJECTED":
                if self.is_orchestrator_mode:
                    self._workflow_write(f"agent creation rejected: {self._quote(data, 300)}", actor)
            elif name == "AGENT CREATED":
                if self.is_orchestrator_mode:
                    self._workflow_write(
                        f"agent created id={self._data_get(data, 'id') or actor} "
                        f"name={self._quote(self._data_get(data, 'name') or 'Worker', 80)}",
                        actor,
                    )
            elif name == "AGENT UPDATE REQUEST":
                if self.is_orchestrator_mode:
                    fields = []
                    for key in ("name", "instruction", "language"):
                        value = self._data_get(data, key)
                        if value:
                            fields.append(f"{key}={self._quote(value, 180)}")
                    self._workflow_write(
                        f"updating agent id={self._data_get(data, 'agent_id') or actor}"
                        + (" " + " ".join(fields) if fields else ""), actor
                    )
            elif name == "AGENT UPDATED":
                if self.is_orchestrator_mode:
                    self._workflow_write(f"agent updated id={self._data_get(data, 'id') or actor}", actor)
            elif name == "AGENT RUN REQUEST":
                if self.is_orchestrator_mode:
                    self._workflow_write(
                        f"running agent id={self._data_get(data, 'agent_id') or actor} "
                        f"task={self._quote(self._data_get(data, 'task'), 360)}", actor
                    )
            elif name == "WORKER CANCELLED":
                self._workflow_write(f"agent stopped id={self._data_get(data, 'id') or actor}", actor)
            elif name == "WORKER ERROR":
                self._workflow_write(f"agent failed: {self._quote(self._data_get(data, 'error') or data, 360)}", actor)
            elif name == "AGENT STOP REQUEST":
                if self.is_orchestrator_mode:
                    self._workflow_write(f"stopping agent id={self._data_get(data, 'agent_id') or actor}", actor)
            elif name == "AGENT STOPPED":
                if self.is_orchestrator_mode:
                    self._workflow_write(f"agent stopped id={self._data_get(data, 'id') or actor}", actor)
            elif name == "AGENT REMOVE REQUEST":
                if self.is_orchestrator_mode:
                    self._workflow_write(f"removing agent id={self._data_get(data, 'agent_id') or actor}", actor)
            elif name == "AGENT REMOVED":
                if self.is_orchestrator_mode:
                    self._workflow_write(f"agent removed id={self._data_get(data, 'id') or actor}", actor)
            elif name == "AGENT STATUS":
                if self.is_orchestrator_mode:
                    self._workflow_write(
                        f"agent status id={self._data_get(data, 'id') or actor} "
                        f"status={self._data_get(data, 'status') or '-'}", actor
                    )
            elif name == "AGENT LIST":
                if self.is_orchestrator_mode:
                    states = data if isinstance(data, list) else []
                    summary = ", ".join(
                        f"{item.get('id', '?')}={item.get('status', '?')}"
                        for item in states if isinstance(item, dict)
                    )
                    self._workflow_write(f"agents: {summary or 'none'}", actor)
            elif name == "AGENT WAIT REQUEST":
                if self.is_orchestrator_mode:
                    ids = self._data_get(data, "agent_ids") or "all"
                    self._workflow_write(
                        f"waiting for agents ids={ids} mode={self._data_get(data, 'wait_for') or 'all'} "
                        f"timeout={self._data_get(data, 'timeout_seconds') or 60}s", actor
                    )
            elif name == "AGENT WAIT RESULT":
                if self.is_orchestrator_mode:
                    workers = self._data_get(data, "workers", []) or []
                    summary = ", ".join(
                        f"{item.get('id', '?')}={item.get('status', '?')}"
                        for item in workers if isinstance(item, dict)
                    )
                    self._workflow_write(f"wait completed: {summary or 'no matching agents'}", actor)
            elif name in {"PRIMARY AGENT STATUS", "ORCHESTRATOR STATUS", "SWARM STATUS"}:
                status = self._data_get(data, "status")
                if status:
                    self._workflow_write(f"status: {self._quote(status, 260)}", actor)
            elif name == "WORKFLOW STATUS":
                status = self._data_get(data, "status")
                if status:
                    self._workflow_write(f"workflow status: {self._quote(status, 260)}", actor)
            elif name == "WORKFLOW FINISH REJECTED":
                self._workflow_write(f"workflow finish rejected: {self._quote(data, 360)}", actor)
            elif name == "ARTIFACT":
                self._workflow_write(
                    f"artifact: {self._data_get(data, 'type') or 'item'}={self._quote(self._data_get(data, 'value'), 260)}",
                    actor,
                )
            elif name == "REMOTE TOOL ARTIFACTS":
                urls = self._data_get(data, "urls", []) or []
                if urls:
                    self._workflow_write(f"remote tool artifacts: {len(urls)} URL(s)", actor)
            elif name == "MEMORY APPEND":
                self._workflow_write("conversation memory updated", actor)
            elif name == "RUNNER FINALIZE BEGIN":
                self._workflow_write("finalizing workflow", actor)
            elif name == "RUNNER FINALIZE END":
                self._workflow_write("workflow ended", actor)
            elif name == "CLEANUP BEGIN":
                self._workflow_write("cleaning up agents", actor)
            # Intentionally ignore STREAM/AGENT STREAM, full prompts, full history,
            # raw local-tool request/response JSON and other diagnostic-only events.
        except Exception:
            pass

    def _workflow_text_event(self, event: str, text: Any, actor: str = "orchestrator"):
        if not self.workflow_enabled:
            return
        name = str(event or "").strip().upper()
        try:
            if name == "USER INPUT":
                self._workflow_write(f"user input: {self._quote(text, 420)}", actor)
            elif name == "RAG PREFETCH RESULT":
                length = len(str(text or ""))
                self._workflow_write(f"RAG context received ({length} chars)", actor)
            elif name == "WORKER OUTPUT":
                self._workflow_write(f"response received: {self._quote(text, 600)}", actor)
            elif name == "WORKFLOW FINISH REQUEST":
                self._workflow_write(f"finishing workflow response={self._quote(text, 600)}", actor)
            elif name == "FINAL ANSWER":
                self._workflow_write(f"final response: {self._quote(text, 700)}", actor)
                self._workflow_final_logged = True
            elif name in {"PRIMARY AGENT RESULT", "ORCHESTRATOR RESULT"}:
                if text:
                    label = "orchestrator" if name == "ORCHESTRATOR RESULT" else "primary agent"
                    self._workflow_write(f"{label} response received: {self._quote(text, 600)}", actor)
            elif name in {"PRIMARY AGENT FINAL TEXT", "ORCHESTRATOR FINAL TEXT"}:
                if not self._workflow_final_logged:
                    self._workflow_write(f"final response: {self._quote(text, 700)}", actor)
                    self._workflow_final_logged = True
            # SYSTEM PROMPT and STREAM are deliberately omitted from compact mode.
        except Exception:
            pass

    def log(self, event: str, data: Any = None, actor: str = "orchestrator"):
        self._workflow_event(event, data, actor)
        if not self.enabled:
            return
        try:
            label = str(event or "EVENT").strip().upper()
            actor_name = str(actor or "orchestrator").strip()
            header = f"[Agents v2][{self._timestamp()}][run={self.run_id}][{actor_name}][{label}]"
            with self._lock:
                print(header, flush=True)
                if data is not None:
                    print(self._json(data), flush=True)
        except Exception:
            pass

    def text(self, event: str, text: Any, actor: str = "orchestrator"):
        self._workflow_text_event(event, text, actor)
        if not self.enabled:
            return
        try:
            label = str(event or "TEXT").strip().upper()
            actor_name = str(actor or "orchestrator").strip()
            header = f"[Agents v2][{self._timestamp()}][run={self.run_id}][{actor_name}][{label}]"
            with self._lock:
                print(header, flush=True)
                print(str(text or ""), flush=True)
        except Exception:
            pass

    def tool_inventory(self, tools: Iterable[Any], actor: str = "orchestrator"):
        if not self.enabled and not self.workflow_enabled:
            return
        inventory = []
        for tool in tools or []:
            try:
                metadata = getattr(tool, "metadata", None)
                name = getattr(metadata, "name", None) or getattr(tool, "name", None) or tool.__class__.__name__
                item = {"name": name, "type": tool.__class__.__name__}
                if self.enabled:
                    description = getattr(metadata, "description", None) or ""
                    schema = None
                    get_params = getattr(metadata, "get_parameters_dict", None)
                    if callable(get_params):
                        try:
                            schema = get_params()
                        except Exception:
                            schema = None
                    if schema is None:
                        fn_schema = getattr(metadata, "fn_schema", None)
                        if fn_schema is not None:
                            model_schema = getattr(fn_schema, "model_json_schema", None)
                            if callable(model_schema):
                                try:
                                    schema = model_schema()
                                except Exception:
                                    schema = None
                    item.update({"description": description, "schema": schema})
                inventory.append(item)
            except Exception:
                inventory.append({"type": tool.__class__.__name__, "value": str(tool)})
        self.log("TOOLS", inventory, actor=actor)

    def llm_state(self, llm: Any, actor: str = "orchestrator"):
        if not self.enabled:
            return
        data = {
            "class": llm.__class__.__name__ if llm is not None else None,
        }
        try:
            metadata = getattr(llm, "metadata", None)
            if metadata is not None:
                data["metadata"] = self._safe_value(metadata)
        except Exception:
            pass

        # Only inspect known tool-related attributes. Do not dump the whole LLM
        # object because it can contain API credentials and HTTP client state.
        for key in (
            "built_in_tools",
            "pygpt_remote_tools",
            "_pygpt_remote_tools",
            "tools",
            "tool_choice",
            "parallel_tool_calls",
            "allow_parallel_tool_calls",
        ):
            try:
                value = getattr(llm, key, None)
                if value not in (None, [], {}, ""):
                    data[key] = self._safe_value(value)
            except Exception:
                pass
        self.log("LLM / REMOTE TOOLS", data, actor=actor)
