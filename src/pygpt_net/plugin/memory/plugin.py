#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 15:15:00                  #
# ================================================== #

import threading
from typing import Optional

from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base.plugin import BasePlugin

from .config import Config
from .store import KeyStore, Store


class Plugin(BasePlugin):
    UPDATE_SYSTEM_PROMPT = """You maintain a compact long-term memory cache for an AI assistant.
Update the existing memory using the newest completed conversation turn.

Rules:
- Return ONLY the full updated memory content. Do not wrap it in XML, JSON, Markdown fences, or commentary.
- Keep only durable, useful information that is likely to matter in future conversations: stable preferences, ongoing projects, important decisions, constraints, recurring workflows, durable facts, and unresolved follow-ups.
- Do not store routine chatter, temporary details, duplicated facts, transient tool output, or information that is already represented more clearly elsewhere in the memory.
- Treat memory as a canonical compact state, not an append-only log. Before creating a new line, look for an existing entry about the same subject, entity, preference, plan, task, or time frame and merge compatible information into that entry whenever possible.
- Prefer contextual consolidation over accumulation. For example, if memory says "User tomorrow will buy beer" and the new information says "User tomorrow will also buy pizza", rewrite the existing fact as "User tomorrow will buy beer and pizza" instead of keeping two separate lines.
- Merge duplicates, reconcile newer information with older information, and remove obsolete or contradicted details when the new turn clearly supersedes them.
- Treat explicit user instructions to correct, forget, or remove remembered information as authoritative and update the memory accordingly.
- Preserve important existing memory that is still valid even when the new turn does not mention it.
- Organize the memory for fast future use. Prefer concise lines or short grouped sections.
- Keep the complete result within approximately {max_chars} characters. If space is tight, retain the most important and durable information first.
- If the new turn adds nothing worth remembering, return the existing memory unchanged.
"""

    GLOBAL_UPDATE_SYSTEM_PROMPT = """You maintain a compact long-term global memory about the user who is talking with the AI assistant.
Update the existing memory using the newest completed conversation turn.

The purpose of this global memory is to preserve the most important durable information ABOUT THE USER so future conversations can be better personalized and do not require the user to repeat important context.

Rules:
- Return ONLY the full updated memory content. Do not wrap it in XML, JSON, Markdown fences, or commentary.
- Prioritize durable user information: stable preferences, communication style, technical level, interests, background, recurring habits and workflows, long-term goals, persistent constraints, important decisions, frequently used technologies/tools, and other facts that are likely to remain useful across unrelated future conversations.
- Prefer information explicitly stated by the user. Do not turn weak guesses, temporary behavior, or assistant speculation into facts about the user.
- Keep information about a specific task, temporary debugging session, one-off request, transient tool output, or short-lived project detail only when it reveals a durable and broadly useful fact about the user.
- Do not preserve routine chatter, generic assistant output, duplicated facts, or details that are useful only inside one conversation.
- Treat memory as a canonical compact state, not an append-only log. Before creating a new line, look for an existing entry about the same subject, entity, preference, plan, task, or time frame and merge compatible information into that entry whenever possible.
- Prefer contextual consolidation over accumulation. For example, if memory says "User tomorrow will buy beer" and the new information says "User tomorrow will also buy pizza", rewrite the existing fact as "User tomorrow will buy beer and pizza" instead of keeping two separate lines.
- Merge duplicates, reconcile newer information with older information, and remove obsolete or contradicted details when the new turn clearly supersedes them.
- Treat explicit user instructions to correct, forget, or remove remembered information as authoritative and update the memory accordingly.
- Preserve important existing user information that is still valid even when the new turn does not mention it.
- Organize the memory for fast future use. Prefer concise lines or short grouped sections.
- Keep the complete result within approximately {max_chars} characters. If space is tight, retain the most important, stable, and broadly reusable information about the user first.
- If the new turn adds nothing important about the user, return the existing memory unchanged.
"""

    ADD_SYSTEM_PROMPT = """You maintain a compact long-term memory cache for an AI assistant.
Merge a selected important memory addition into the existing memory and rewrite the complete memory when useful.

Rules:
- Return ONLY the full updated memory content. Do not wrap it in XML, JSON, Markdown fences, or commentary.
- memory_add is intended for selective, high-value memory writes, not routine logging. Preserve the addition only if it is important enough to be useful later; if it is plainly routine, temporary, redundant, or low-value, return the existing memory unchanged.
- The content inside <memory_addition> is the candidate information to incorporate into memory.
- Integrate it naturally with existing information instead of blindly appending raw text.
- Preserve important existing memory that remains valid.
- Treat memory as a canonical compact state, not an append-only log. Before creating a new line, look for an existing entry about the same subject, entity, preference, plan, task, or time frame and merge compatible information into that entry whenever possible.
- Prefer contextual consolidation over accumulation. For example, if memory says "User tomorrow will buy beer" and the new information says "User tomorrow will also buy pizza", rewrite the existing fact as "User tomorrow will buy beer and pizza" instead of keeping two separate lines.
- Merge duplicates, reconcile compatible facts, and replace older information when the addition clearly supersedes it.
- Keep the memory concise, structured, and useful for future conversations.
- Aim to keep the complete result within approximately {max_chars} characters. This is a target, not a reason to drop important information from the requested addition.
- Prefer concise lines or short grouped sections and remove redundant wording when space is tight.
"""

    GLOBAL_ADD_SYSTEM_PROMPT = """You maintain a compact long-term global memory about the user who is talking with the AI assistant.
Merge a selected important memory addition into the existing global user memory and rewrite the complete memory when useful.

Rules:
- Return ONLY the full updated memory content. Do not wrap it in XML, JSON, Markdown fences, or commentary.
- memory_add is intended for selective, high-value memory writes, not routine logging. Preserve the addition only if it is an important, durable fact about the user that is likely to matter across future conversations; if it is plainly routine, temporary, redundant, or low-value, return the existing memory unchanged.
- The content inside <memory_addition> is the candidate information to incorporate into memory.
- Integrate it naturally with existing information instead of blindly appending raw text.
- Preserve important existing user information that remains valid.
- Prefer durable facts about the user: stable preferences, communication style, technical level, interests, background, recurring workflows, long-term goals, persistent constraints, important decisions, and frequently used technologies or tools.
- Do not convert assistant speculation into facts about the user.
- Treat memory as a canonical compact state, not an append-only log. Before creating a new line, look for an existing entry about the same subject, entity, preference, plan, task, or time frame and merge compatible information into that entry whenever possible.
- Prefer contextual consolidation over accumulation. For example, if memory says "User tomorrow will buy beer" and the new information says "User tomorrow will also buy pizza", rewrite the existing fact as "User tomorrow will buy beer and pizza" instead of keeping two separate lines.
- Merge duplicates, reconcile compatible facts, and replace older information when the addition clearly supersedes it.
- Keep the memory concise, structured, and useful across unrelated future conversations.
- Aim to keep the complete result within approximately {max_chars} characters. This is a target, not a reason to drop important information from the requested addition.
- Prefer concise lines or short grouped sections and remove redundant wording when space is tight.
"""

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "memory"
        self.name = "Memory (inline)"
        self.type = ["cmd.inline"]
        self.description = "Provides global and per-project long-term memory backed by the local database."
        self.prefix = "Memory"
        self.order = 3
        self.use_locale = True
        self.allowed_cmds = [
            "memory_get",
            "memory_add",
            "memory_update",
            "memory_clear",
            "memory_key_get",
            "memory_key_add",
            "memory_key_append",
            "memory_key_update",
            "memory_key_list",
            "memory_key_search",
            "memory_key_remove",
        ]
        self.config = Config(self)
        self.store = Store()
        self.key_store = KeyStore()
        self.update_lock = threading.Lock()
        self.skip_lock = threading.Lock()
        self.skip_auto_update = set()
        self.init_options()

    def attach(self, window):
        super().attach(window)
        self.store.window = window
        self.key_store.window = window

    def init_options(self):
        self.config.from_defaults(self)

    def handle(self, event: Event, *args, **kwargs):
        name = event.name
        data = event.data
        ctx = event.ctx

        if name in [
            Event.CMD_SYNTAX,
            Event.CMD_SYNTAX_INLINE,
        ]:
            self.cmd_syntax(data)
        elif name in [
            Event.CMD_EXECUTE,
            Event.CMD_INLINE,
        ]:
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

    def get_max_chars(self) -> int:
        try:
            return max(1, int(self.get_option_value("max_chars") or 15000))
        except (TypeError, ValueError):
            return 15000

    def get_hard_max_chars(self) -> int:
        """Return the storage safety limit (configured target + 300 characters)."""
        return self.get_max_chars() + 300

    def limit_chars(self, content: str, keep: str = "first") -> str:
        """Apply the hard character safety limit without any line-based truncation."""
        content = str(content or "").strip()
        if not content:
            return ""

        char_limit = self.get_hard_max_chars()
        if len(content) > char_limit:
            if keep == "last":
                content = content[-char_limit:]
            else:
                content = content[:char_limit]
            content = content.strip()

        return content

    def should_refine_add(self) -> bool:
        return bool(self.get_option_value("refine_add"))

    def get_memory(self, project_id: Optional[int] = None) -> str:
        return self.store.get(project_id)

    def add_memory(self, text: str, project_id: Optional[int] = None) -> str:
        addition = str(text or "").strip()
        if not addition:
            return self.store.get(project_id)
        with self.update_lock:
            current = self.store.get(project_id)
            merged = addition if not current.strip() else current.rstrip() + "\n" + addition
            merged = self.limit_chars(merged, keep="last")
            return self.store.set(merged, project_id)

    def update_memory(self, text: str, project_id: Optional[int] = None) -> str:
        content = self.limit_chars(str(text or ""), keep="first")
        if not content:
            return self.store.get(project_id)
        with self.update_lock:
            return self.store.set(content, project_id)

    def clear_memory(self, project_id: Optional[int] = None) -> bool:
        with self.update_lock:
            return self.store.clear(project_id)

    def should_search_key_content(self) -> bool:
        return bool(self.get_option_value("key_search_content"))

    def get_memory_keys(self, keys, project_id: Optional[int] = None) -> list[dict]:
        return self.key_store.get(keys, project_id)

    def add_memory_key(self, key: str, content: str, project_id: Optional[int] = None) -> dict:
        return self.key_store.add(key, content, project_id)

    def append_memory_key(self, key: str, content: str, project_id: Optional[int] = None) -> dict:
        return self.key_store.append(key, content, project_id)

    def update_memory_key(self, key: str, content: str, project_id: Optional[int] = None) -> dict:
        return self.key_store.update(key, content, project_id)

    def list_memory_keys(self, project_id: Optional[int] = None) -> list[str]:
        return self.key_store.list_keys(project_id)

    def search_memory_keys(self, query: str, project_id: Optional[int] = None) -> list[dict]:
        return self.key_store.search(
            query,
            project_id,
            search_content=self.should_search_key_content(),
        )

    def remove_memory_keys(self, keys, project_id: Optional[int] = None) -> list[str]:
        return self.key_store.remove(keys, project_id)

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

    def get_update_system_prompt(self, project_id: Optional[int]) -> str:
        """Return the updater prompt for project-scoped or global memory."""
        if project_id is None:
            return self.GLOBAL_UPDATE_SYSTEM_PROMPT.format(
                max_chars=self.get_max_chars()
            )
        return self.UPDATE_SYSTEM_PROMPT.format(
            max_chars=self.get_max_chars()
        )

    def get_add_system_prompt(self, project_id: Optional[int]) -> str:
        """Return the merge prompt used by memory_add."""
        if project_id is None:
            return self.GLOBAL_ADD_SYSTEM_PROMPT.format(
                max_chars=self.get_max_chars()
            )
        return self.ADD_SYSTEM_PROMPT.format(
            max_chars=self.get_max_chars()
        )

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

    def build_add_input(self, current: str, addition: str) -> str:
        current = str(current or "").strip()
        if not current:
            current = "(empty)"
        return (
            "<existing_memory>\n"
            + current
            + "\n</existing_memory>\n\n<memory_addition>\n"
            + str(addition or "").strip()
            + "\n</memory_addition>"
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
