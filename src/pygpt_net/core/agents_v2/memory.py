#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import List

from llama_index.core.base.llms.types import ChatMessage, MessageRole

from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.types import MODE_AGENT_V2


class OrchestratorMemoryStore:
    """Persist only orchestrator-facing turns in a hidden child context."""

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

    def load_history(self, master_ctx: CtxItem, preset, model=None, current_input: str = "") -> List[ChatMessage]:
        """Load hidden orchestrator history and apply PyGPT's normal token-window policy."""
        meta = self.get_meta(master_ctx, preset)
        items = self.window.core.ctx.provider.load(meta.id) if meta and meta.id is not None else []

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
            if item.output:
                messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=str(item.output)))
        return messages

    def append_turn(self, master_ctx: CtxItem, preset, user_input: str, assistant_output: str):
        if master_ctx is None or master_ctx.meta is None:
            return
        meta = self.get_meta(master_ctx, preset)
        if meta is None:
            return
        item = CtxItem(MODE_AGENT_V2)
        item.hidden = True
        item.internal = True
        item.agent_call = True
        item.meta = meta
        item.meta_id = meta.id
        item.model = master_ctx.model
        item.input = user_input or ""
        item.output = assistant_output or ""
        item.extra = {"agents_v2_memory": True}
        self.window.core.ctx.add_to_meta(item, meta.id)
