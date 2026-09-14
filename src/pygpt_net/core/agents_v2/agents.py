#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .memory import AgentsV2MemoryStore
from .runner import Runner


class AgentsV2:
    def __init__(self, window=None):
        self.window = window
        self.runner = Runner(window)
        # Stateless helper shared by the live UI token estimator. Runtime turns
        # may still instantiate/use their own facade; both read the same hidden
        # DB-backed Primary Agent memory.
        self.memory_store = AgentsV2MemoryStore(window)

    def count_current_history_tokens(
            self,
            model,
            used_tokens: int = 0,
            max_tokens: int = 0,
    ):
        """Return token usage for the history actually replayed by Agents v2."""
        if model is None:
            return 0, 0
        core_ctx = self.window.core.ctx
        master_ctx = core_ctx.get_last_item()
        if master_ctx is None:
            items = core_ctx.get_items()
            if items:
                master_ctx = items[-1]
        if master_ctx is None or master_ctx.meta is None:
            return 0, 0
        preset = self.window.controller.presets.get_current()
        return self.memory_store.count_history_tokens(
            master_ctx,
            preset,
            model,
            used_tokens=used_tokens,
            max_tokens=max_tokens,
        )
