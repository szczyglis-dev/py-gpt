#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.27 06:00:00                  #
# ================================================== #

from __future__ import annotations

from typing import Any, List, Optional
from agents import TResponseInputItem
from .graph import FlowGraph
from .memory import MemoryManager
from .flow_types import DebugConfig
from .utils import sanitize_input_items
from .debug import ellipsize


class FlowMemoryPolicy:
    """Transfer displayed answers between nodes and update per-node memory."""

    def __init__(self, logger):
        self.logger = logger

    # ========================================
    # Baton and memory
    # ========================================

    def build_input(
        self,
        *,
        node_id: str,
        g: FlowGraph,
        mem: MemoryManager,
        initial_messages: List[TResponseInputItem],
        first_dispatch_done: bool,
        last_plain_output: str,
        dbg: DebugConfig,
    ) -> tuple[List[TResponseInputItem], str, Optional[str], Any, str]:
        """
        Returns: (prepared_items, baton_user_text, mem_id, mem_state, source_tag)
        Mirrors LI baton/memory policy.
        """
        mem_id = g.agent_to_memory.get(node_id)
        mem_state = mem.get(mem_id) if mem_id else None

        baton_user_text = ""
        source = ""

        if mem_state and mem_state.items:
            # memory with history -> base history + baton from last output (preferred)
            base_items = list(mem_state.items[:-1]) if len(mem_state.items) >= 1 else []
            if last_plain_output and last_plain_output.strip():
                baton_user_text = last_plain_output
                prepared = base_items + [{"role": "user", "content": baton_user_text}]
                source = "memory:existing_to_user_baton"
            else:
                # fallback: use last assistant content as baton
                last_ass = mem_state.items[-1] if isinstance(mem_state.items[-1], dict) else {}
                if isinstance(last_ass.get("content"), str):
                    baton_user_text = last_ass.get("content", "")
                elif isinstance(last_ass.get("content"), list) and last_ass["content"]:
                    baton_user_text = last_ass["content"][0].get("text", "") or ""
                else:
                    baton_user_text = ""
                prepared = base_items + [{"role": "user", "content": baton_user_text}]
                source = "memory:existing_to_last_assistant"
            return sanitize_input_items(prepared), baton_user_text, mem_id, mem_state, source

        if mem_state:
            # memory attached but empty -> seed from last output else from initial (use last user msg as baton)
            if last_plain_output and last_plain_output.strip():
                baton_user_text = last_plain_output
                prepared = [{"role": "user", "content": baton_user_text}]
                source = "memory:seed_from_last_output"
            else:
                base_items = list(initial_messages[:-1]) if initial_messages else []
                last_item = initial_messages[-1] if initial_messages else {"role": "user", "content": ""}
                baton_user_text = self._extract_text_from_item(last_item)
                prepared = base_items + [{"role": "user", "content": baton_user_text}]
                source = "memory:seed_from_initial"
            return sanitize_input_items(prepared), baton_user_text, mem_id, mem_state, source

        # no memory attached
        if not first_dispatch_done:
            # first agent: pass initial messages as-is; baton is last user text (for potential external memory)
            last_item = initial_messages[-1] if initial_messages else {"role": "user", "content": ""}
            baton_user_text = self._extract_text_from_item(last_item)
            return sanitize_input_items(list(initial_messages)), baton_user_text, None, None, "no-mem:first_initial"
        else:
            baton_user_text = last_plain_output if last_plain_output and last_plain_output.strip() else (
                self._extract_text_from_item(initial_messages[-1]) if initial_messages else ""
            )
            prepared = [{"role": "user", "content": baton_user_text}]
            return sanitize_input_items(prepared), baton_user_text, None, None, "no-mem:last_output"

    def update_after_step(
        self,
        *,
        node_id: str,
        mem_state: Any,
        baton_user_text: str,
        display_text: str,
        last_response_id: Optional[str],
        dbg: DebugConfig,
    ) -> None:
        """Update memory strictly with [user baton, assistant display_text], mirroring LI semantics."""
        if not mem_state:
            return
        base_items = list(mem_state.items[:-1]) if getattr(mem_state, "items", None) else []
        new_mem = (base_items or []) + [
            {"role": "user", "content": baton_user_text or ""},
            {"role": "assistant", "content": [{"type": "output_text", "text": display_text or ""}]},
        ]
        try:
            mem_state.set_from(new_mem, last_response_id)
            if dbg.log_inputs:
                self.logger.debug(
                    f"[memory] {node_id} updated len {len(base_items)} -> {len(new_mem)} "
                    f"user='{ellipsize(baton_user_text or '', dbg.preview_chars)}' "
                    f"assist='{ellipsize(display_text or '', dbg.preview_chars)}'"
                )
        except Exception as e:
            self.logger.error(f"[memory] update failed for {node_id}: {e}")

    # ========================================
    # Content extraction
    # ========================================

    def _extract_text_from_item(self, item: TResponseInputItem) -> str:
        """Best-effort extract plain text from TResponseInputItem."""
        if isinstance(item, dict):
            content = item.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for p in content:
                    if isinstance(p, dict):
                        t = p.get("text")
                        if isinstance(t, str):
                            parts.append(t)
                return "\n".join(parts)
            return ""
        if isinstance(item, str):
            return item
        return ""

