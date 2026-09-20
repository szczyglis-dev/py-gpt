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

import json
from typing import Any, Dict, Optional

from pygpt_net.core.types import PERSIST_HIDDEN_TOOL_CALLS

from .utils import (
    json_safe_tool_result,
    json_safe_tool_value,
    tool_event_value,
    tool_result_value,
)


class RuntimeToolHistory:
    """Persist tool calls/results and project them to the durable UI history."""

    def __init__(self, runtime):
        self.runtime = runtime

    def register_local_plugin_tool(self, name: str):
        value = str(name or "").strip()
        if value:
            self.runtime._local_plugin_tool_names.add(value)

    def _new_tool_call_id(self, call_id: Any = None) -> str:
        if call_id not in (None, ""):
            return str(call_id)
        self.runtime._main_tool_call_seq += 1
        return f"agents_v2_{self.runtime.run_id}_{self.runtime._main_tool_call_seq}"

    def _persist_tool_call(self, name: str, args: Any, actor: str, call_id: Any = None) -> str:
        """Persist an Agents v2 tool invocation according to hidden-tool policy."""
        name = str(name or "tool").strip() or "tool"
        actor_id, agent_name, current_task = self.runtime._actor_metadata(actor)
        value = self.runtime._new_tool_call_id(call_id)
        hidden = self.runtime.window.core.command.is_tool_hidden(name)
        self.runtime.window.core.api.tool_logger.log_call(
            name=name,
            params=args,
            call_id=value,
            actor=actor,
            raw={"name": name, "arguments": args, "call_id": value},
            extra={"agents_v2": True, "hidden": hidden},
        )
        if hidden and not PERSIST_HIDDEN_TOOL_CALLS:
            return value
        part = self.runtime._actor_part(actor, create=True)
        safe_args = json_safe_tool_value(args)
        if isinstance(safe_args, dict) and len(safe_args) == 1:
            for wrapper in ("params", "arguments"):
                wrapped = safe_args.get(wrapper)
                if isinstance(wrapped, dict):
                    safe_args = dict(wrapped)
                    break
        if part is None:
            return value
        calls = [{
            "id": value, "call_id": value, "type": "function",
            "function": {"name": name, "arguments": safe_args},
        }]
        tasks = self.runtime.window.core.ctx.record_tool_calls(
            getattr(self.runtime.context, "ctx", None), calls, part=part,
            agent_id=actor_id, agent_name=agent_name,
            task_name=current_task or name, update_legacy_cache=False,
            ui_visible=(
                self.runtime.return_tool_calls_to_main_ctx
                and not hidden
            ),
            provider_history=(str(actor or "orchestrator") == "orchestrator"),
        )
        if tasks:
            task = tasks[0]
            if not isinstance(task.extra, dict):
                task.extra = {}
            task.extra["agents_v2_actor"] = actor_id
            task.extra["tool_name"] = name
            task.extra["ui_ready"] = False
            self.runtime.window.core.ctx.update_part_task(task)
            self.runtime._persisted_tool_tasks[f"{actor_id}:{value}"] = task
        return value

    def _persist_tool_result(
            self, result: Any, actor: str, name: str = "", call_id: Any = None
    ) -> bool:
        actor_id, _agent_name, _task_name = self.runtime._actor_metadata(actor)
        name = str(name or "").strip()
        value = str(call_id).strip() if call_id not in (None, "") else ""
        self.runtime.window.core.api.tool_logger.log_result(
            name=name or "tool",
            response=result,
            call_id=value or None,
            actor=actor,
            extra={"agents_v2": True},
        )
        task = self.runtime._persisted_tool_tasks.get(f"{actor_id}:{value}") if value else None
        main = getattr(self.runtime.context, "ctx", None)
        if task is None and main is not None:
            for part in main.parts or []:
                for candidate in part.tasks or []:
                    extra = candidate.extra if isinstance(candidate.extra, dict) else {}
                    if str(candidate.agent_id or "") != actor_id:
                        continue
                    if extra.get("status") == "completed":
                        continue
                    if value and str(candidate.tool_call_id or "") != value:
                        continue
                    tool_name = str(extra.get("tool_name") or candidate.task_name or "")
                    if name and tool_name != name:
                        continue
                    task = candidate
                    break
                if task is not None:
                    break
        if task is None:
            return False
        safe_result = json_safe_tool_result(result)
        task.tool_output = safe_result
        task.output = safe_result if isinstance(safe_result, str) else json.dumps(
            safe_result, ensure_ascii=False, default=str
        )
        if not isinstance(task.extra, dict):
            task.extra = {}
        task.extra["status"] = "completed"
        task.extra["ui_ready"] = False
        task.task_summary = f"Tool {task.extra.get('tool_name') or name or 'tool'} completed"
        task.touch()
        self.runtime.window.core.ctx.update_part_task(task)
        return True

    def _promote_part_tasks(self, part):
        """Expose completed tasks once the model has produced its next response."""
        if part is None:
            return
        for task in part.tasks or []:
            extra = task.extra if isinstance(task.extra, dict) else {}
            if extra.get("status") == "completed" and not extra.get("ui_ready"):
                task.mark_ui_ready(True)
                self.runtime.window.core.ctx.update_part_task(task)

    def _promote_actor_tasks(self, actor: str):
        """Expose completed calls once that actor has produced a next response."""
        actor_id, _agent_name, _task_name = self.runtime._actor_metadata(actor)
        main = getattr(self.runtime.context, "ctx", None)
        if main is None:
            return
        for part in main.parts or []:
            for task in part.tasks or []:
                if str(getattr(task, "agent_id", "") or "") != str(actor_id):
                    continue
                extra = task.extra if isinstance(task.extra, dict) else {}
                if extra.get("status") == "completed" and not extra.get("ui_ready"):
                    task.mark_ui_ready(True)
                    self.runtime.window.core.ctx.update_part_task(task)

    def _promote_all_tasks(self):
        """Expose every completed displayable tool before the final UI commit."""
        main = getattr(self.runtime.context, "ctx", None)
        if main is None:
            return
        for part in main.parts or []:
            self.runtime._promote_part_tasks(part)

    def _append_main_tool_call(self, name: str, args: Any, actor: str, call_id: Any = None) -> Optional[str]:
        if not self.runtime.return_tool_calls_to_main_ctx:
            return None
        name = str(name or "").strip()
        if not name or self.runtime.window.core.command.is_tool_hidden(name):
            return None

        args = json_safe_tool_value(args)
        # Match the local plugin bridge: providers occasionally wrap the real
        # function payload once more in params/arguments.
        if isinstance(args, dict) and len(args) == 1:
            for wrapper in ("params", "arguments"):
                wrapped = args.get(wrapper)
                if isinstance(wrapped, dict):
                    args = dict(wrapped)
                    break

        value = self.runtime._new_tool_call_id(call_id)
        self.runtime._main_tool_calls.append({
            "id": value,
            "call_id": value,
            "type": "function",
            "function": {
                "name": name,
                "arguments": args,
            },
            # Kept as metadata for diagnostics; the regular tool renderer ignores it.
            "agents_v2_actor": str(actor or "orchestrator"),
        })
        return value

    def _set_main_tool_result(
            self,
            result: Any,
            actor: str,
            name: str = "",
            call_id: Any = None,
    ) -> bool:
        """Attach a response to the matching persisted call without reordering it."""
        if not self.runtime.return_tool_calls_to_main_ctx:
            return False
        actor = str(actor or "orchestrator")
        name = str(name or "").strip()
        call_id = str(call_id).strip() if call_id not in (None, "") else ""

        def matches(item: Dict[str, Any], require_id: bool) -> bool:
            if "agents_v2_response" in item:
                return False
            if str(item.get("agents_v2_actor") or "orchestrator") != actor:
                return False
            function = item.get("function") or {}
            if name and str(function.get("name") or "") != name:
                return False
            if require_id:
                item_id = str(item.get("call_id") or item.get("id") or "")
                if item_id != call_id:
                    return False
            return True

        # Prefer the provider/LlamaIndex call id. If a provider does not preserve
        # it on ToolCallResult, fall back to the oldest unmatched call with the
        # same actor + name. This also handles repeated calls to one tool.
        if call_id:
            for item in self.runtime._main_tool_calls:
                if matches(item, True):
                    item["agents_v2_response"] = json_safe_tool_result(result)
                    return True
        for item in self.runtime._main_tool_calls:
            if matches(item, False):
                item["agents_v2_response"] = json_safe_tool_result(result)
                return True
        return False

    def record_local_plugin_tool_call(
            self, name: str, args: Any, actor: str = "orchestrator"
    ) -> Optional[str]:
        """Persist a validated local plugin call and optionally mirror it to UI cache."""
        call_id = self.runtime._persist_tool_call(name, args, actor)
        self.runtime._append_main_tool_call(name, args, actor, call_id=call_id)
        return call_id

    def record_local_plugin_tool_result(
            self, call_id: Any, name: str, result: Any, actor: str = "orchestrator"
    ):
        """Attach the exact local plugin response to its persisted task/call."""
        if not call_id:
            return
        self.runtime._persist_tool_result(result, actor=actor, name=name, call_id=call_id)
        self.runtime._set_main_tool_result(result, actor=actor, name=name, call_id=call_id)

    def record_tool_call(self, event: Any, actor: str = "orchestrator"):
        """Persist a non-plugin tool invocation and optionally mirror it to legacy UI."""
        name = tool_event_value(event, "tool_name", "name", "tool")
        name = str(name or "").strip()
        if not name or name in self.runtime._local_plugin_tool_names:
            return
        args = tool_event_value(
            event, "tool_kwargs", "tool_args", "arguments", "kwargs", "args", "raw_arguments",
        )
        event_id = tool_event_value(event, "tool_id", "call_id", "id")
        call_id = self.runtime._persist_tool_call(name, args, actor, call_id=event_id)
        self.runtime._append_main_tool_call(name, args, actor, call_id=call_id)

    def record_tool_result(self, event: Any, actor: str = "orchestrator"):
        """Persist the corresponding ToolCallResult for a non-plugin invocation."""
        name = tool_event_value(event, "tool_name", "name", "tool")
        name = str(name or "").strip()
        if not name or name in self.runtime._local_plugin_tool_names:
            return
        event_id = tool_event_value(event, "tool_id", "call_id", "id")
        result = tool_result_value(event)
        self.runtime._persist_tool_result(result, actor=actor, name=name, call_id=event_id)
        self.runtime._set_main_tool_result(result, actor=actor, name=name, call_id=event_id)

    def export_tool_calls_to_main_ctx(self):
        """Persist the collected normal tool calls on the user-visible turn.

        Intentionally do *not* assign ``main.tool_calls`` and do not synthesize
        ``tool_output``. Those fields participate in the legacy execution/reply
        pipeline and could cause the already executed tools to be replayed.
        """
        main = getattr(self.runtime.context, "ctx", None)
        if main is None:
            return
        if not isinstance(main.extra, dict):
            main.extra = {}

        # If the option was disabled after this CtxItem previously received an
        # Agents v2 display-only export (for example before Regenerate), remove
        # only that export. Never touch tool data owned by another mode.
        if not self.runtime.return_tool_calls_to_main_ctx:
            if main.extra.get("agents_v2_tool_calls_display"):
                main.extra.pop("tool_calls", None)
                main.extra.pop("agents_v2_tool_calls_display", None)
                try:
                    self.runtime.window.core.ctx.update_item(main)
                except Exception as exc:
                    self.runtime.window.core.debug.log(exc)
            return

        # Always replace a previous Agents v2 export (e.g. after Regenerate) so
        # the main item reflects exactly this workflow execution.
        if self.runtime._main_tool_calls:
            main.extra["tool_calls"] = list(self.runtime._main_tool_calls)
            main.extra["agents_v2_tool_calls_display"] = True
        elif main.extra.get("agents_v2_tool_calls_display"):
            main.extra.pop("tool_calls", None)
            main.extra.pop("agents_v2_tool_calls_display", None)

        try:
            self.runtime.window.core.ctx.update_item(main)
        except Exception as exc:
            self.runtime.window.core.debug.log(exc)
