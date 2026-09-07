#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.15 22:00:00                  #
# ================================================== #

import copy
import datetime
import uuid
import json
from typing import Optional, Tuple, List, Dict

from packaging.version import Version

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_ASSISTANT,
    MODE_AUDIO,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_EXPERT,
    MODE_IMAGE,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_RESEARCH,
    MODE_COMPUTER,
    MODE_AGENT_OPENAI,
    MODE_AGENT_V2,
)
from pygpt_net.item.ctx import CtxItem, CtxMeta, CtxGroup
from pygpt_net.item.ctx_part import CtxItemPart
from pygpt_net.item.ctx_part_task import CtxItemPartTask
from pygpt_net.provider.core.ctx.base import BaseProvider
from pygpt_net.provider.core.ctx.db_sqlite import DbSqliteProvider
from pygpt_net.utils import trans

from .idx import Idx
from .container import Container
from .output import Output


class Ctx:
    def __init__(self, window=None):
        """
        Context core

        :param window: Window instance
        """
        self.window = window
        self.provider = DbSqliteProvider(window)
        self.container = Container(window)  # context container
        self.output = Output(window)  # context render output
        self.idx = Idx(window)  # context indexing core
        self.meta = {}
        self.current = None
        self.last_item = None
        self.assistant = None
        self.mode = None
        self.model = None
        self.preset = None
        self.run = None
        self.status = None
        self.thread = None
        self.last_mode = None
        self.last_model = None
        self.tmp_meta = None
        self.search_string = None  # search string
        self.groups = {}  # groups
        self.filters = {}  # search filters
        self.filters_labels = []  # search labels
        self.current_cmd = []  # current commands
        self.current_cmd_schema = "" # current commands schema
        self.all_modes = [
            MODE_CHAT,
            MODE_COMPLETION,
            MODE_IMAGE,
            MODE_LANGCHAIN,
            MODE_VISION,
            MODE_ASSISTANT,
            MODE_LLAMA_INDEX,
            MODE_AGENT,
            MODE_AGENT_LLAMA,
            MODE_AGENT_OPENAI,
            MODE_AGENT_V2,
            MODE_EXPERT,
            MODE_AUDIO,
            MODE_RESEARCH,
            MODE_COMPUTER,
        ]
        self.allowed_modes = {
            MODE_CHAT: self.all_modes,
            MODE_COMPLETION: self.all_modes,
            MODE_IMAGE: [MODE_IMAGE],
            MODE_LANGCHAIN: self.all_modes,
            MODE_VISION: self.all_modes,
            MODE_ASSISTANT: [MODE_ASSISTANT],
            MODE_LLAMA_INDEX: self.all_modes,
            MODE_EXPERT: self.all_modes,
            MODE_AUDIO: self.all_modes,
            MODE_AGENT: self.all_modes,
            MODE_AGENT_LLAMA: self.all_modes,
            MODE_AGENT_OPENAI: self.all_modes,
            MODE_AGENT_V2: self.all_modes,
            MODE_RESEARCH: self.all_modes,
            MODE_COMPUTER: self.all_modes,
        }
        self.current_sys_prompt = ""
        self.groups_loaded = False

    def get_items(self) -> List[CtxItem]:
        """
        Get context items

        :return: context items
        """
        return self.container.get_items()

    def set_items(self, items: List[CtxItem]):
        """
        Set context items

        :param items: context items
        """
        self.container.set_items(items)

    def clear_items(self):
        """Clear context items"""
        self.container.clear_items()

    def count_items(self) -> int:
        """
        Count context items
        :return: context items count
        """
        return self.container.count_items()

    def get_current(self) -> int:
        """
        Get current context ID

        :return: current context ID
        """
        return self.current

    def set_current(self, current: int):
        """
        Set current context ID

        :param current: current context ID
        """
        self.current = current

    def clear_current(self):
        """Clear current context ID"""
        self.current = None

    def get_last_item(self) -> Optional[CtxItem]:
        """
        Get last item

        :return: last item
        """
        return self.last_item

    def set_last_item(self, last_item: Optional[CtxItem]):
        """
        Set last item

        :param last_item: last item
        """
        self.last_item = last_item

    def get_assistant(self) -> str:
        """
        Get assistant name

        :return: assistant name
        """
        return self.assistant

    def set_assistant(self, assistant: str):
        """
        Set assistant name

        :param assistant: assistant name
        :return: assistant name
        """
        self.assistant = assistant

    def get_mode(self) -> str:
        """
        Get mode

        :return: mode
        """
        return self.mode

    def set_mode(self, mode: str):
        """
        Set mode

        :param mode: mode
        """
        self.mode = mode

    def get_model(self) -> str:
        """
        Get model name
        :return: model name
        """
        return self.model

    def set_model(self, model: str):
        """
        Set model name

        :param model: model name
        """
        self.model = model

    def get_preset(self) -> str:
        """
        Get preset name
        :return: preset
        """
        return self.preset

    def set_preset(self, preset: str):
        """
        Set preset name

        :param preset: preset name
        """
        self.preset = preset

    def get_run(self) -> str:
        """
        Get run ID

        :return: run ID
        """
        return self.run

    def set_status(self, status: int):
        """
        Set status (label color)

        :param status: status
        """
        self.status = status

    def get_status(self) -> int:
        """
        Get status (label color)

        :return: status
        """
        return self.status

    def set_run(self, run: str):
        """
        Set run ID

        :param run: run ID
        """
        self.run = run

    def get_thread(self) -> str:
        """
        Get thread ID

        :return: thread ID
        """
        return self.thread

    def set_thread(self, thread: str):
        """
        Set thread ID

        :param thread: thread ID
        """
        self.thread = thread

    def clear_thread(self):
        """Clear thread ID"""
        self.thread = None

    def get_last_mode(self) -> str:
        """
        Get last mode

        :return: last mode
        """
        return self.last_mode

    def set_last_mode(self, last_mode: str):
        """
        Set last mode

        :param last_mode: last mode
        """
        self.last_mode = last_mode

    def get_last_model(self) -> str:
        """
        Get last model name

        :return: last model
        """
        return self.last_model

    def set_last_model(self, last_model: str):
        """
        Set last model name

        :param last_model: last model name
        """
        self.last_model = last_model

    def get_tmp_meta(self) -> Optional[CtxMeta]:
        """
        Get temporary meta

        :return: temporary meta
        """
        return self.tmp_meta

    def set_tmp_meta(self, tmp_meta: Optional[CtxMeta]):
        """
        Set temporary meta

        :param tmp_meta: temporary meta
        """
        self.tmp_meta = tmp_meta

    def get_search_string(self) -> Optional[str]:
        """
        Get search string

        :return: search string
        """
        return self.search_string

    def set_search_string(self, search_string: Optional[str]):
        """
        Set search string

        :param search_string: search string
        """
        self.search_string = search_string

    def clear_search_string(self):
        """Clear search string"""
        self.search_string = None

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version: Version) -> bool:
        """
        Patch provider data

        :param app_version: app version
        :return: True if data was patched
        """
        return self.provider.patch(app_version)

    def get_provider(self) -> BaseProvider:
        """
        Get provider instance

        :return: provider instance
        """
        return self.provider

    def select(
            self,
            id: int,
            restore_model: bool = True
    ):
        """
        Select ctx meta by ID and load ctx items

        :param id: context meta id
        :param restore_model: restore model
        """
        if id not in self.meta:
            self.load_tmp_meta(id)

        if id in self.meta:
            ctx = self.meta[id]
            self.current = id

            self.thread = None
            self.mode = None
            self.assistant = None

            self.thread = ctx.thread
            self.mode = ctx.mode
            self.assistant = ctx.assistant
            self.preset = ctx.preset

            if restore_model:
                if ctx.last_model is not None \
                        and self.window.core.models.has_model(self.mode, ctx.last_model):
                    self.model = ctx.last_model
                elif ctx.model is not None \
                        and self.window.core.models.has_model(self.mode, ctx.model):
                    self.model = ctx.model

            self.set_items(self.load(id))

    def new(
            self,
            group_id: Optional[int] = None
    ) -> Optional[CtxMeta]:
        """
        Create new ctx and set as current

        :param group_id: group id
        :return: CtxMeta instance (new ctx meta)
        """
        meta = self.create(group_id)
        if meta is None:
            self.window.core.debug.log("Error creating new ctx")
            return
        preset = self.window.core.config.get('preset')
        meta.preset = preset
        self.meta[meta.id] = meta
        self.tmp_meta = meta
        self.current = meta.id
        self.last_item = None
        self.thread = None
        self.assistant = None
        self.mode = self.window.core.config.get('mode')
        self.model = self.window.core.config.get('model')
        self.preset = preset
        self.clear_items()
        self.save(meta.id)

        return meta

    def build(self) -> CtxMeta:
        """
        Build new ctx

        :return: created CtxMeta instance
        """
        meta = CtxMeta()
        meta.name = "{}".format(trans('ctx.new.prefix'))
        meta.date = datetime.datetime.now().strftime("%Y-%m-%d")
        meta.mode = self.window.core.config.get('mode')
        meta.model = self.window.core.config.get('model')
        meta.last_mode = self.window.core.config.get('mode')
        meta.last_model = self.window.core.config.get('model')
        meta.initialized = False
        return meta

    def create(
            self,
            group_id: Optional[int] = None
    ) -> CtxMeta:
        """
        Send created meta to provider and return new ID

        :param group_id: group id
        :return: CtxMeta instance
        """
        meta = self.build()
        if group_id is not None:
            meta.group_id = group_id
        id = self.provider.create(meta)
        meta.id = id
        return meta

    def add(
            self,
            item: CtxItem,
            parent_id: Optional[int] = None
    ):
        """
        Add CtxItem to contexts and saves context

        :param item: CtxItem to append
        :param parent_id: parent id
        """
        if parent_id is not None:
            self.add_to_meta(item, parent_id)
            return

        items = self.get_items()
        items.append(item)

        if self.current is not None:
            if self.current not in self.meta:
                self.load_tmp_meta(self.current)
            if self.current in self.meta:
                meta = self.meta[self.current]
                result = self.provider.append_item(meta, item)
                if not result:
                    self.store()

    def add_to_meta(
            self,
            item: CtxItem,
            meta_id: Optional[int] = None
    ):
        """
        Add CtxItem to custom meta

        :param item: CtxItem to append
        :param meta_id: meta id
        """
        if meta_id in self.meta:
            meta = self.meta[meta_id]
        else:
            meta = self.provider.get_meta_by_id(meta_id)
        if meta is not None:
            self.provider.append_item(meta, item)

    def update_item(self, item: CtxItem):
        """Update a turn and keep its compatibility output cache in sync."""
        if item is None:
            return
        if item.parts:
            # Legacy/simple paths still write directly to CtxItem.output. Mirror
            # that into the sole part automatically; multi-part paths update the
            # active part explicitly and are only folded here.
            if len(item.parts) == 1:
                part = item.get_active_part()
                if part is not None and part.output != item.output:
                    part.set_output(item.output)
                    self.provider.update_part(part)
            else:
                item.sync_output_from_parts()
        self.provider.update_item(item)

    def ensure_part(
            self,
            item: CtxItem,
            agent_id: Optional[str] = None,
            name: Optional[str] = None,
    ) -> CtxItemPart:
        """Return the active partial item, creating it if necessary."""
        part = item.get_active_part()
        if part is not None:
            return part
        return self.begin_part(item, agent_id=agent_id, name=name, output=item.output)

    def begin_part(
            self,
            item: CtxItem,
            agent_id: Optional[str] = None,
            name: Optional[str] = None,
            output: Optional[str] = None,
            extra: Optional[dict] = None,
            joiner: str = "",
    ) -> CtxItemPart:
        """Create and persist a logical fragment inside one context turn."""
        if item is None or item.id is None:
            part = CtxItemPart(parent_item_id=getattr(item, 'id', None))
        else:
            part = CtxItemPart(parent_item_id=item.id)
        part.agent_id = agent_id
        part.name = name
        part.output = output
        part.extra = dict(extra or {})
        if joiner:
            part.extra["joiner"] = joiner
        if item.id is not None:
            self.provider.append_part(part)
        item.set_active_part(part)
        return part

    def update_part(self, item: CtxItem, part: Optional[CtxItemPart] = None, sync_item: bool = True):
        """Persist a partial item and optionally refresh the parent output cache."""
        part = part or item.get_active_part()
        if part is None:
            return
        if part.id is not None:
            self.provider.update_part(part)
        if sync_item:
            item.sync_output_from_parts()
            if item.id is not None:
                self.provider.update_item(item)

    def add_part_task(
            self,
            item: CtxItem,
            part: Optional[CtxItemPart] = None,
            *,
            agent_id: Optional[str] = None,
            name: Optional[str] = None,
            task_name: Optional[str] = None,
            task_summary: Optional[str] = None,
            input: Optional[str] = None,
            output: Optional[str] = None,
            tool_call_id: Optional[str] = None,
            tool_input=None,
            tool_output=None,
            extra: Optional[dict] = None,
    ) -> CtxItemPartTask:
        """Create and persist one task under a partial item."""
        part = part or self.ensure_part(item, agent_id=agent_id, name=name)
        task = CtxItemPartTask(
            parent_item_part_id=part.id, agent_id=agent_id, name=name, task_name=task_name,
            task_summary=task_summary, input=input, output=output, tool_call_id=tool_call_id,
            tool_input=tool_input if tool_input is not None else {}, tool_output=tool_output,
            extra=dict(extra or {}),
        )
        part.add_task(task)
        if part.id is not None:
            self.provider.append_part_task(task)
        return task

    def update_part_task(self, task: CtxItemPartTask):
        if task is not None and task.id is not None:
            self.provider.update_part_task(task)

    @staticmethod
    def _part_has_text(part: Optional[CtxItemPart]) -> bool:
        """Return True only when a partial already owns assistant-visible text."""
        if part is None:
            return False
        return bool(str(getattr(part, "output", None) or "").strip())

    @staticmethod
    def _task_tool_round(task: CtxItemPartTask) -> int:
        """Return persisted tool round; pre-v8 rows belong to round 1."""
        extra = task.extra if isinstance(getattr(task, "extra", None), dict) else {}
        try:
            value = int(extra.get("tool_round") or 1)
        except (TypeError, ValueError):
            value = 1
        return max(1, value)

    @staticmethod
    def _task_in_provider_history(task: CtxItemPartTask) -> bool:
        extra = task.extra if isinstance(getattr(task, "extra", None), dict) else {}
        return extra.get("provider_history") is not False

    def _part_max_tool_round(self, part: Optional[CtxItemPart]) -> int:
        if part is None:
            return 0
        rounds = [
            self._task_tool_round(task)
            for task in (getattr(part, "tasks", None) or [])
            if self._task_in_provider_history(task)
            and (task.tool_call_id or (isinstance(task.extra, dict) and task.extra.get("tool_name")))
        ]
        return max(rounds) if rounds else 0

    def _part_tool_round_ids(self, part: Optional[CtxItemPart]) -> list:
        if part is None:
            return []
        return sorted({
            self._task_tool_round(task)
            for task in (getattr(part, "tasks", None) or [])
            if self._task_in_provider_history(task)
            and (task.tool_call_id or (isinstance(task.extra, dict) and task.extra.get("tool_name")))
        })

    def record_tool_calls(
            self,
            item: CtxItem,
            tool_calls: list,
            part: Optional[CtxItemPart] = None,
            agent_id: Optional[str] = None,
            agent_name: Optional[str] = None,
            task_name: Optional[str] = None,
            update_legacy_cache: bool = True,
            ui_visible: bool = True,
            provider_history: bool = True,
    ) -> list:
        """Persist native/legacy tool requests as tasks without ending the turn."""
        part = part or self.ensure_part(item, agent_id=agent_id, name=agent_name)
        existing = {}
        for task in part.tasks:
            if task.tool_call_id:
                existing[str(task.tool_call_id)] = task
            task_extra = task.extra if isinstance(task.extra, dict) else {}
            item_id = task_extra.get("tool_item_id")
            if item_id:
                existing[str(item_id)] = task

        # One call to record_tool_calls() represents one model tool-response
        # round. All sibling calls from that response share the same round, while
        # later tool-only continuations stay in this same CtxItemPart and receive
        # the next round number.
        next_tool_round = self._part_max_tool_round(part) + 1
        new_round_used = False
        tasks = []
        for index, call in enumerate(tool_calls or []):
            if not isinstance(call, dict):
                continue
            fn = call.get("function") if isinstance(call.get("function"), dict) else {}
            name = str(fn.get("name") or call.get("name") or "tool")
            args = fn.get("arguments", call.get("arguments", {}))

            # OpenAI Responses exposes two different identifiers for a function
            # call: ``id`` (e.g. fc_...) identifies the output item, whereas
            # ``call_id`` (e.g. call_...) is the protocol identifier that MUST
            # be echoed by function_call_output. Persist the protocol call_id as
            # the task's canonical ID and keep the provider item ID separately.
            provider_item_id = str(call.get("id") or "")
            call_id = str(call.get("call_id") or provider_item_id or f"{part.uuid}:{index}")
            lookup_ids = [value for value in (call_id, provider_item_id) if value]
            existing_task = next((existing[value] for value in lookup_ids if value in existing), None)
            if existing_task is not None:
                # Repair tasks created by older partial-flow builds which stored
                # Responses' fc_* item ID in tool_call_id and lost call_id.
                changed = False
                if existing_task.tool_call_id != call_id:
                    existing_task.tool_call_id = call_id
                    changed = True
                if not isinstance(existing_task.extra, dict):
                    existing_task.extra = {}
                if provider_item_id and existing_task.extra.get("tool_item_id") != provider_item_id:
                    existing_task.extra["tool_item_id"] = provider_item_id
                    changed = True
                tool_type = str(call.get("type") or "function")
                if existing_task.extra.get("tool_type") != tool_type:
                    existing_task.extra["tool_type"] = tool_type
                    changed = True
                if not existing_task.extra.get("tool_round"):
                    existing_task.extra["tool_round"] = 1
                    changed = True
                if existing_task.extra.get("provider_history") != bool(provider_history):
                    existing_task.extra["provider_history"] = bool(provider_history)
                    changed = True
                if changed:
                    self.update_part_task(existing_task)
                tasks.append(existing_task)
                continue

            request = {"cmd": name, "params": args}
            tool_type = str(call.get("type") or "function")
            if not new_round_used:
                # If this partial already contains its one text response, remember
                # how many tool rounds happened before that text. This lets the
                # provider-history projection place text and tool calls in their
                # original protocol order without creating more DB partials.
                if (provider_history
                        and self._part_has_text(part)
                        and isinstance(part.extra, dict)):
                    part.extra.setdefault("text_after_tool_round", next_tool_round - 1)
                    self.update_part(item, part, sync_item=False)
                new_round_used = True
            task = self.add_part_task(
                item, part, agent_id=agent_id, name=agent_name,
                task_name=task_name or name, input=json.dumps(request, ensure_ascii=False, default=str),
                tool_call_id=call_id, tool_input=args,
                extra={
                    "status": "pending", "ui_ready": False,
                    "agent_name": agent_name, "tool_name": name,
                    "tool_item_id": provider_item_id or call_id,
                    "tool_type": tool_type,
                    "tool_round": next_tool_round,
                    "ui_visible": bool(ui_visible),
                    "provider_history": bool(provider_history),
                },
            )
            tasks.append(task)
        if tasks and update_legacy_cache and isinstance(item.extra, dict):
            item.extra["tool_calls"] = list(tool_calls or [])
        return tasks

    def complete_part_tasks(self, item: CtxItem, results: list, part: Optional[CtxItemPart] = None) -> list:
        """Attach plugin results to pending tasks while preserving request order."""
        part = part or item.get_active_part()
        if part is None:
            return []
        pending = [t for t in part.tasks if not (isinstance(t.extra, dict) and t.extra.get("status") == "completed")]
        completed = []
        by_name = {}
        for task in pending:
            tool_name = (task.extra or {}).get("tool_name") if isinstance(task.extra, dict) else None
            by_name.setdefault(str(tool_name or task.task_name or task.name or ""), []).append(task)
        fallback = list(pending)
        for response in results or []:
            req = response.get("request") if isinstance(response, dict) else None
            name = str(req.get("cmd") or "") if isinstance(req, dict) else ""
            task = None
            if name and by_name.get(name):
                task = by_name[name].pop(0)
                if task in fallback:
                    fallback.remove(task)
            elif fallback:
                task = fallback.pop(0)
            if task is None:
                continue
            result = response.get("result") if isinstance(response, dict) and "result" in response else response
            # Persist the full structured plugin/tool response exactly as it is
            # forwarded through the tool-result loop. The plain-text output column
            # keeps a compact human-readable summary for quick inspection/UI.
            task.tool_output = copy.deepcopy(response)
            task.output = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
            if not isinstance(task.extra, dict):
                task.extra = {}
            task.extra["status"] = "completed"
            task.extra["response"] = response
            task.touch()
            self.update_part_task(task)
            completed.append(task)
        return completed

    def mark_part_tasks_ui_ready(self, part: Optional[CtxItemPart], ready: bool = True):
        """Promote completed tool tasks from waiting status into renderable buttons."""
        if part is None:
            return
        for task in part.tasks or []:
            if isinstance(task.extra, dict) and task.extra.get("status") == "completed":
                task.mark_ui_ready(ready)
                self.update_part_task(task)

    def merge_continuation(self, continuation: CtxItem) -> CtxItem:
        """Merge a post-tool model response into the same durable user turn.

        Tool-only responses reuse the active part so consecutive tool rounds stay
        compact. As soon as provider output contains visible assistant text after
        one or more tools, that text gets a new partial. This keeps the durable UI
        timeline chronological: text -> tool(s) -> later text.
        """
        parent = continuation.turn_parent
        if parent is None:
            return continuation

        current_part = parent.get_active_part()
        if current_part is None:
            current_part = self.ensure_part(parent)

        raw_output = str(continuation.output or "")
        legacy_cmds = self.window.core.command.extract_cmds(raw_output)
        visible_output = self.window.core.command.strip_cmds(raw_output) or ""
        has_text = bool(visible_output.strip())

        part = current_part
        if has_text:
            if (self._part_has_text(current_part)
                    or self._part_max_tool_round(current_part) > 0):
                part = self.begin_part(
                    parent,
                    name=continuation.output_name,
                    output=None,
                    joiner="\n\n" if (parent.compose_output() or "").strip() else "",
                )
            elif part is None:
                part = self.begin_part(parent, name=continuation.output_name, output=None)

            if not isinstance(part.extra, dict):
                part.extra = {}
            # A newly allocated text partial has no preceding tool rounds. For
            # legacy/reused empty parts retain ordering metadata so old contexts
            # can still be projected correctly after reload.
            part.extra.setdefault("text_after_tool_round", self._part_max_tool_round(part))
            part.output = visible_output
            if continuation.output_name:
                part.name = continuation.output_name
            self.update_part(parent, part, sync_item=False)
        else:
            # Tool-only continuation: do not clear prior text and do not create a
            # new partial. Legacy <tool> markup is represented solely by tasks.
            part = current_part

        continuation.turn_part = part

        # Promote only tasks that existed before this provider call. New calls
        # from the response are recorded afterwards, so they remain pending.
        self.mark_part_tasks_ui_ready(continuation.turn_previous_part, True)

        for attr in ("urls", "images", "files", "attachments", "results", "doc_ids"):
            target = getattr(parent, attr, None)
            source = getattr(continuation, attr, None)
            if isinstance(target, list) and source:
                for value in source:
                    if value not in target:
                        target.append(value)
        parent.input_tokens += int(continuation.input_tokens or 0)
        parent.output_tokens += int(continuation.output_tokens or 0)
        parent.total_tokens += int(continuation.total_tokens or 0)
        parent.output_timestamp = continuation.output_timestamp or parent.output_timestamp
        parent.msg_id = continuation.msg_id or parent.msg_id
        parent.response = continuation.response
        parent.tool_calls = list(continuation.tool_calls or [])
        parent.cmds = list(continuation.cmds or [])
        parent.cmds_before = list(continuation.cmds_before or legacy_cmds or [])
        if isinstance(continuation.extra, dict):
            if not isinstance(parent.extra, dict):
                parent.extra = {}
            for key, value in continuation.extra.items():
                if key not in ("sub_reply",):
                    parent.extra[key] = copy.deepcopy(value)
        if not parent.tool_calls and isinstance(parent.extra, dict):
            parent.extra.pop("tool_calls", None)
        parent.sync_output_from_parts()
        self.provider.update_item(parent)
        return parent

    def update_indexed_ts_by_id(self, id: int, ts: int):
        """
        Update indexed timestamp by ID

        :param id: context id
        :param ts: timestamp
        """
        if id in self.meta:
            self.meta[id].indexed = ts

    def is_empty(self) -> bool:
        """
        Check if ctx is empty

        :return: True if empty, false otherwise
        """
        if self.current is None:
            return True
        return self.count_items() == 0

    def update(self):
        """
        Update current parent (when ctx item load from the list or setting mode)
        """
        self.mode = self.window.core.config.get('mode')

        if self.current is None:
            return

        if self.current not in self.meta:
            self.load_tmp_meta(self.current)

        if self.current not in self.meta:
            return

        self.meta[self.current].mode = self.mode
        self.save(self.current)

    def replace(self, meta: CtxMeta):
        """
        Replace meta

        :param meta: CtxMeta
        """
        self.meta[meta.id] = meta

    def post_update(self, mode: str):
        """
        Update current (last) ctx data

        :param mode: mode name
        """
        if self.current is None:
            return

        if self.current not in self.meta:
            self.load_tmp_meta(self.current)

        if self.current not in self.meta:
            return

        self.assistant = self.window.core.config.get('assistant')
        self.preset = self.window.core.config.get('preset')
        self.model = self.window.core.config.get('model')

        self.meta[self.current].last_mode = mode
        self.meta[self.current].last_model = self.model
        self.meta[self.current].preset = self.preset

        if mode == MODE_ASSISTANT:
            self.meta[self.current].assistant = self.assistant

        self.save(self.current)

    def is_initialized(self) -> bool:
        """
        Check if ctx is initialized (name assigned)

        :return: True if initialized, false otherwise
        """
        if self.current is None:
            return False
        if self.current not in self.meta:
            self.load_tmp_meta(self.current)
        if self.current in self.meta:
            return self.meta[self.current].initialized
        return False

    def set_initialized(self):
        """Set ctx as initialized (name assigned)"""
        if self.current is None:
            return
        if self.current not in self.meta:
            self.load_tmp_meta(self.current)
        if self.current in self.meta:
            self.meta[self.current].initialized = True
            self.save(self.current)

    def has(self, id: int) -> bool:
        """
        Check if ctx meta exists

        :param id: ctx ID
        :return: True if exists, false otherwise
        """
        return id in self.meta

    def get(self, idx: int) -> CtxItem:
        """
        Return ctx item by index

        :param idx: item index
        :return: context item
        """
        if idx < self.count_items():
            return self.get_items()[idx]

    def get_item_by_id(self, id: int) -> CtxItem:
        """
        Return ctx item by id

        :param id: item id
        :return: context item
        """
        items = self.get_items()
        for item in items:
            if item.id == id:
                return item
        return self.fetch_item_by_id(id)

    def fetch_item_by_id(self, id: int) -> CtxItem:
        """
        Fetch ctx item by id

        :param id: item id
        :return: context item
        """
        return self.provider.get_item_by_id(id)

    def get_meta(self, reload: bool = False) -> dict:
        """
        Get ctx items sorted descending by date

        :param reload: True if reload from provider
        :return: ctx metas dict
        """
        if reload:
            self.load_meta()
        return self.meta

    def get_current_meta(self) -> Optional[CtxMeta]:
        """
        Get current meta

        :return: current meta
        """
        if self.current is not None:
            return self.get_meta_by_id(self.current)

    def get_id_by_idx(self, idx: int) -> int:
        """
        Get ctx id (id) by index

        :param idx: index
        :return: ctx id
        """
        i = 0
        for id in self.get_meta():
            if i == idx:
                return id
            i += 1

    def get_idx_by_id(self, id: int) -> int:
        """
        Get ctx index by id

        :param id: id
        :return: idx
        """
        for i, key in enumerate(self.get_meta()):
            if key == id:
                return i

    def get_first(self) -> str:
        """
        Return first ctx ID from list

        :return: ctx id
        """
        for id in self.get_meta():
            return id

    def get_meta_by_id(self, id: int) -> Optional[CtxMeta]:
        """
        Return ctx meta by id

        :param id: ctx id
        :return: ctx meta object
        """
        if id is None:
            return None
        if id in self.meta:
            return self.meta[id]

        # Context lists can be paginated. A tab may legitimately point to a
        # context that is not in the currently loaded page, so resolve it from
        # the provider and return it in this same call. Previously load_tmp_meta
        # populated ``self.meta`` but get_meta_by_id() still returned None on
        # the first lookup, which made tab restore intermittently fall back to
        # "New" until another lookup happened.
        self.load_tmp_meta(id)
        return self.meta.get(id)

    def get_last(self) -> Optional[CtxItem]:
        """
        Return last item from ctx

        :return: last ctx item
        """
        items = self.get_items()
        if items:
            return items[-1]
        return None

    def is_first_item(self, item_id: int) -> bool:
        """
        Check if item is first in ctx

        :param item_id: item id
        :return: True if first
        """
        items = self.get_items()
        if items:
            return items[0].id == item_id
        return False

    def is_last_item(self, item_id: int) -> bool:
        """
        Check if item is last in ctx

        :param item_id: item id
        :return: True if last
        """
        items = self.get_items()
        if items:
            return items[-1].id == item_id
        return False

    def get_previous_item(self, item_id: int) -> Optional[CtxItem]:
        """
        Get previous item from ctx

        :param item_id: item id
        :return: ctx item
        """
        items = self.get_items()
        prev = None
        for it in items:
            if it.id == item_id:
                return prev
            prev = it
        return None

    def prepare(self):
        """Prepare context for prompt"""
        if self.count_meta() == 0:
            self.new()

    def count(self) -> int:
        """
        Count ctx items

        :return: ctx items count
        """
        return self.count_items()

    def count_meta(self) -> int:
        """
        Count ctx meta items

        :return: ctx meta count
        """
        return len(self.meta) + (1 if self.tmp_meta is not None else 0)

    def count_found_meta(self) -> int:
        """
        Count ctx meta items

        :return: ctx meta count
        """
        return len(self.meta)

    def all(
            self,
            meta_id: Optional[int] = None
    ) -> List[CtxItem]:
        """
        Return ctx items (current or by meta_id if provided)

        :param meta_id: meta id
        :return: ctx items
        """
        if meta_id is None:
            return self.get_items()
        else:
            return self.load(meta_id)

    def remove(self, id: int):
        """
        Delete ctx by id

        :param id: ctx id
        """
        if id in self.meta:
            del self.meta[id]
            self.provider.remove(id)

    def remove_item(self, id: int):
        """
        Remove ctx item by id

        :param id: ctx id
        """
        items = self.get_items()
        for i, item in enumerate(items):
            if item.id == id:
                items.pop(i)
                self.provider.remove_item(id)
                break

    def remove_items_from(
            self,
            meta_id: int,
            item_id: int
    ):
        """
        Remove ctx items from meta_id

        :param meta_id: meta_id
        :param item_id: item_id
        """
        items = [item for item in self.get_items() if item.id < item_id]
        self.set_items(items)
        return self.provider.remove_items_from(meta_id, item_id)

    def truncate(self):
        """Delete all ctx"""
        self.meta = {}
        self.provider.truncate()

    def clear(self):
        """Clear ctx items"""
        self.clear_items()

    def append_thread(self, thread: str):
        """
        Append thread ID to ctx

        :param thread: thread ID
        """
        self.thread = thread
        if self.current is None:
            return
        if self.current not in self.meta:
            self.load_tmp_meta(self.current)
        if self.current in self.meta:
            self.meta[self.current].thread = self.thread
            self.save(self.current)

    def append_run(self, run):
        """
        Append run ID to ctx

        :param run: run ID
        """
        self.run = run
        if self.current is None:
            return
        if self.current not in self.meta:
            self.load_tmp_meta(self.current)
        if self.current in self.meta:
            self.meta[self.current].run = self.run
            self.save(self.current)

    def append_status(self, status: int):
        """
        Append status (label color) to ctx

        :param status: status
        """
        self.status = status
        if self.current is None:
            return
        if self.current in self.meta:
            self.meta[self.current].status = self.status
            self.save(self.current)

    def get_or_create_slave_meta(
            self,
            master_ctx: CtxItem,
            preset_id: str
    ) -> CtxMeta:
        """
        Get or create slave meta

        :param master_ctx: master context
        :param preset_id: preset ID
        :return: slave meta
        """
        slaves = []
        if master_ctx.meta is not None:
            slaves = self.provider.get_meta_by_root_id_and_preset_id(
                master_ctx.meta.id,
                preset_id,
            )
        if len(slaves) > 0:
            return next(iter(slaves.values()))
        slave = self.build()

        if master_ctx.meta is not None:
            slave.root_id = master_ctx.meta.id
            slave.parent_id = master_ctx.meta.id

        slave.preset = preset_id
        id = self.provider.create(slave)
        slave.id = id
        return slave

    def get_prev(self) -> Optional[int]:
        """
        Get previous context

        :return: previous context
        """
        if self.current is None:
            return None
        idx = self.get_idx_by_id(self.current)
        if idx is not None and idx > 0:
            return self.get_id_by_idx(idx - 1)

    def get_next(self) -> Optional[int]:
        """
        Get next context

        :return: next context
        """
        if self.current is None:
            return None
        idx = self.get_idx_by_id(self.current)
        if idx is not None and idx < self.count_meta() - 1:
            return self.get_id_by_idx(idx + 1)

    def get_last_meta(self) -> Optional[int]:
        """
        Get last context

        :return: last meta
        """
        return self.provider.get_last_meta_id()

    @staticmethod
    def _part_tool_calls(
            part: CtxItemPart,
            legacy_calls: Optional[list] = None,
            tool_round: Optional[int] = None,
    ) -> list:
        """Normalize persisted part tasks to provider-compatible tool calls.

        ``tool_call_id`` is the protocol call ID. Provider-specific output-item
        IDs (notably OpenAI Responses' ``fc_*`` IDs) live in ``extra.tool_item_id``.
        ``legacy_calls`` is used only to repair rows written by early versions of
        the partial-item migration which stored ``id`` instead of ``call_id``.
        """
        calls = []
        legacy_calls = legacy_calls if isinstance(legacy_calls, list) else []
        for task in getattr(part, "tasks", None) or []:
            extra = task.extra if isinstance(task.extra, dict) else {}
            if extra.get("provider_history") is False:
                continue
            if not task.tool_call_id and not extra.get("tool_name"):
                continue
            if tool_round is not None and Ctx._task_tool_round(task) != int(tool_round):
                continue
            name = str(extra.get("tool_name") or task.task_name or task.name or "tool")
            args = task.tool_input if task.tool_input not in (None, "") else task.input
            protocol_call_id = str(task.tool_call_id or task.uuid)
            item_id = str(extra.get("tool_item_id") or protocol_call_id)
            tool_type = str(extra.get("tool_type") or "function")

            # Compatibility repair for rows created before call_id and id were
            # separated. The current durable item's legacy tool_calls cache still
            # contains both identifiers for the active/latest tool round.
            if protocol_call_id.startswith("fc_"):
                for legacy in legacy_calls:
                    if not isinstance(legacy, dict):
                        continue
                    legacy_id = str(legacy.get("id") or "")
                    legacy_call_id = str(legacy.get("call_id") or "")
                    legacy_fn = legacy.get("function") if isinstance(legacy.get("function"), dict) else {}
                    if legacy_id == protocol_call_id and legacy_call_id:
                        protocol_call_id = legacy_call_id
                        item_id = legacy_id
                        tool_type = str(legacy.get("type") or tool_type)
                        if not name and legacy_fn.get("name"):
                            name = str(legacy_fn.get("name"))
                        break

            calls.append({
                "id": item_id,
                "call_id": protocol_call_id,
                "type": tool_type,
                "function": {
                    "name": name,
                    "arguments": args if args is not None else {},
                },
            })
        return calls

    @staticmethod
    def _part_tool_outputs(part: CtxItemPart, tool_round: Optional[int] = None) -> list:
        """Return persisted structured tool responses for one partial item.

        New partial-task rows store the full JSON response produced by the
        plugin/tool loop. Rebuild a provider-friendly payload from that stored
        structure, preserving request/result metadata and backfilling the legacy
        top-level ``cmd`` key for older provider adapters.
        """
        outputs = []
        for task in getattr(part, "tasks", None) or []:
            extra = task.extra if isinstance(task.extra, dict) else {}
            if extra.get("provider_history") is False:
                continue
            if not task.tool_call_id and not extra.get("tool_name"):
                continue
            if tool_round is not None and Ctx._task_tool_round(task) != int(tool_round):
                continue
            completed = (
                task.tool_output is not None
                or (isinstance(task.extra, dict) and task.extra.get("status") == "completed")
            )
            if not completed:
                continue

            tool_name = str((task.extra or {}).get("tool_name") or task.task_name or task.name or "tool")
            stored = copy.deepcopy(task.tool_output)
            if isinstance(stored, dict):
                if "request" not in stored or not isinstance(stored.get("request"), dict):
                    stored["request"] = {"cmd": tool_name, "params": copy.deepcopy(task.tool_input or {})}
                else:
                    stored["request"].setdefault("cmd", tool_name)
                    stored["request"].setdefault("params", copy.deepcopy(task.tool_input or {}))
                if "cmd" not in stored:
                    stored["cmd"] = str(stored.get("request", {}).get("cmd") or tool_name)
                if "result" not in stored:
                    stored["result"] = task.output
                outputs.append(stored)
                continue

            result = stored if stored is not None else task.output
            outputs.append({
                "cmd": tool_name,
                "request": {
                    "cmd": tool_name,
                    "params": copy.deepcopy(task.tool_input or {}),
                },
                "result": result,
            })
        return outputs

    def expand_history_item(self, item: CtxItem) -> List[CtxItem]:
        """Project one durable turn to provider-facing protocol segments.

        A DB partial is a text fragment and may contain many sequential tool
        rounds. Those rounds are expanded only in memory so providers still see
        assistant-call -> tool-result ordering without extra ctx_item_partial rows.
        """
        parts = list(getattr(item, "parts", None) or [])
        if not parts:
            return [item]

        usable = []
        for part in parts:
            extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
            if extra.get("provider_history") is False or extra.get("agents_v2_worker") is True:
                continue
            if (getattr(part, "output", None) not in (None, "")
                    or bool(getattr(part, "tasks", None))):
                usable.append(part)
        if not usable:
            return [item]

        expanded: List[CtxItem] = []
        previous_clone = None
        previous_calls = []
        previous_outputs = []
        first_segment = True
        pack_cmds = self.window.core.command.pack_cmds
        to_cmds = self.window.core.command.tool_calls_to_cmds
        legacy_calls = item.extra.get("tool_calls") if isinstance(item.extra, dict) else None

        def build_tool_input(calls, outputs):
            if not outputs:
                return None
            values = []
            for call, value in zip(calls or [], outputs or []):
                if not isinstance(value, dict):
                    value = {"result": value}
                request = value.get("request") if isinstance(value.get("request"), dict) else {}
                values.append({
                    "request": {
                        "cmd": value.get("cmd") or request.get("cmd") or call.get("function", {}).get("name"),
                        "params": request.get("params", call.get("function", {}).get("arguments", {})),
                    },
                    "result": value.get("result", value),
                })
            return json.dumps(values, ensure_ascii=False, default=str)

        for part in usable:
            round_ids = self._part_tool_round_ids(part)
            raw_text = str(getattr(part, "output", None) or "")
            part_extra = part.extra if isinstance(part.extra, dict) else {}
            try:
                text_after_round = int(part_extra.get("text_after_tool_round", 0) or 0)
            except (TypeError, ValueError):
                text_after_round = 0
            text_emitted = False

            segments = []
            if round_ids:
                for round_id in round_ids:
                    calls = self._part_tool_calls(part, legacy_calls, tool_round=round_id)
                    outputs = self._part_tool_outputs(part, tool_round=round_id)
                    segment_text = ""
                    if raw_text and not text_emitted and round_id > text_after_round:
                        segment_text = raw_text
                        text_emitted = True
                    segments.append((segment_text, calls, outputs))
                if raw_text and not text_emitted:
                    segments.append((raw_text, [], []))
                    text_emitted = True
            else:
                segments.append((raw_text, [], []))
                text_emitted = bool(raw_text)

            for segment_text, calls, outputs in segments:
                if not segment_text and not calls:
                    continue
                clone = copy.copy(item)
                clone.parts = []
                clone.active_part = None
                clone.turn_parent = None
                clone.turn_part = None
                clone.turn_previous_part = None
                clone.turn_continuation = False
                clone.prev_ctx = previous_clone
                clone.extra = copy.deepcopy(item.extra) if isinstance(item.extra, dict) else {}
                clone.cmds = []
                clone.cmds_before = []
                clone.tool_calls = []
                clone.hidden_output = None

                if first_segment:
                    clone.input = item.input
                    clone.hidden_input = item.hidden_input
                    first_segment = False
                else:
                    clone.input = build_tool_input(previous_calls, previous_outputs)
                    clone.hidden_input = None
                    clone.internal = True

                clone.output = segment_text or ""
                if calls:
                    clone.output += pack_cmds(to_cmds(calls))
                    clone.tool_calls = copy.deepcopy(calls)
                    clone.extra["tool_calls"] = copy.deepcopy(calls)
                    clone.extra["prev_tool_calls"] = copy.deepcopy(calls)
                    if outputs:
                        clone.extra["tool_output"] = copy.deepcopy(outputs)
                    else:
                        clone.extra.pop("tool_output", None)
                else:
                    clone.extra.pop("tool_calls", None)
                    clone.extra.pop("tool_output", None)
                    clone.extra.pop("prev_tool_calls", None)

                expanded.append(clone)
                previous_clone = clone
                previous_calls = calls
                previous_outputs = outputs

        if expanded:
            expanded[-1].hidden_output = item.hidden_output
        return expanded or [item]

    def expand_history(self, history_items: List[CtxItem]) -> List[CtxItem]:
        """Project durable context turns to provider-facing history items."""
        result: List[CtxItem] = []
        for item in history_items:
            result.extend(self.expand_history_item(item))
        return result

    def count_history(
            self,
            history_items: List[CtxItem],
            model: str,
            mode: str,
            used_tokens: int = 100,
            max_tokens: int = 1000
    ) -> Tuple[int, int]:
        """
        Count ctx items to add to prompt

        :param history_items: history items list
        :param model: model
        :param mode: mode
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :return: ctx items count, ctx tokens count
        """
        i = 0
        tokens = used_tokens
        context_tokens = 0
        from_ctx = self.window.core.tokens.from_ctx
        expanded_items = self.expand_history(history_items)
        for item in reversed(expanded_items):
            num = from_ctx(item, mode, model)
            new_total = tokens + num
            if 0 < max_tokens < new_total:
                break
            tokens = new_total
            context_tokens += num
            i += 1

        return i, context_tokens

    def get_history(
            self,
            history_items: List[CtxItem],
            model: str,
            mode: str = MODE_CHAT,
            used_tokens: int = 100,
            max_tokens: int = 1000,
            ignore_first: bool = True
    ) -> list:
        """
        Return ctx items to add to prompt

        :param history_items: history items list
        :param model: model
        :param mode: mode
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :param ignore_first: ignore current item (provided by user)
        :return: ctx items list
        """
        items = []
        tokens = used_tokens
        # Ignore the current durable turn before expansion. Otherwise a single
        # turn containing multiple partials would accidentally skip only its last
        # protocol fragment instead of the whole current item.
        source_items = history_items[:-1] if ignore_first and history_items else history_items
        expanded_items = self.expand_history(source_items)
        from_ctx = self.window.core.tokens.from_ctx
        for item in reversed(expanded_items):
            cost = from_ctx(item, mode, model)
            new_total = tokens + cost
            if 0 < max_tokens < new_total:
                break
            tokens = new_total
            items.append(item)

        items.reverse()
        return items

    def count_prompt_items(
            self,
            model: str,
            mode: str,
            used_tokens: int = 100,
            max_tokens: int = 1000
    ) -> Tuple[int, int]:
        """
        Count ctx items to add to prompt

        :param model: model
        :param mode: mode
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :return: ctx items count, ctx tokens count
        """
        return self.count_history(
            self.get_items(),
            model,
            mode,
            used_tokens,
            max_tokens,
        )

    def get_prompt_items(
            self,
            model: str,
            mode: str = MODE_CHAT,
            used_tokens: int = 100,
            max_tokens: int = 1000,
            ignore_first: bool = True
    ) -> list:
        """
        Return ctx items to add to prompt

        :param model: model
        :param mode: mode
        :param used_tokens: used tokens
        :param max_tokens: max tokens
        :param ignore_first: ignore current item (provided by user)
        :return: ctx items list
        """
        return self.get_history(
            self.get_items(),
            model,
            mode,
            used_tokens,
            max_tokens,
            ignore_first,
        )

    def get_all_items(self, ignore_first: bool = True) -> list:
        """
        Return all ctx items

        :param ignore_first: ignore current item (provided by user)
        :return: ctx items list
        """
        items = self.get_items()
        if ignore_first:
            return items[:-1]
        return items[:]

    def check(self, threshold: int, max_total: int):
        """
        Check context and clear if limit exceeded

        :param threshold: threshold
        :param max_total: max total tokens
        """
        if self.get_tokens_left(max_total) <= threshold:
            self.remove_first()

    def get_tokens_left(self, max: int) -> int:
        """
        Return remaining tokens in context

        :param max: max tokens
        :return: remaining tokens in context
        """
        return max - self.get_total_tokens()

    def get_total_tokens(self) -> int:
        """
        Return current prompt tokens

        :return: total tokens
        """
        last = self.get_last()
        if last is not None:
            return last.total_tokens
        return 0

    def get_last_tokens(self) -> int:
        """
        Return last tokens count

        :return: last tokens
        """
        return self.get_total_tokens()

    def remove_last(self):
        """Remove last item"""
        items = self.get_items()
        if items:
            items.pop()

    def duplicate(self, id: int) -> int:
        """
        Duplicate ctx and return new ctx id

        :param id: ctx id
        :return: new ctx id
        """
        if id in self.meta:
            meta = self.create(self.meta[id].group_id)
            new_id = meta.id
            old_data = self.meta[id].to_dict()
            meta.from_dict(old_data)
            meta.id = new_id
            items = self.load(id)
            self.provider.save_all(meta.id, meta, items)
            return meta.id

    def remove_first(self):
        """Remove first item"""
        items = self.get_items()
        if items:
            items.pop(0)

    def set_display_filters(self, filters: dict):
        """
        Update current display filters

        :param filters: filters dict
        """
        self.filters = filters

    def is_allowed_for_mode(
            self,
            mode: str,
            check_assistant: bool = True
    ) -> bool:
        """
        Check if ctx is allowed for this mode

        :param mode: mode name
        :param check_assistant: True if check also current assistant
        :return: True if allowed for mode
        """
        if not self.window.core.config.get('lock_modes'):
            return True

        if self.is_empty():
            return True

        if self.current is None or self.current == '' or not self.has(self.current):
            return True

        meta = self.get_meta_by_id(self.current)

        if meta.last_mode is None:
            return True

        prev_mode = meta.last_mode
        if prev_mode not in self.allowed_modes[mode]:
            if mode == MODE_ASSISTANT:
                if meta.assistant is not None:
                    if meta.assistant == self.window.core.config.get('assistant'):
                        return True
                else:
                    return True
            return False

        if mode == MODE_ASSISTANT and check_assistant:
            if meta.assistant is None:
                return True
            if meta.assistant != self.window.core.config.get('assistant'):
                return False
        return True

    def has_labels(self) -> bool:
        """
        Check if label query is needed

        :return: True if labels not default
        """
        num_all = len(self.window.controller.ui.get_colors())
        return len(self.filters_labels) < num_all

    def load_meta(self):
        """Load ctx list: pinned and grouped unlimited; ungrouped not pinned paginated directly in SQL."""
        # base package size (per page)
        base_limit = 0
        if self.window.core.config.has('ctx.records.limit'):
            try:
                base_limit = int(self.window.core.config.get('ctx.records.limit') or 0)
            except Exception:
                base_limit = 0

        # total loaded (persisted); fallback to base when missing
        try:
            loaded_total = int(self.window.core.config.get('ctx.records.limit.total') or 0)
        except Exception:
            loaded_total = 0
        if loaded_total <= 0:
            loaded_total = base_limit

        # Common filters (labels etc.)
        common_filters = self.get_parsed_filters()

        # If explicit filters target a narrow subset (legacy path), keep old behavior
        if "is_important" in self.filters or "indexed_ts" in self.filters:
            limit = 0 if base_limit == 0 else loaded_total
            self.meta = self.provider.get_meta(
                search_string=self.search_string,
                order_by='updated_ts',
                order_direction='DESC',
                limit=limit,
                offset=0,
                filters=common_filters,
                search_content=self.is_search_content(),
            )
            return

        # 1) Pinned (important) – unlimited
        filters_pinned = self.get_parsed_filters()
        filters_pinned['is_important'] = {"mode": "=", "value": 1}
        meta_pinned = self.provider.get_meta(
            search_string=self.search_string,
            order_by='updated_ts',
            order_direction='DESC',
            limit=0,
            offset=0,
            filters=filters_pinned,
            search_content=self.is_search_content(),
        )

        # 2) Grouped – unlimited
        filters_grouped = self.get_parsed_filters()
        filters_grouped['group_id'] = {"mode": ">", "value": 0}
        meta_grouped = self.provider.get_meta(
            search_string=self.search_string,
            order_by='updated_ts',
            order_direction='DESC',
            limit=0,
            offset=0,
            filters=filters_grouped,
            search_content=self.is_search_content(),
        )

        # 3) Ungrouped & not pinned – paginate directly in SQL
        #    If base_limit == 0 -> unlimited (no paging)
        filters_ungrp = self.get_parsed_filters()
        filters_ungrp['is_important'] = {"mode": "=", "value": 0}
        filters_ungrp['group_id'] = {"mode": "NULL_OR_ZERO", "value": 0}  # special mode handled in Storage

        if base_limit <= 0:
            meta_ungrouped = self.provider.get_meta(
                search_string=self.search_string,
                order_by='updated_ts',
                order_direction='DESC',
                limit=0,         # unlimited
                offset=0,
                filters=filters_ungrp,
                search_content=self.is_search_content(),
            )
        else:
            # Always take the top-N ungrouped newest items directly from DB
            take = max(0, int(loaded_total or 0))
            meta_ungrouped = self.provider.get_meta(
                search_string=self.search_string,
                order_by='updated_ts',
                order_direction='DESC',
                limit=take,
                offset=0,
                filters=filters_ungrp,
                search_content=self.is_search_content(),
            )

        # Compose final dict with deterministic order: pinned -> grouped -> ungrouped
        combined = {}
        combined.update(meta_pinned)
        combined.update(meta_grouped)
        combined.update(meta_ungrouped)
        self.meta = combined

    def load_tmp_meta(self, meta_id: int):
        """
        Load tmp meta

        :param meta_id: meta id
        """
        meta = self.provider.get_meta(
            order_by='updated_ts',
            order_direction='DESC',
            limit=1,
            filters={
                "id": {
                    "mode": "=",
                    "value": meta_id,
                },
            }
        )
        if len(meta) > 0:
            self.tmp_meta = next(iter(meta.values()))
            if self.tmp_meta.id not in self.meta:
                self.meta = {self.tmp_meta.id: self.tmp_meta, **self.meta}

    def clear_tmp_meta(self):
        """Clear tmp meta"""
        if self.tmp_meta is not None and self.current != self.tmp_meta.id:
            self.tmp_meta = None

    def get_parsed_filters(self) -> dict:
        """
        Get parsed filters

        :return: parsed filters
        """
        filters = copy.deepcopy(self.filters)
        if self.has_labels():
            filters['label'] = {
                "mode": "IN",
                "value": self.filters_labels,
            }
        return filters

    def load(self, id: int) -> List[CtxItem]:
        """
        Load ctx items from provider and append meta to each item

        :param id: ctx id
        :return: ctx items list
        """
        items = self.provider.load(id)
        meta = self.get_meta_by_id(id)
        for item in items:
            item.meta = meta
        return items

    def load_groups(self):
        """Load groups"""
        self.groups = self.provider.get_groups()

    def has_group(self, id: int) -> bool:
        """
        Check if group exists

        :param id: group id
        :return: True if exists
        """
        return id in self.groups

    def get_groups(self) -> Dict[int, CtxGroup]:
        """
        Get groups

        :return: groups
        """
        if not self.groups_loaded:
            self.load_groups()
            self.groups_loaded = True
        return self.groups

    def get_group_by_id(self, id: int) -> Optional[CtxGroup]:
        """
        Get group by ID

        :param id: group id
        :return: group instance
        """
        if not self.groups_loaded:
            self.load_groups()
            self.groups_loaded = True
        if id not in self.groups:
            return None
        return self.groups[id]

    def update_model_in_current(self, model):
        """
        Update model in current context

        :param model: model name
        """
        if self.current is None:
            return
        meta = self.meta.get(self.current)
        if meta is not None:
            meta.last_model = model
            self.save(self.current)

    def remove_group(
            self,
            group: CtxGroup,
            all: bool = False
    ):
        """
        Remove group

        :param group: group instance
        :param all: remove all items
        """
        self.provider.remove_group(group.id, all=all)
        self.load_groups()

    def truncate_groups(self):
        """Remove all groups"""
        self.provider.truncate_groups()
        self.load_groups()

    def make_group(self, name: str) -> CtxGroup:
        """
        Make group

        :param name: group name
        :return: group instance
        """
        group = CtxGroup()
        group.uuid = str(uuid.uuid4())
        group.name = name
        return group

    def insert_group(self, group: CtxGroup) -> int:
        """
        Insert group

        :param group: group instance
        :return: group id
        """
        id = self.provider.insert_group(group)
        self.load_groups()
        return id

    def update_group(self, group: CtxGroup):
        """
        Update group

        :param group: group instance
        """
        self.provider.update_group(group)
        self.load_groups()

    def update_meta_group_id(self, id: int, group_id: int):
        """
        Update meta group ID

        :param id: meta id
        :param group_id: group id
        """
        meta = self.get_meta_by_id(id)
        if meta is None:
            return
        meta.group_id = group_id
        self.provider.update_meta_group_id(id, group_id)
        self.load_groups()

    def get_items_by_id(self, id: int) -> List[str]:
        """
        Get ctx items by id as string list

        :param id: ctx id
        :return: ctx items list
        """
        items = self.provider.load(id)
        data = []
        for item in items:
            data.append("Human: " + str(item.input) + "\n" + "Assistant: " + str(item.output) + "\n")
        return data

    def get_list_in_date_range(
            self,
            search_string: Optional[str] = None,
            limit: int = 0
    ) -> List[Dict[str, Dict]]:
        """
        Get ctx list in date range

        :param search_string: search string
        :param limit: limit
        :return: ctx list
        """
        meta = self.provider.get_meta(
            search_string=search_string,
            order_by='updated_ts',
            order_direction='DESC',
            limit=limit,
            filters={},
            search_content=self.is_search_content(),
        )
        data = []
        for key in meta:
            item = meta[key]
            data.append({key: {
                "subject": item.name,
                "last_updated": datetime.datetime.fromtimestamp(item.updated).strftime('%Y-%m-%d %H:%M:%S'),
            }})
        return data

    def is_search_content(self) -> bool:
        """
        Check if search in content is enabled

        :return: True if enabled
        """
        return bool(self.window.core.config.get('ctx.search_content'))

    def save(self, id: int):
        """
        Save ctx data

        :param id: ctx id
        """
        self.provider.save(id, self.meta[id], self.get_items())

    def store(self):
        """Store current ctx"""
        cur = self.current
        if cur is not None:
            if cur not in self.meta:
                self.load_tmp_meta(cur)
            if cur in self.meta:
                self.save(cur)

    def reset_meta(self, id: int):
        """
        Reset meta

        :param id: meta id
        """
        if id in self.meta:
            self.provider.clear_meta(id)
            self.meta[id].initialized = False
        self.load_meta()

    def as_previous(self, ctx: CtxItem) -> CtxItem:
        """
        Prepare previous context item and clear current reply results

        :param ctx: CtxItem instance (current)
        :return: CtxItem instance (previous)
        """
        prev_ctx = CtxItem()
        for name in (
            "urls", "urls_before", "images", "images_before", "files", "files_before",
            "attachments", "attachments_before", "results", "index_meta", "doc_ids",
            "input_name", "output_name"
        ):
            setattr(prev_ctx, name, copy.deepcopy(getattr(ctx, name)))
        ctx.clear_reply()
        if len(ctx.cmds) == 0:
            ctx.from_previous()
        return prev_ctx

    def dump(self, ctx: CtxItem) -> str:
        """
        Dump context item

        :param ctx: CtxItem instance
        """
        return self.provider.dump(ctx)

    def reset(self):
        """Reset all data"""
        self.meta = {}
        self.clear_items()
        self.current = None
        self.last_item = None
        self.assistant = None
        self.mode = None
        self.model = None
        self.preset = None
        self.run = None
        self.status = None
        self.thread = None
        self.last_mode = None
        self.last_model = None
        self.tmp_meta = None
        self.search_string = None  # search string
        self.groups = {}  # groups
        self.filters = {}  # search filters
        self.filters_labels = []  # search labels
        self.current_cmd = []  # current commands
        self.current_cmd_schema = ""  # current commands schema
        self.current_sys_prompt = ""
        self.groups_loaded = False