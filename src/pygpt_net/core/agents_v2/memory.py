#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import copy
import html
import re
from typing import List, Optional

from llama_index.core.base.llms.types import ChatMessage, MessageRole

from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.types import MODE_AGENT_V2


class OrchestratorMemoryStore:
    """Persist only Primary-Agent-facing turns in a hidden child context."""

    PREFIX = "agents_v2.memory:"

    def __init__(self, window):
        self.window = window

    def _preset_key(self, preset) -> str:
        if preset is None:
            return self.PREFIX + "default"
        value = getattr(preset, "uuid", None) or getattr(preset, "filename", None) or "default"
        return self.PREFIX + str(value)

    def get_meta(self, master_ctx: CtxItem, preset):
        return self.window.core.ctx.get_or_create_slave_meta(master_ctx, self._preset_key(preset))

    @staticmethod
    def _compact_legacy_output(value: str) -> str:
        """Extract one useful assistant answer from pre-fix full-trace memory."""
        text = str(value or "").strip()
        if not text:
            return ""
        final = re.findall(
            r"<final_answer(?:\s+[^>]*)?>\s*(.*?)\s*</final_answer>",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if final:
            return str(final[-1]).strip()
        outputs = re.findall(
            r"<orchestrator_output(?:\s+[^>]*)?>\s*(.*?)\s*</orchestrator_output>",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if outputs:
            return str(outputs[-1]).strip()
        return text

    @staticmethod
    def _worker_context_records(part) -> list:
        """Return normalized worker finals stored on one orchestrator partial."""
        extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
        values = extra.get("worker_context")
        legacy = False
        if not isinstance(values, list):
            values = extra.get("worker_outputs")
            legacy = True
        if not isinstance(values, list):
            return []

        result = []
        for value in values:
            if not isinstance(value, dict):
                continue
            output = value.get("output")
            if output is None and legacy:
                output = value.get("output_text")
            created_at = value.get("created_at")
            if created_at is None and legacy:
                created_at = value.get("output_created_at")
            try:
                created_at = int(created_at or 0)
            except (TypeError, ValueError):
                created_at = 0
            record = {
                "id": str(value.get("id") or (value.get("worker_id") if legacy else "") or ""),
                "name": str(value.get("name") or (value.get("worker_name") if legacy else "") or ""),
                "input": str(value.get("input") or (value.get("task") if legacy else "") or ""),
                "output": str(output or ""),
                "created_at": created_at,
            }
            result.append(record)
        result.sort(key=lambda item: item["created_at"])
        return result

    @staticmethod
    def _worker_context_block(record: dict) -> str:
        output = str(record.get("output") or "").strip()
        if not output:
            return ""
        name = html.escape(str(record.get("name") or record.get("id") or "Worker"), quote=True)
        return f'<worker_context="{name}">\n{output}\n</worker_context>'

    def _compose_source_history(self, source: Optional[CtxItem]) -> str:
        """Rebuild exactly the Primary-Agent-facing prose/specialist chronology.

        This projection is model-only.  ``worker_context`` lives in partial.extra
        and is never appended to CtxItem.output, so the chat renderer continues to
        display only the normal Primary Agent partials/tool UI.
        """
        if source is None:
            return ""
        parts = list(getattr(source, "parts", None) or [])
        if not parts:
            return ""

        def part_key(part):
            try:
                created = int(getattr(part, "created_at", 0) or 0)
            except (TypeError, ValueError):
                created = 0
            try:
                row_id = int(getattr(part, "id", 0) or 0)
            except (TypeError, ValueError):
                row_id = 0
            return created, row_id

        chunks = []
        for part in sorted(parts, key=part_key):
            extra = part.extra if isinstance(getattr(part, "extra", None), dict) else {}
            if extra.get("provider_history") is False or extra.get("agents_v2_worker") is True:
                continue

            text = str(getattr(part, "output", None) or "").strip()
            if text:
                chunks.append(text)

            for record in self._worker_context_records(part):
                block = self._worker_context_block(record)
                if block:
                    chunks.append(block)

        return "\n\n".join(chunks).strip()

    def _history_output(self, item: CtxItem) -> str:
        """Return enriched assistant history for one hidden Primary Agent turn."""
        extra = item.extra if isinstance(getattr(item, "extra", None), dict) else {}
        source_id = extra.get("agents_v2_source_item_id")
        if source_id not in (None, ""):
            try:
                source = self.window.core.ctx.fetch_item_by_id(int(source_id))
                output = self._compose_source_history(source)
                if output:
                    return output
            except Exception as exc:
                self.window.core.debug.log(exc)

        output = str(getattr(item, "output", None) or "")
        if extra.get("agents_v2_memory_full_trace") is True:
            output = self._compact_legacy_output(output)
        return output.strip()

    def load_history(self, master_ctx: CtxItem, preset, model=None, current_input: str = "") -> List[ChatMessage]:
        """Load Primary Agent history, including persisted specialist finals by partial.

        Hidden memory rows still define which preset-specific user turns belong to
        this Primary Agent.  For rows created by current Agents v2 versions the
        assistant side is projected from the source CtxItem partials so reload
        restores the same chronology the Primary Agent saw during the live run:
        Primary Agent prose -> worker_context -> following Primary Agent prose.
        """
        meta = self.get_meta(master_ctx, preset)
        stored_items = self.window.core.ctx.provider.load(meta.id) if meta and meta.id is not None else []

        # Materialize enriched output on disposable copies *before* token-window
        # selection.  Otherwise max_total_tokens would count only the compact final
        # answer while the actual chat_history also contained worker responses.
        items = []
        for item in stored_items:
            clone = copy.copy(item)
            clone.parts = []
            clone.active_part = None
            clone.output = self._history_output(item)
            items.append(clone)

        if model is not None and items:
            try:
                model_id = model.id
                used_tokens = self.window.core.tokens.from_user(current_input or "", "")
                max_tokens = int(self.window.core.config.get("max_total_tokens") or 0)
                model_ctx = int(getattr(model, "ctx", 0) or 0)
                if model_ctx > 0 and (max_tokens <= 0 or max_tokens > model_ctx):
                    max_tokens = model_ctx
                if max_tokens > 0:
                    items = self.window.core.ctx.get_history(
                        items,
                        model_id,
                        MODE_AGENT_V2,
                        used_tokens,
                        max_tokens,
                        ignore_first=False,
                    )
            except Exception as exc:
                self.window.core.debug.log(exc)

        messages: List[ChatMessage] = []
        for item in items:
            if item.input:
                messages.append(ChatMessage(role=MessageRole.USER, content=str(item.input)))
            output = str(getattr(item, "output", None) or "").strip()
            if output:
                messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=output))
        return messages


    @staticmethod
    def compose_turn_output(master_ctx: CtxItem, final_answer: str = "") -> str:
        """Return the compact fallback for one completed Primary Agent turn.

        The full restore trace is reconstructed from the durable source CtxItem
        partials and their ``worker_context`` metadata.  The hidden memory row only
        keeps a compact final answer as a fallback for legacy/missing source rows
        and as a stable turn index for preset-specific orchestrator memory.
        """
        final = str(final_answer or "").strip()
        if final:
            return final
        if master_ctx is None:
            return ""
        try:
            value = master_ctx.get_agents_v2_final_output()
        except Exception:
            value = None
        return str(value or "").strip()

    def begin_turn(self, master_ctx: CtxItem, preset, user_input: str):
        """Persist the user side of a Primary Agent turn before execution starts.

        Agents v2 can be stopped while the Primary Agent is inside a tool call.  The
        main conversation CtxItem already contains the user's input at that point,
        but historically the hidden Primary Agent memory row was created only after
        a successful final answer.  A stopped turn therefore disappeared from the
        Primary Agent chat history entirely.

        Create the memory row after the previous history has been loaded, but before
        the new workflow starts doing any real work.  If the run is interrupted this
        input-only row intentionally remains in memory; the next user turn can then
        refer to the interrupted request (for example with "repeat").
        """
        if master_ctx is None or master_ctx.meta is None:
            return None
        meta = self.get_meta(master_ctx, preset)
        if meta is None:
            return None

        item = CtxItem(MODE_AGENT_V2)
        item.hidden = True
        item.internal = True
        item.agent_call = True
        item.meta = meta
        item.meta_id = meta.id
        item.model = master_ctx.model
        item.input = user_input or ""
        item.output = ""
        item.extra = {
            "agents_v2_memory": True,
            "agents_v2_memory_pending": True,
        }
        if getattr(master_ctx, "id", None) is not None:
            item.extra["agents_v2_source_item_id"] = master_ctx.id
        self.window.core.ctx.add_to_meta(item, meta.id)
        return item

    def complete_turn(self, item: CtxItem, assistant_output: str):
        """Complete a previously persisted orchestrator memory turn in place."""
        if item is None:
            return
        item.output = assistant_output or ""
        if not isinstance(item.extra, dict):
            item.extra = {}
        item.extra["agents_v2_memory"] = True
        item.extra.pop("agents_v2_memory_pending", None)
        self.window.core.ctx.update_item(item)

    def append_turn(self, master_ctx: CtxItem, preset, user_input: str, assistant_output: str):
        """Compatibility helper for callers that already have a completed turn."""
        item = self.begin_turn(master_ctx, preset, user_input)
        self.complete_turn(item, assistant_output)
        return item


# Semantic name for the new Primary Agent flow; keep the old class name for compatibility.
PrimaryAgentMemoryStore = OrchestratorMemoryStore


# Mode-neutral alias used by the merged Agents v2 runtime.
AgentsV2MemoryStore = OrchestratorMemoryStore
