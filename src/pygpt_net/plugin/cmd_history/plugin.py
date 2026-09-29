#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.18 19:30:00                  #
# ================================================== #

from datetime import datetime
from PySide6.QtCore import Slot

from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import Event, KernelEvent
from pygpt_net.item.ctx import CtxItem

from .config import Config


class Plugin(BasePlugin):
    NO_RELEVANT_CONTEXT = "NO_RELEVANT_CONTEXT"
    FALLBACK_CONTEXT_WINDOW = 32768
    DEFAULT_SUMMARY_MAX_TOKENS = 1500

    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "cmd_history"
        self.is_common_plugin = True
        self.name = "Chat history (inline)"
        self.type = ["cmd.inline"]
        self.description = "Provides real-time access to context history database"
        self.prefix = "History"
        self.allowed_cmds = [
            "get_ctx_list_in_date_range",
            "get_ctx_content_by_id",
            "count_ctx_in_date",
            "get_day_note",
            "add_day_note",
            "update_day_note",
            "remove_day_note",
        ]
        self.order = 100
        self.use_locale = True
        self.worker = None
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        """Initialize options."""
        self.config.from_defaults(self)

    def handle(self, event: Event, *args, **kwargs):
        """Handle dispatched event."""
        name = event.name
        data = event.data
        ctx = event.ctx

        if name in [
            Event.CMD_SYNTAX_INLINE,
            Event.CMD_SYNTAX,
        ]:
            self.cmd_syntax(data)

        # Keep the plugin's historical time helper for normal plugin use. The new
        # numeric @mention resolver itself is deliberately not event-driven, so it
        # works even when this plugin is disabled and cannot collide with the old
        # POST_PROMPT/@ID implementation.
        elif name == Event.SYSTEM_PROMPT:
            data['value'] = self.on_system_prompt(data['value'])

        elif name in [
            Event.CMD_INLINE,
            Event.CMD_EXECUTE,
        ]:
            self.cmd(
                ctx,
                data['commands'],
            )

        elif name == Event.MODELS_CHANGED:
            self.refresh_option("model_summarize")

    def on_system_prompt(self, prompt: str) -> str:
        """Event: SYSTEM_PROMPT."""
        if not self.window.controller.plugins.is_type_enabled("time"):
            prompt += "\nCurrent time is: " + datetime.now().strftime('%A, %Y-%m-%d %H:%M:%S')
        return prompt

    def cmd_syntax(self, data: dict):
        """Event: CMD_SYNTAX."""
        for option in self.allowed_cmds:
            if self.has_cmd(option):
                data['cmd'].append(self.get_cmd(option))

    @Slot()
    def handle_updated(self):
        """Handle updated signal."""
        self.window.controller.calendar.setup()

    def cmd(self, ctx: CtxItem, cmds: list):
        """Events: CMD_EXECUTE."""
        from .worker import Worker

        is_cmd = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds and self.has_cmd(item["cmd"]):
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
            return

        self.cmd_prepare(ctx, my_commands)

        worker = Worker()
        worker.from_defaults(self)
        worker.cmds = my_commands
        worker.ctx = ctx
        worker.signals.updated.connect(self.handle_updated)

        if not self.is_async(ctx):
            worker.run()
            return
        worker.run_async()

    def get_day_note(self, year: int, month: int, day: int) -> str:
        """Get day note."""
        return self.window.core.calendar.load_note(year, month, day)

    def add_day_note(self, year: int, month: int, day: int, note: str) -> bool:
        """Add day note."""
        return self.window.core.calendar.append_to_note(year, month, day, note)

    def update_day_note(self, year: int, month: int, day: int, note: str) -> bool:
        """Update day note."""
        return self.window.core.calendar.update_note(year, month, day, note)

    def remove_day_note(self, year: int, month: int, day: int) -> bool:
        """Remove day note."""
        return self.window.core.calendar.remove_note(year, month, day)

    def get_list(self, range: str) -> list:
        """Get context list in date range."""
        limit = int(self.get_option_value("ctx_items_limit"))
        return self.window.core.ctx.get_list_in_date_range(range, limit=limit)

    def get_summary(self, id: int, query: str) -> str:
        """Return a query-focused summary of one previous conversation.

        The source transcript is packed using the selected summarizer model's
        context window. Chunks are processed newest-first, but text inside each
        chunk remains chronological. If the transcript needs multiple calls,
        query-focused extracts are recursively reduced until a single bounded
        summary remains. No plugin-enabled check is required by this method.
        """
        try:
            id = int(id)
        except (TypeError, ValueError):
            return ""

        items = self.window.core.ctx.get_items_by_id(id)
        if not items:
            return ""

        model = self._get_summary_model()
        if model is None:
            return ""

        query = self._clip_query(str(query or "").strip(), model)
        if not query:
            query = "Continue from this previous conversation using the most recent relevant state."

        extract_prompt = self._format_prompt(
            "prompt_tag_summary",
            id=id,
            query=query,
        )
        reduce_prompt = self._format_prompt(
            "prompt_tag_reduce",
            id=id,
            query=query,
        )
        max_tokens = self._summary_max_tokens(model)
        input_budget = self._input_budget(model, extract_prompt, max_tokens)
        if input_budget < 64:
            self.log("Chat history summary skipped: summarizer context window is too small for the configured prompt/output budget.")
            return ""
        chunks = self._pack_recent_first(items, model, input_budget)
        if not chunks:
            return ""

        extracts = []
        total = len(chunks)
        for idx, chunk in enumerate(chunks, start=1):
            user_prompt = (
                f"<conversation_chunk id=\"{id}\" recency_rank=\"{idx}\" "
                f"chunks_total=\"{total}\">\n{chunk}\n</conversation_chunk>"
            )
            response = self._call_model(user_prompt, extract_prompt, model, max_tokens)
            response = self._normalize_summary(response)
            if response:
                extracts.append(response)

        if not extracts:
            return ""
        if len(extracts) == 1:
            return extracts[0]

        return self._reduce_extracts(
            id=id,
            query=query,
            extracts=extracts,
            model=model,
            sys_prompt=reduce_prompt,
            max_tokens=max_tokens,
        )

    def count_ctx_in_date(
            self,
            year: int = None,
            month: int = None,
            day: int = None
    ) -> dict:
        """Get context counters."""
        return self.window.core.ctx.provider.get_ctx_count_by_day(
            year=year,
            month=month,
            day=day,
        )

    def _get_summary_model(self):
        """Return the configured summarizer model, with the app default as fallback."""
        model = self.window.core.models.from_defaults()
        model_key = self.get_option_value("model_summarize")
        if model_key and self.window.core.models.has(model_key):
            model = self.window.core.models.get(model_key)
        return model

    def _summary_max_tokens(self, model=None) -> int:
        try:
            value = int(self.get_option_value("summary_max_tokens") or 0)
        except (TypeError, ValueError):
            value = 0
        value = value if value > 0 else self.DEFAULT_SUMMARY_MAX_TOKENS
        if model is not None:
            # Never reserve an output larger than one quarter of a small model's
            # context window; reduction outputs must fit back into the next pass.
            value = min(value, max(256, int(self._context_window(model) * 0.25)))
        return value

    def _count_tokens(self, text: str, model) -> int:
        value = str(text or "")
        model_id = str(getattr(model, "id", None) or "gpt-4")
        try:
            count = int(self.window.core.tokens.from_text(value, model_id) or 0)
            if count > 0 or not value:
                return max(0, count)
        except Exception:
            pass
        # Unknown/custom model tokenizers may return 0 rather than raising. Use
        # one token per character as a deliberately conservative multilingual
        # fallback (len/4 can badly undercount CJK and other tokenizations).
        return len(value) if value else 0

    def _context_window(self, model) -> int:
        try:
            value = int(getattr(model, "ctx", 0) or 0)
        except (TypeError, ValueError):
            value = 0
        if value <= 0:
            return self.FALLBACK_CONTEXT_WINDOW
        # Respect the advertised window exactly. Some local/custom models have
        # contexts below 4k; inflating them here would defeat the safety budget.
        return max(256, value)

    def _input_budget(self, model, sys_prompt: str, max_output_tokens: int) -> int:
        """Compute a conservative per-call transcript budget in tokens."""
        context_window = self._context_window(model)
        prompt_tokens = self._count_tokens(sys_prompt, model)
        # Use only 80% of the advertised window. This leaves room for provider
        # wrappers/tokenizer differences and avoids a boundary failure when model
        # metadata is approximate (common for custom/OpenAI-compatible models).
        safe_window = max(256, int(context_window * 0.80))
        # Provider wrappers plus the XML chunk envelope also consume tokens. Keep
        # a proportional reserve instead of a fixed 512 tokens so small local
        # models are not accidentally budgeted above their real context window.
        reserve = max(96, min(512, int(context_window * 0.08)))
        available = safe_window - prompt_tokens - max_output_tokens - reserve
        return max(0, available)

    def _clip_query(self, query: str, model) -> str:
        """Keep an unusually large current request from consuming the whole map call."""
        value = str(query or "").strip()
        if not value:
            return ""
        limit = max(96, min(4096, int(self._context_window(model) * 0.12)))
        if self._count_tokens(value, model) <= limit:
            return value

        # Preserve both the beginning (task framing) and tail (latest qualifiers).
        chars = max(256, int(len(value) * limit / max(1, self._count_tokens(value, model)) * 0.90))
        while chars >= 128:
            head = max(64, int(chars * 0.62))
            tail = max(64, chars - head)
            candidate = (value[:head].rstrip() + "\n…\n" + value[-tail:].lstrip()).strip()
            if self._count_tokens(candidate, model) <= limit:
                return candidate
            chars = int(chars * 0.80)
        return value[:128]

    def _char_chunk_limit(self) -> int:
        try:
            value = int(self.get_option_value("chunk_size") or 0)
        except (TypeError, ValueError):
            value = 0
        return max(1000, value) if value > 0 else 100000

    def _split_text_to_budget(self, text: str, model, token_budget: int) -> list[str]:
        """Split one oversized turn without ever exceeding the per-call budget."""
        remaining = str(text or "")
        if not remaining:
            return []
        char_limit = self._char_chunk_limit()
        chunks = []

        while remaining:
            candidate = remaining[:char_limit]
            if self._count_tokens(candidate, model) <= token_budget:
                cut = len(candidate)
            else:
                lo = 1
                hi = len(candidate)
                cut = 1
                while lo <= hi:
                    mid = (lo + hi) // 2
                    probe = candidate[:mid]
                    if self._count_tokens(probe, model) <= token_budget:
                        cut = mid
                        lo = mid + 1
                    else:
                        hi = mid - 1

            # Prefer a natural line boundary near the safe cut without making a
            # very small fragment. This keeps Human/Assistant pairs readable.
            natural = remaining.rfind("\n", max(0, int(cut * 0.65)), cut)
            if natural > 0:
                cut = natural + 1
            part = remaining[:cut].strip()
            if part:
                chunks.append(part)
            remaining = remaining[cut:]

        return chunks

    def _pack_recent_first(self, items: list, model, token_budget: int) -> list[str]:
        """Pack source turns newest-first while retaining chronological text per chunk."""
        units = []
        for item in items:
            units.extend(self._split_text_to_budget(str(item or ""), model, token_budget))
        if not units:
            return []

        chunks = []
        current = []
        current_tokens = 0
        separator_tokens = max(1, self._count_tokens("\n\n", model))

        for unit in reversed(units):
            unit_tokens = self._count_tokens(unit, model)
            extra = unit_tokens + (separator_tokens if current else 0)
            if current and current_tokens + extra > token_budget:
                chunks.append("\n\n".join(reversed(current)))
                current = []
                current_tokens = 0
            current.append(unit)
            current_tokens += unit_tokens + (separator_tokens if len(current) > 1 else 0)

        if current:
            chunks.append("\n\n".join(reversed(current)))
        return chunks

    def _format_prompt(self, key: str, **kwargs) -> str:
        try:
            return str(self.get_option_value(key) or "").format(**kwargs)
        except Exception as e:
            self.log("Incorrect prompt: " + str(e))
            return ""

    def _call_model(self, prompt: str, sys_prompt: str, model, max_tokens: int) -> str:
        try:
            bridge_context = BridgeContext(
                prompt=prompt,
                system_prompt=sys_prompt,
                max_tokens=max_tokens,
                model=model,
            )
            event = KernelEvent(KernelEvent.CALL, {
                'context': bridge_context,
                'extra': {},
            })
            self.window.dispatch(event)
            return str(event.data.get('response') or "").strip()
        except Exception as e:
            self.error(e)
            return ""

    def _normalize_summary(self, response: str) -> str:
        value = str(response or "").strip()
        if not value:
            return ""
        normalized = value.strip().strip('`').strip()
        if normalized.upper() == self.NO_RELEVANT_CONTEXT:
            return ""
        return value

    def _format_extracts(self, extracts: list[str], model=None, token_budget: int = 0) -> list[str]:
        """Format reduction inputs, splitting any unexpectedly large model output."""
        units = []
        for idx, value in enumerate(extracts, start=1):
            value = str(value or "").strip()
            if not value:
                continue

            parts = [value]
            if model is not None and token_budget > 0:
                envelope = f'<extract recency_rank="{idx}" part="1/1">\n\n</extract>'
                body_budget = max(16, token_budget - self._count_tokens(envelope, model) - 8)
                parts = self._split_text_to_budget(value, model, body_budget) or [value]

            total = len(parts)
            for part_idx, part in enumerate(parts, start=1):
                units.append(
                    f'<extract recency_rank="{idx}" part="{part_idx}/{total}">\n{part}\n</extract>'
                )
        return units

    def _reduce_extracts(
            self,
            id: int,
            query: str,
            extracts: list[str],
            model,
            sys_prompt: str,
            max_tokens: int,
    ) -> str:
        """Recursively merge map outputs without exceeding the model context."""
        current = list(extracts)
        budget = self._input_budget(model, sys_prompt, max_tokens)
        if budget < 64:
            # Every map extract is already query-focused and ordered newest-first.
            # If a custom reduction prompt leaves no safe room, keep the newest
            # extract rather than issuing a request that could exceed model limits.
            return current[0] if current else ""
        guard = 0

        while len(current) > 1 and guard < 16:
            guard += 1
            units = self._format_extracts(current, model=model, token_budget=budget)
            groups = []
            group = []
            group_tokens = 0
            for unit in units:
                tokens = self._count_tokens(unit, model)
                if group and group_tokens + tokens > budget:
                    groups.append("\n\n".join(group))
                    group = []
                    group_tokens = 0
                group.append(unit)
                group_tokens += tokens
            if group:
                groups.append("\n\n".join(group))

            reduced = []
            for group_idx, body in enumerate(groups, start=1):
                prompt = (
                    f'<conversation_extracts id="{id}" group="{group_idx}" '
                    f'groups_total="{len(groups)}">\n{body}\n</conversation_extracts>'
                )
                response = self._normalize_summary(
                    self._call_model(prompt, sys_prompt, model, max_tokens)
                )
                if response:
                    reduced.append(response)

            if not reduced:
                return current[0]
            if len(reduced) >= len(current):
                # Defensive progress guarantee for pathological tiny model windows.
                return reduced[0]
            current = reduced

        return current[0] if current else ""
