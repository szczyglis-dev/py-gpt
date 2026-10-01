#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 00:00:00                  #
# ================================================== #

"""History replay, date labels and turn action routing."""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from PySide6.QtCore import QLocale
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.utils import get_locale_lang, trans


class History:
    """History replay, date labels and turn action routing.

    The renderer supplies session services and the shared session state.
    Collaborators are called explicitly through their component APIs.
    """

    # ========================================
    # Initialization
    # ========================================

    def __init__(self, renderer):
        self.renderer = renderer
        self.state = renderer.state

    # ========================================
    # History replay
    # ========================================

    def append_context(self, meta: CtxMeta, items: List[CtxItem], clear: bool = True):
        """
        Append all context items to output

        :param meta: context meta
        :param items: list of context items
        :param clear: clear previous content
        """
        self.renderer.tools.tool_output_end()
        self.append_context_all(meta, items, clear=clear)

    def append_context_partial(self, meta: CtxMeta, items: List[CtxItem], clear: bool = True):
        """
        Append context items part-by-part

        Append each item as it comes, useful for non-streaming mode when
        context is built gradually.

        :param meta: context meta
        :param items: list of context items
        :param clear: clear previous content
        """
        if len(items) == 0:
            if meta is None:
                return

        pid = self.renderer.session.get_or_create_pid(meta)
        self.renderer.session.init(pid)
        if clear:
            self.renderer.session.reset(meta)

        self.state.pids[pid].use_buffer = True
        self.state.pids[pid].html = ""
        prev_ctx = None
        next_item = None
        previous_user_day = None
        total = len(items)
        latest_visible_index = next(
            (i for i in range(total - 1, -1, -1) if not getattr(items[i], "hidden", False)),
            -1,
        )
        for i, item in enumerate(items):
            self.renderer.view.update_names(meta, item)
            item.idx = i
            if i == 0:
                item.first = True
            next_item = items[i + 1] if i + 1 < total else None

            # ignore hidden
            if item.hidden:
                prev_ctx = item
                continue

            # build single RenderBlock with both input and output (if present)
            input_text = self.renderer.messages.prepare_input(meta, item, flush=False, append=False)
            history_date_label = None
            if input_text:
                input_day = self._history_input_day(item)
                if input_day is not None and input_day != previous_user_day:
                    history_date_label = self._format_history_date_label(item.input_timestamp)
                    previous_user_day = input_day
            output_text = self.renderer.messages.prepare_output(meta, item, flush=False, prev_ctx=prev_ctx, next_ctx=next_item)
            action_state = self._get_action_state(items, i)
            block = self.renderer.messages.build_render_block(
                meta,
                item,
                input_text,
                output_text,
                prev_ctx=prev_ctx,
                next_ctx=next_item,
                action_state=action_state,
                rebuild=True,
                is_latest_ctx=(i == latest_visible_index),
                history_date_label=history_date_label,
            )
            if block:
                self.renderer.bridge.append(pid, block.to_json(wrap=True))

            prev_ctx = item

        self.state.pids[pid].use_buffer = False
        if self.state.pids[pid].html != "":
            self.renderer.bridge.append(pid, self.state.pids[pid].html, flush=True)

    def append_context_all(self, meta: CtxMeta, items: List[CtxItem], clear: bool = True):
        """
        Append whole context at once, using JSON nodes

        :param meta: context meta
        :param items: list of context items
        :param clear: clear previous content
        """
        if len(items) == 0:
            if meta is None:
                return

        pid = self.renderer.session.get_or_create_pid(meta)
        self.renderer.session.init(pid)

        if clear:
            # nodes will be cleared on JS when replace flag is True
            self.renderer.session.reset(meta, clear_nodes=False)

        self.state.pids[pid].use_buffer = True
        self.state.pids[pid].html = ""
        prev_ctx = None
        next_ctx = None
        previous_user_day = None
        total = len(items)
        nodes: List[dict] = []
        latest_visible_index = next(
            (i for i in range(total - 1, -1, -1) if not getattr(items[i], "hidden", False)),
            -1,
        )

        for i, item in enumerate(items):
            self.renderer.view.update_names(meta, item)
            item.idx = i
            if i == 0:
                item.first = True
            next_ctx = items[i + 1] if i + 1 < total else None

            if item.hidden:
                prev_ctx = item
                continue

            input_text = self.renderer.messages.prepare_input(meta, item, flush=False, append=False)
            history_date_label = None
            if input_text:
                input_day = self._history_input_day(item)
                if input_day is not None and input_day != previous_user_day:
                    history_date_label = self._format_history_date_label(item.input_timestamp)
                    previous_user_day = input_day
            output_text = self.renderer.messages.prepare_output(meta, item, flush=False, prev_ctx=prev_ctx, next_ctx=next_ctx)
            action_state = self._get_action_state(items, i)
            block = self.renderer.messages.build_render_block(
                meta,
                item,
                input_text,
                output_text,
                prev_ctx=prev_ctx,
                next_ctx=next_ctx,
                action_state=action_state,
                rebuild=True,
                is_latest_ctx=(i == latest_visible_index),
                history_date_label=history_date_label,
            )
            if block:
                nodes.append(block.to_dict())

            prev_ctx = item

        if nodes:
            payload = json.dumps({"nodes": nodes}, ensure_ascii=False, separators=(',', ':'))
            self.renderer.bridge.append(pid, payload, replace=True)

        prev_ctx = None
        next_ctx = None
        self.state.pids[pid].use_buffer = False
        if self.state.pids[pid].html != "":
            self.renderer.bridge.append(pid, self.state.pids[pid].html, flush=True, replace=True)

    # ========================================
    # Date separators
    # ========================================

    def get_live_input_date_label(self, meta: CtxMeta, ctx: CtxItem) -> Optional[str]:
        """Return the day separator for an input rendered before history rebuild.

        History rendering tracks the previous visible user-input day while it
        walks the whole context. Live INPUT_APPEND normally happens before the
        new item is stored, so reproduce the same decision from the currently
        loaded items. This reserves the separator's final layout space before
        response streaming starts.
        """
        current_day = self._history_input_day(ctx)
        if current_day is None:
            return None

        target_meta_id = getattr(meta, "id", None)
        current_id = getattr(ctx, "id", None)
        previous_user_day = None

        try:
            core_ctx = self.renderer.window.core.ctx
            if target_meta_id is not None and core_ctx.get_current() != target_meta_id:
                items = list(core_ctx.all(target_meta_id) or [])
            else:
                items = list(core_ctx.get_items() or [])
        except Exception:
            items = []

        for i, item in enumerate(items):
            # Standard chat stores the item after INPUT_APPEND, while some
            # modes store it before. In the latter case stop at the current row.
            if item is ctx:
                break
            item_id = getattr(item, "id", None)
            if current_id is not None and item_id == current_id:
                break

            if getattr(item, "hidden", False):
                continue

            item_meta_id = getattr(item, "meta_id", None)
            if item_meta_id is None:
                item_meta = getattr(item, "meta", None)
                item_meta_id = getattr(item_meta, "id", None) if item_meta is not None else None
            if (target_meta_id is not None
                    and item_meta_id is not None
                    and item_meta_id != target_meta_id):
                continue

            raw_input = getattr(item, "input", None)
            if raw_input is None or str(raw_input).strip() == "":
                continue

            # Match prepare_input() visibility rules. append_context_* marks
            # list index 0 as the first item before evaluating these rules.
            if getattr(item, "internal", False) and i != 0:
                stripped = str(raw_input).strip()
                if not stripped.startswith("user: ") and not stripped.startswith("@"):
                    continue

            item_day = self._history_input_day(item)
            if item_day is not None:
                previous_user_day = item_day

        if previous_user_day == current_day:
            return None
        return self._format_history_date_label(getattr(ctx, "input_timestamp", None))

    # ========================================
    # Turn actions
    # ========================================

    def get_action_state_for_ctx(self, ctx: CtxItem) -> dict:
        """Resolve action state for single-item/live render paths."""
        try:
            items = self.renderer.window.core.ctx.get_items()
        except Exception:
            items = []

        cid = getattr(ctx, "id", None)
        for index, item in enumerate(items):
            if item is ctx or (cid is not None and getattr(item, "id", None) == cid):
                return self._get_action_state(items, index)

        # Fallback for a just-created streamed item not yet present in the
        # container. Rebuild the visual turn from prev_ctx and only apply it when
        # an agent marker (primarily ``agent_output``) confirms an agent turn.
        chain = [ctx]
        current = ctx
        previous = getattr(current, "prev_ctx", None)
        guard = 0
        while previous is not None and guard < 256:
            chain.insert(0, previous)
            if self._is_user_turn_ctx(previous):
                break
            current = previous
            previous = getattr(current, "prev_ctx", None)
            guard += 1
        if self._is_agent_turn(chain, 0, len(chain) - 1):
            return self._get_action_state(chain, len(chain) - 1)

        return {
            "footer_icons": True,
            "edit_replay_id": cid,
            "delete_start_id": None,
            "delete_end_id": None,
        }

    def hide_previous_agent_action_icons(self, meta: CtxMeta, ctx: CtxItem) -> None:
        """
        Remove stale footers from earlier already-rendered agent outputs.

        Full history renders compute footer visibility from the complete item
        list. This DOM cleanup is only needed live, when a response that was the
        last one a moment ago must lose its footer as soon as the next agent
        response starts.
        """
        ids = self._get_agent_chain_previous_ids_for_ctx(ctx)
        if not ids:
            return

        try:
            node = self.renderer.get_output_node(meta)
            if node is None:
                return
            ids_json = json.dumps(ids, separators=(',', ':'))
            node.page().runJavaScript(
                "(() => {"
                f"const ids={ids_json};"
                "for (const id of ids) {"
                "const box=document.getElementById('msg-bot-' + id);"
                "if (!box) continue;"
                "const actions=box.querySelector('.action-icons');"
                "if (actions) actions.remove();"
                "}"
                "})();"
            )
        except Exception:
            pass

    # ========================================
    # Private: date labels
    # ========================================

    @staticmethod
    def _history_input_day(ctx: CtxItem):
        """Return the local calendar day for a persisted user input."""
        timestamp = getattr(ctx, "input_timestamp", None)
        if timestamp is None:
            return None
        try:
            return datetime.fromtimestamp(float(timestamp)).date()
        except (TypeError, ValueError, OSError, OverflowError):
            return None

    def _format_history_date_label(self, timestamp) -> Optional[str]:
        """Format a day separator shown above user messages."""
        if timestamp is None:
            return None
        try:
            dt = datetime.fromtimestamp(float(timestamp))
        except (TypeError, ValueError, OSError, OverflowError):
            return None

        today = datetime.now().date()
        day = dt.date()
        clock = dt.strftime("%H:%M")

        if day == today:
            return f"{trans('ctx.date.today')}, {clock}"
        if day == today - timedelta(days=1):
            return f"{trans('ctx.date.yesterday')}, {clock}"

        try:
            locale = QLocale(get_locale_lang() or "en")
            weekday = locale.dayName(dt.isoweekday(), QLocale.FormatType.LongFormat).strip()
            month = locale.monthName(dt.month, QLocale.FormatType.LongFormat).strip()
        except Exception:
            weekday = dt.strftime("%A")
            month = dt.strftime("%B")

        # Preserve the capitalization supplied by QLocale. Weekday names are
        # conventionally capitalized in some languages (e.g. English/German)
        # and lowercase in others (e.g. Polish/French/Spanish).
        weekday = weekday.rstrip(".")
        if not month:
            month = dt.strftime("%B")

        prefix = f"{weekday}, " if weekday else ""
        if day.year == today.year:
            return f"{prefix}{dt.day} {month} {clock}"
        return f"{prefix}{dt.day} {month} {dt.year}"

    # ========================================
    # Private: turn boundaries
    # ========================================

    @staticmethod
    def _is_agent_turn_marker(ctx: Optional[CtxItem]) -> bool:
        """Return True when an item is explicitly part of an agent turn."""
        if ctx is None:
            return False
        extra = getattr(ctx, "extra", None)
        if not isinstance(extra, dict):
            return False
        return bool(
            extra.get("agent_output")
            or extra.get("agent_input")
            or extra.get("agent_step")
        )

    @staticmethod
    def _is_user_turn_ctx(ctx: Optional[CtxItem]) -> bool:
        """Return True when an item starts a visible, non-internal user turn."""
        if ctx is None or getattr(ctx, "hidden", False) or getattr(ctx, "internal", False):
            return False
        value = getattr(ctx, "input", None)
        return bool(value is not None and str(value).strip())

    @staticmethod
    def _ctx_has_output(ctx: Optional[CtxItem]) -> bool:
        """Return True when an item owns a visible assistant output payload."""
        if ctx is None or getattr(ctx, "hidden", False):
            return False
        value = getattr(ctx, "output", None)
        return bool(value is not None and str(value).strip())

    def _get_turn_bounds(self, items: List[CtxItem], index: int) -> Tuple[int, int]:
        """Return [start, end] bounds of the visible turn containing index."""
        if not items:
            return 0, -1

        start = 0
        for pos in range(index, -1, -1):
            if self._is_user_turn_ctx(items[pos]):
                start = pos
                break

        end = len(items) - 1
        for pos in range(index + 1, len(items)):
            if self._is_user_turn_ctx(items[pos]):
                end = pos - 1
                break
        return start, end

    def _is_agent_turn(self, items: List[CtxItem], start: int, end: int) -> bool:
        """Return True when the turn contains persisted agent markers."""
        if start < 0 or end < start:
            return False
        return any(
            self._is_agent_turn_marker(items[pos])
            for pos in range(start, end + 1)
        )

    # ========================================
    # Private: action routing
    # ========================================

    def _get_action_state(self, items: List[CtxItem], index: int) -> dict:
        """
        Resolve footer visibility and action targets for a context item.

        Intermediate grouped responses do not get a footer. The final response
        keeps audio/copy bound to itself, while edit/replay targets the user item
        that initiated the tool/agent sequence. Delete targets only that exact
        grouped range, so later unrelated messages are never removed.

        :param items: Ordered context items
        :param index: Index of the rendered item
        :return: Footer/action routing state
        """
        if index < 0 or index >= len(items):
            return {
                "footer_icons": True,
                "edit_replay_id": None,
                "delete_start_id": None,
                "delete_end_id": None,
            }

        ctx = items[index]
        cid = getattr(ctx, "id", None)
        state = {
            "footer_icons": True,
            "edit_replay_id": cid,
            "delete_start_id": None,
            "delete_end_id": None,
        }

        # Agent turns are broader than embedded tool chains, so agent routing
        # takes precedence whenever a persisted agent marker is present.
        agent_state = self._get_agent_action_state(items, index, state)
        if agent_state is not None:
            return agent_state

        next_ctx = items[index + 1] if index + 1 < len(items) else None
        if self.renderer.tools.is_tool_reply_transition(ctx, next_ctx):
            state["footer_icons"] = False
            return state

        # Only the final item in a tool-reply chain needs action rerouting.
        if index == 0 or not self.renderer.tools.is_tool_reply_transition(items[index - 1], ctx):
            return state

        # Walk back over all consecutive tool request -> internal reply edges.
        chain_start = index - 1
        while chain_start > 0 and self.renderer.tools.is_tool_reply_transition(
                items[chain_start - 1],
                items[chain_start]
        ):
            chain_start -= 1

        # Edit/replay should always restart from the user turn which initiated
        # the chain, never from an internal tool-result prompt.
        user_index = chain_start
        while user_index >= 0:
            candidate = items[user_index]
            if not getattr(candidate, "internal", False) and getattr(candidate, "input", None):
                break
            user_index -= 1
        if user_index < 0:
            user_index = chain_start

        state["edit_replay_id"] = getattr(items[user_index], "id", cid)
        state["delete_start_id"] = getattr(items[chain_start], "id", cid)
        state["delete_end_id"] = cid
        return state

    def _get_agent_action_state(
            self,
            items: List[CtxItem],
            index: int,
            state: dict
    ) -> Optional[dict]:
        """
        Resolve footer/action routing for one agent-driven turn.

        ``agent_output`` is the primary persisted marker used by agent responses;
        ``agent_input`` and ``agent_step`` cover the opening/legacy intermediate
        rows. Only the last assistant output before the next visible user turn
        keeps the footer. Audio/copy stay on that output, edit/replay target the
        first user row of the turn, and delete covers the whole stored turn.
        """
        start, end = self._get_turn_bounds(items, index)
        if not self._is_agent_turn(items, start, end):
            return None

        last_output = None
        for pos in range(end, start - 1, -1):
            if self._ctx_has_output(items[pos]):
                last_output = pos
                break
        if last_output is None:
            return None

        if index != last_output:
            state["footer_icons"] = False
            return state

        cid = getattr(items[index], "id", None)
        anchor = start
        state["edit_replay_id"] = getattr(items[anchor], "id", cid)
        state["delete_start_id"] = getattr(items[anchor], "id", cid)
        state["delete_end_id"] = getattr(items[end], "id", cid)
        return state

    def _get_agent_chain_previous_ids_for_ctx(self, ctx: CtxItem) -> List[int]:
        """Return previous rendered assistant-output IDs in ctx's agent turn."""
        try:
            items = list(self.renderer.window.core.ctx.get_items())
        except Exception:
            items = []

        index = None
        cid = getattr(ctx, "id", None)
        for i, item in enumerate(items):
            if item is ctx or (cid is not None and getattr(item, "id", None) == cid):
                index = i
                break

        if index is not None:
            start, end = self._get_turn_bounds(items, index)
            if not self._is_agent_turn(items, start, end):
                return []
            return [
                getattr(items[pos], "id")
                for pos in range(start, index)
                if self._ctx_has_output(items[pos])
                and getattr(items[pos], "id", None) is not None
            ]

        # A just-created streamed item can arrive before insertion into the
        # current context container. Follow prev_ctx back to the opening user row.
        chain = [ctx]
        current = ctx
        previous = getattr(current, "prev_ctx", None)
        guard = 0
        while previous is not None and guard < 256:
            chain.insert(0, previous)
            if self._is_user_turn_ctx(previous):
                break
            current = previous
            previous = getattr(current, "prev_ctx", None)
            guard += 1

        if not self._is_agent_turn(chain, 0, len(chain) - 1):
            return []
        return [
            getattr(item, "id")
            for item in chain[:-1]
            if self._ctx_has_output(item) and getattr(item, "id", None) is not None
        ]

