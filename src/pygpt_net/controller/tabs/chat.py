#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 11:45:00                  #
# ================================================== #

from typing import Optional

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.item.ctx import CtxMeta


class ChatTabs:
    """Chat/context routing for output tabs.

    All bindings are PID-based. Focus can change independently, but a context
    assignment is always made against one concrete chat tab.
    """

    def _request_active(self) -> bool:
        try:
            return self.window.core.ctx.output.has_request()
        except Exception:
            return False

    def get_effective_current_pid(self) -> Optional[int]:
        column_idx = self.get_pending_focus_column()
        if column_idx is None:
            column_idx = self.get_current_column_idx()
        tab = self.get_current_by_column(column_idx)
        return tab.pid if tab is not None else None


    def get_preferred_chat_tab(self, column_idx: Optional[int] = None) -> Optional[Tab]:
        """Resolve the deterministic chat target for a context operation."""
        if column_idx is None:
            column_idx = self.get_current_column_idx()
        column_idx = int(column_idx)

        tab = self.get_current_by_column(column_idx)
        if tab is not None and tab.type == Tab.TAB_CHAT:
            return tab

        # Prefer a chat already selected in another visible column.
        for other in range(self.window.core.tabs.NUM_COLS):
            if other == column_idx:
                continue
            if other == 1 and not self.is_split_screen_enabled():
                continue
            tab = self.get_current_by_column(other)
            if tab is not None and tab.type == Tab.TAB_CHAT:
                return tab

        return self.window.core.tabs.get_first_by_type(Tab.TAB_CHAT)

    def bind_chat(self, tab: Tab, meta_id: Optional[int]) -> Optional[Tab]:
        """Bind one chat tab to a context ID without consulting current focus."""
        if tab is None or tab.type != Tab.TAB_CHAT:
            return None
        tab.data_id = meta_id
        tab.loaded = False
        if meta_id is None:
            self.window.core.ctx.output.remove_pid(tab.pid)
            return tab

        meta = self.window.core.ctx.get_meta_by_id(meta_id)
        if meta is not None:
            self.window.core.ctx.output.store(meta, pid=tab.pid)
            self.update_title_by_tab(tab, meta.name)
        else:
            # prepare_meta still records a persisted ID when CtxMeta collection
            # has not been populated yet (startup/profile restore).
            self.window.core.ctx.output.prepare_meta(tab)
        return tab

    def create_chat_context(self, tab: Tab):
        """Create and bind a new context to ``tab`` atomically."""
        if tab is None or tab.type != Tab.TAB_CHAT or tab.data_id is not None:
            return None
        if self._request_active():
            return None

        current = self.get_current_tab()
        if current is None or current.pid != tab.pid:
            self.activate_tab(tab)
        meta = self.window.controller.ctx.new(tab_pid=tab.pid)
        if meta is not None:
            self.bind_chat(tab, meta.id)
        return meta

    def sync_focused_chat_context(self):
        """Synchronize core.ctx after request ownership has been released."""
        if self._request_active():
            return
        tab = self.get_current_tab()
        if tab is None or tab.type != Tab.TAB_CHAT:
            return

        meta_id = getattr(tab, "data_id", None)
        if meta_id is None:
            self.create_chat_context(tab)
            return

        core = self.window.core
        controller = self.window.controller
        if core.ctx.get_current() == meta_id:
            return
        meta = core.ctx.get_meta_by_id(meta_id)
        if meta is None:
            return
        pid_data = controller.chat.render.get_pid_data(tab.pid)
        if not pid_data or not pid_data.loaded:
            controller.ctx.load(meta.id, tab_pid=tab.pid)
        else:
            controller.ctx.select_on_list_only(meta.id)

    def on_load_ctx(self, meta: CtxMeta, pid: Optional[int] = None):
        """Bind a loaded context to an explicit chat PID (or active chat)."""
        tab = self.window.core.tabs.get_tab_by_pid(pid) if pid is not None else self.get_current_tab()
        if tab is not None and tab.type == Tab.TAB_CHAT:
            self.bind_chat(tab, meta.id)
        self.debug()

    def get_chat_tab_by_data_id(self, data_id: int) -> Optional[Tab]:
        if data_id is None:
            return None
        active_column = self.get_current_column_idx()
        tabs = [
            tab for tab in self.window.core.tabs.pids.values()
            if tab is not None and tab.type == Tab.TAB_CHAT and tab.data_id == data_id
        ]
        if not tabs:
            return None
        tabs.sort(key=lambda tab: (
            0 if tab.column_idx == active_column else 1,
            tab.column_idx,
            tab.idx if tab.idx is not None else 10**9,
            tab.pid,
        ))
        return tabs[0]

    def focus_chat_by_data_id(self, data_id: int) -> bool:
        tab = self.get_chat_tab_by_data_id(data_id)
        if tab is None:
            return False
        if tab.column_idx == 1 and not self.is_split_screen_enabled():
            self.enable_split_screen(update_switch=True)
        self.activate_tab(tab)
        return True

    def detach_chat_contexts(self, meta_ids) -> int:
        """Detach deleted contexts from chat tabs without closing the tabs.

        Every affected tab is converted into an empty placeholder: its context
        binding and renderer state are removed, its output is cleared by PID,
        and the tab title becomes ``...``. PID-based cleanup keeps bulk deletes
        deterministic even when affected tabs live in different columns.

        :param meta_ids: context ID or iterable of context IDs
        :return: number of detached tabs
        """
        if meta_ids is None:
            return 0
        if isinstance(meta_ids, (int, str)):
            meta_ids = [meta_ids]

        ids = set()
        for meta_id in meta_ids:
            try:
                ids.add(int(meta_id))
            except (TypeError, ValueError):
                continue
        if not ids:
            return 0

        targets = []
        for tab in self.window.core.tabs.pids.values():
            if tab is None or tab.type != Tab.TAB_CHAT or tab.data_id is None:
                continue
            try:
                matches = int(tab.data_id) in ids
            except (TypeError, ValueError):
                matches = False
            if matches:
                targets.append(tab)

        for tab in targets:
            # Clear the concrete view first; never rely on whichever column is
            # currently focused when contexts are removed in bulk.
            self.window.controller.chat.render.clear_pid(tab.pid)
            self.window.core.ctx.output.remove_pid(tab.pid)
            tab.data_id = None
            tab.loaded = False
            self.set_chat_placeholder(tab)

        if targets:
            self.window.core.tabs.save()
        return len(targets)

    def switch_to_first_chat(self):
        current = self.get_current_tab()
        if current is not None and current.type == Tab.TAB_CHAT:
            return

        # Prefer a chat already selected in a visible column, then any chat.
        for column_idx in range(self.window.core.tabs.NUM_COLS):
            tab = self.get_current_by_column(column_idx)
            if tab is not None and tab.type == Tab.TAB_CHAT:
                self.activate_tab(tab)
                return
        tab = self.window.core.tabs.get_first_by_type(Tab.TAB_CHAT)
        if tab is not None:
            self.activate_tab(tab)

    def focus_by_type(
        self,
        type: int,
        data_id: Optional[int] = None,
        title: Optional[str] = None,
        meta: Optional[CtxMeta] = None,
    ):
        """Focus a tab type without deriving the destination from widget focus."""
        current = self.get_current_tab()
        tab = current if current is not None and current.type == type else None

        if tab is None and current is not None:
            idx, column_idx, exists = self.window.core.tabs.get_closest_idx_by_type_exists(
                current, type, self.get_current_column_idx()
            )
            if exists:
                tab = self.window.core.tabs.get_tab_by_index(idx, column_idx)
        if tab is None:
            tab = self.window.core.tabs.get_first_by_type(type)
        if tab is None:
            return None

        if tab.column_idx == 1 and not self.is_split_screen_enabled():
            self.enable_split_screen(update_switch=True)

        target_meta_id = meta.id if meta is not None else data_id
        if tab.type == Tab.TAB_CHAT and target_meta_id is not None:
            self.bind_chat(tab, target_meta_id)
            if title is not None:
                self.update_title_by_tab(tab, title)

        if current is None or current.pid != tab.pid:
            self.activate_tab(tab, sync_context=False if target_meta_id is not None else True)

        # Usually the caller has already selected/loaded ``meta``. Only perform
        # a load when core.ctx is genuinely on a different context.
        if (meta is not None and tab.type == Tab.TAB_CHAT
                and not self._request_active()
                and self.window.core.ctx.get_current() != meta.id):
            self.window.controller.ctx.load(meta.id, tab_pid=tab.pid)

        self.debug()
        return tab

