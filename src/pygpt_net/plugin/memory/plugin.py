#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.09 19:45:00                  #
# ================================================== #

import threading
from typing import Optional

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base.plugin import BasePlugin

from .config import Config
from .store import Store


class Plugin(BasePlugin):
    UPDATE_SYSTEM_PROMPT = """You maintain a compact long-term memory cache for an AI assistant.
Update the existing memory using the newest completed conversation turn.

Rules:
- Return ONLY the full updated memory content. Do not wrap it in XML, JSON, Markdown fences, or commentary.
- Keep only durable, useful information that is likely to matter in future conversations: stable preferences, ongoing projects, important decisions, constraints, recurring workflows, durable facts, and unresolved follow-ups.
- Do not store routine chatter, temporary details, duplicated facts, transient tool output, or information that is already represented more clearly elsewhere in the memory.
- Merge duplicates, reconcile newer information with older information, and remove obsolete or contradicted details when the new turn clearly supersedes them.
- Treat explicit user instructions to correct, forget, or remove remembered information as authoritative and update the memory accordingly.
- Preserve important existing memory that is still valid even when the new turn does not mention it.
- Organize the memory for fast future use. Prefer concise lines or short grouped sections.
- Keep the complete result within {max_lines} lines. If space is tight, retain the most important and durable information first.
- If the new turn adds nothing worth remembering, return the existing memory unchanged.
"""

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "memory"
        self.name = "Memory"
        self.description = "Provides global and per-project long-term memory backed by the local database."
        self.prefix = "Memory"
        self.order = 3
        self.use_locale = True
        self.allowed_cmds = [
            "memory_get",
            "memory_add",
            "memory_update",
            "memory_clear",
        ]
        self.config = Config(self)
        self.store = Store()
        self.update_lock = threading.Lock()
        self.skip_lock = threading.Lock()
        self.skip_auto_update = set()
        self.init_options()

    def attach(self, window):
        super().attach(window)
        self.store.window = window

    def init_options(self):
        self.config.from_defaults(self)

    def handle(self, event: Event, *args, **kwargs):
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)
        elif name == Event.CMD_EXECUTE:
            self.cmd(ctx, data.get("commands", []))
        elif name == Event.POST_PROMPT:
            data["value"] = self.attach_memory_to_prompt(data.get("value", ""), ctx)
        elif name == Event.CTX_END:
            self.on_ctx_end(ctx)

    def cmd_syntax(self, data: dict):
        for option in self.allowed_cmds:
            if self.has_cmd(option):
                data["cmd"].append(self.get_cmd(option))

    def cmd(self, ctx: CtxItem, cmds: list):
        from .worker import Worker

        my_commands = [
            item for item in (cmds or [])
            if item.get("cmd") in self.allowed_cmds and self.has_cmd(item.get("cmd"))
        ]
        if not my_commands:
            return

        self.cmd_prepare(ctx, my_commands)
        worker = Worker()
        worker.from_defaults(self)
        worker.cmds = my_commands
        worker.ctx = ctx
        if not self.is_async(ctx):
            worker.run()
            return
        worker.run_async()

    def resolve_project_id(self, ctx: Optional[CtxItem] = None) -> Optional[int]:
        """Resolve the stable project/group ID for the context, or None for global scope."""
        meta = getattr(ctx, "meta", None) if ctx is not None else None
        if meta is None and ctx is not None:
            meta_id = getattr(ctx, "meta_id", None)
            if meta_id is not None:
                try:
                    meta = self.window.core.ctx.get_meta_by_id(int(meta_id))
                except (TypeError, ValueError):
                    meta = None
        if meta is None:
            meta = self.window.core.ctx.get_current_meta()

        group_id = getattr(meta, "group_id", None) if meta is not None else None
        try:
            group_id = int(group_id)
        except (TypeError, ValueError):
            return None
        return group_id if group_id > 0 else None

    def get_max_lines(self) -> int:
        try:
            return max(1, int(self.get_option_value("max_lines") or 300))
        except (TypeError, ValueError):
            return 300

    def limit_lines(self, content: str, keep: str = "first") -> str:
        content = str(content or "").strip()
        if not content:
            return ""
        lines = content.splitlines()
        limit = self.get_max_lines()
        if len(lines) <= limit:
            return content
        if keep == "last":
            lines = lines[-limit:]
        else:
            lines = lines[:limit]
        return "\n".join(lines).strip()

    def get_memory(self, project_id: Optional[int] = None) -> str:
        return self.store.get(project_id)

    def add_memory(self, text: str, project_id: Optional[int] = None) -> str:
        addition = str(text or "").strip()
        if not addition:
            return self.store.get(project_id)
        with self.update_lock:
            current = self.store.get(project_id)
            merged = addition if not current.strip() else current.rstrip() + "\n" + addition
            merged = self.limit_lines(merged, keep="last")
            return self.store.set(merged, project_id)

    def update_memory(self, text: str, project_id: Optional[int] = None) -> str:
        content = self.limit_lines(str(text or ""), keep="first")
        if not content:
            return self.store.get(project_id)
        with self.update_lock:
            return self.store.set(content, project_id)

    def clear_memory(self, project_id: Optional[int] = None) -> bool:
        with self.update_lock:
            return self.store.clear(project_id)

    def should_auto_attach(self, project_id: Optional[int]) -> bool:
        if self.get_option_value("auto_attach"):
            return True
        if project_id is not None and self.get_option_value("auto_attach_project"):
            return True
        return False

    def attach_memory_to_prompt(self, prompt: str, ctx: Optional[CtxItem] = None) -> str:
        prompt = str(prompt or "")
        if "<context_memory>" in prompt:
            return prompt
        project_id = self.resolve_project_id(ctx)
        if not self.should_auto_attach(project_id):
            return prompt
        content = self.get_memory(project_id).strip()
        if not content:
            return prompt
        block = f"<context_memory>\n{content}\n</context_memory>"
        if prompt.strip():
            return prompt.rstrip() + "\n\n" + block
        return block

    def _auto_update_key(
            self,
            ctx: Optional[CtxItem],
            project_id: Optional[int],
    ):
        meta_id = getattr(ctx, "meta_id", None) if ctx is not None else None
        try:
            if meta_id is not None:
                return ("meta", int(meta_id))
        except (TypeError, ValueError):
            pass
        return ("scope", int(project_id) if project_id is not None else 0)

    def skip_next_auto_update(self, ctx: Optional[CtxItem], project_id: Optional[int]):
        key = self._auto_update_key(ctx, project_id)
        with self.skip_lock:
            self.skip_auto_update.add(key)

    def consume_auto_update_skip(self, ctx: Optional[CtxItem], project_id: Optional[int]) -> bool:
        key = self._auto_update_key(ctx, project_id)
        with self.skip_lock:
            if key not in self.skip_auto_update:
                return False
            self.skip_auto_update.remove(key)
            return True

    def build_turn_snapshot(self, ctx: Optional[CtxItem]) -> str:
        if ctx is None:
            return ""
        if getattr(ctx, "internal", False) or getattr(ctx, "sub_call", False):
            return ""
        if getattr(ctx, "stopped", False):
            return ""
        input_text = str(getattr(ctx, "input", "") or "").strip()
        output_text = str(getattr(ctx, "output", "") or "").strip()
        if not input_text or not output_text:
            return ""
        return f"Input:\n{input_text}\n\nOutput:\n{output_text}"

    def on_ctx_end(self, ctx: Optional[CtxItem]):
        project_id = self.resolve_project_id(ctx)
        if self.consume_auto_update_skip(ctx, project_id):
            return
        snapshot = self.build_turn_snapshot(ctx)
        if not snapshot:
            return
        from .worker import UpdateWorker
        worker = UpdateWorker(self, snapshot=snapshot, project_id=project_id)
        worker.run_async()

    def get_update_model(self):
        model = self.window.core.models.from_defaults()
        model_id = self.get_option_value("model_update")
        if model_id and self.window.core.models.has(model_id):
            model = self.window.core.models.get(model_id)
        return model

    def build_update_input(self, current: str, snapshot: str) -> str:
        current = str(current or "").strip()
        if not current:
            current = "(empty)"
        return (
            "<existing_memory>\n"
            + current
            + "\n</existing_memory>\n\n<new_completed_turn>\n"
            + str(snapshot or "").strip()
            + "\n</new_completed_turn>"
        )

    def clean_model_memory(self, content: str) -> str:
        text = str(content or "").strip()
        if text.startswith("```") and text.endswith("```"):
            lines = text.splitlines()
            if len(lines) >= 2:
                lines = lines[1:-1]
                text = "\n".join(lines).strip()
        if text.startswith("<context_memory>") and text.endswith("</context_memory>"):
            text = text[len("<context_memory>"):-len("</context_memory>")].strip()
        return text
