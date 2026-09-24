#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 11:00:00                  #
# ================================================== #

from typing import Any, Optional, Tuple

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans


class TabOperations:
    """Explicit tab operations. No operation derives its target from focus."""

    def debug(self):
        if self.window.controller.dialogs.debug.is_active("tabs"):
            self.window.core.tabs.toggle_debug(True)

    def add(
        self,
        type: int,
        title: str,
        icon: Optional[str] = None,
        child: Any = None,
        data_id: Optional[int] = None,
        tool_id: Optional[str] = None,
    ):
        return self.window.core.tabs.add(
            type=type,
            title=title,
            icon=icon,
            child=child,
            data_id=data_id,
            tool_id=tool_id,
        )

    def append(
        self,
        type: int,
        tool_id: Optional[str] = None,
        idx: int = 0,
        column_idx: int = 0,
        *,
        activate: bool = True,
        create_chat_context: bool = True,
        data_id: Optional[int] = None,
    ):
        """Create a tab in an explicit column and optionally activate it."""
        column_idx = int(column_idx)
        idx = int(idx)

        if type == Tab.TAB_TOOL and tool_id:
            existing = self.get_first_tab_by_tool(tool_id)
            if existing is not None:
                tool = self.window.tools.get(tool_id)
                if tool is not None and getattr(tool, "single_instance", False):
                    if activate and (existing.column_idx != 1 or self.is_split_screen_enabled()):
                        self.activate_tab(existing)
                    return existing

        # insertTab/removeTab can emit currentChanged synchronously. Treat the
        # structural change as a transaction and publish exactly one selection
        # after the core registry and Qt widget agree on the new tab identity.
        with self.suspend_tab_events():
            tab = self.window.core.tabs.append(
                type=type,
                idx=idx,
                column_idx=column_idx,
                tool_id=tool_id,
            )

        # Core also enforces single-instance tools; always trust the returned
        # tab's real identity/column rather than the requested coordinates.
        return self.handler.on_created(
            tab,
            activate=activate,
            create_chat_context=create_chat_context,
            data_id=data_id,
        )

    def activate_tab(self, tab: Tab, *, sync_context: bool = True):
        """Select one concrete tab by identity."""
        if tab is None:
            return None
        if sync_context:
            return self.switch_tab_by_idx(tab.idx, tab.column_idx)
        with self.suspend_context_sync():
            return self.switch_tab_by_idx(tab.idx, tab.column_idx)

    def get_current_idx(self, column_idx: Optional[int] = None) -> int:
        if column_idx is None:
            column_idx = self.get_current_column_idx()
        tab = self.get_current_by_column(int(column_idx))
        if tab is not None and tab.idx is not None:
            return int(tab.idx)
        return self._state.current_idx(column_idx)

    def get_current_column_idx(self) -> int:
        return self._state.get_active_column()

    def get_current_tab(self) -> Optional[Tab]:
        return self.get_current_by_column(self.get_current_column_idx())

    def get_current_type(self) -> Optional[int]:
        tab = self.get_current_tab()
        return tab.type if tab is not None else None

    def get_current_pid(self) -> Optional[int]:
        tab = self.get_current_tab()
        return tab.pid if tab is not None else None

    def get_type_by_idx(self, idx: int, column_idx: Optional[int] = None) -> Optional[int]:
        if column_idx is None:
            column_idx = self.get_current_column_idx()
        tab = self.window.core.tabs.get_tab_by_index(idx, column_idx)
        return tab.type if tab is not None else None

    def get_first_idx_by_type(self, type: int, column_idx: Optional[int] = None) -> Optional[int]:
        if column_idx is None:
            column_idx = self.get_current_column_idx()
        return self.window.core.tabs.get_min_idx_by_type(type, column_idx)

    def get_prev_idx_from(self, idx: int, column_idx: Optional[int] = None) -> Tuple[int, bool]:
        if column_idx is None:
            column_idx = self.get_current_column_idx()
        return self.window.core.tabs.get_prev_idx_from(idx, column_idx)

    def get_next_idx_from(self, idx: int, column_idx: Optional[int] = None) -> Tuple[int, bool]:
        if column_idx is None:
            column_idx = self.get_current_column_idx()
        return self.window.core.tabs.get_next_idx_from(idx, column_idx)

    def get_after_close_idx(self, idx: int, column_idx: Optional[int] = None) -> Optional[int]:
        prev_idx, exists = self.get_prev_idx_from(idx, column_idx)
        if exists:
            return prev_idx
        next_idx, exists = self.get_next_idx_from(idx, column_idx)
        return next_idx if exists else None

    def close(self, idx: int, column_idx: int = 0):
        self.handler.on_tab_closed(idx, column_idx)

    def close_all(self, type: int, column_idx: int = 0, force: bool = False):
        if not force:
            self.window.ui.dialogs.confirm(
                type='tab.close_all',
                id={"type": int(type), "column_idx": int(column_idx)},
                msg=trans('tab.close_all.confirm'),
            )
            return
        column_idx = int(column_idx)
        active_before = self.get_current_column_idx()
        with self.suspend_tab_events():
            self.window.core.tabs.remove_all_by_type(type, column_idx)

        if not self.is_split_screen_enabled():
            self.handler.on_column_changed(0)
        elif active_before == column_idx:
            self.handler.on_column_changed(column_idx)
        else:
            widget = self.window.ui.layout.get_tabs_by_idx(column_idx)
            idx = widget.currentIndex() if widget is not None else -1
            tab = self.window.core.tabs.get_tab_by_index(idx, column_idx) if idx >= 0 else None
            self._state.remember(column_idx, max(0, idx), getattr(tab, "pid", None) if tab else None)

        self.handler.on_changed()
        self.debug()

    def next_tab(self):
        column_idx = self.get_current_column_idx()
        tabs = self.window.ui.layout.get_tabs_by_idx(column_idx)
        if tabs is None or tabs.count() == 0:
            return
        self.switch_tab_by_idx((tabs.currentIndex() + 1) % tabs.count(), column_idx)

    def prev_tab(self):
        column_idx = self.get_current_column_idx()
        tabs = self.window.ui.layout.get_tabs_by_idx(column_idx)
        if tabs is None or tabs.count() == 0:
            return
        self.switch_tab_by_idx((tabs.currentIndex() - 1) % tabs.count(), column_idx)

    def switch_tab(self, type: int):
        tab = self.window.core.tabs.get_first_by_type(type)
        if tab is not None:
            self.activate_tab(tab)

    def switch_tab_by_idx(self, idx: int, column_idx: Optional[int] = None):
        if column_idx is None:
            column_idx = self.get_current_column_idx()
        column_idx = int(column_idx)
        tabs = self.window.ui.layout.get_tabs_by_idx(column_idx)
        if tabs is None or idx is None or idx < 0 or idx >= tabs.count():
            return None
        tab = self.window.core.tabs.get_tab_by_index(idx, column_idx)
        if tab is None:
            return None

        # State is updated before Qt emits currentChanged, making re-entrant
        # callbacks deterministic and independent of keyboard focus. Qt emits
        # currentChanged synchronously when the index actually changes.
        previous = self._state.target()
        if previous is not None and (previous.pid != tab.pid or previous.column_idx != column_idx):
            self._selection_previous_target = previous
        self._state.activate(column_idx, idx, tab.pid)
        if tabs.currentIndex() != idx:
            tabs.setCurrentIndex(idx)
        else:
            self.handler.on_tab_changed(idx, column_idx)
        return tab

    def open_by_type(self, type: int):
        self.switch_tab(type)

    def new_tab(self, column_idx: int = 0):
        """Create a new chat exactly in the column that invoked the action."""
        column_idx = int(column_idx)
        idx = self.window.core.tabs.get_max_idx_by_column(column_idx)
        return self.append(
            type=Tab.TAB_CHAT,
            tool_id=None,
            idx=max(-1, idx),
            column_idx=column_idx,
            activate=True,
            create_chat_context=True,
        )

    def open_chat_context(self, meta_id: int, column_idx: int, after_idx: Optional[int] = None):
        """Create a chat tab already bound to ``meta_id`` and activate it."""
        column_idx = int(column_idx)
        if after_idx is None:
            after_idx = self.window.core.tabs.get_max_idx_by_column(column_idx)
        return self.append(
            type=Tab.TAB_CHAT,
            idx=max(-1, int(after_idx)),
            column_idx=column_idx,
            activate=True,
            create_chat_context=False,
            data_id=meta_id,
        )

    def restore_data(self):
        """Restore visual selections, then publish visible tabs deterministically."""
        titles_changed = self.sync_chat_titles()
        data = self.window.core.config.get("tabs.opened", [])
        selected = {}

        # QTabWidget selection is restored as one silent structural phase. No
        # context is loaded until both columns have their final persisted index.
        with self.suspend_context_sync():
            if data:
                for col_idx, tab_idx in data.items():
                    col_idx = int(col_idx)
                    widget = self.window.ui.layout.get_tabs_by_idx(col_idx)
                    tab_idx = int(tab_idx)
                    if widget is None or widget.count() == 0:
                        continue
                    tab_idx = max(0, min(tab_idx, widget.count() - 1))
                    widget.setCurrentIndex(tab_idx)
                    tab = self.window.core.tabs.get_tab_by_index(tab_idx, col_idx)
                    self._state.remember(col_idx, tab_idx, getattr(tab, "pid", None) if tab else None)
                    selected[col_idx] = tab_idx
            else:
                widget = self.window.ui.layout.get_tabs_by_idx(0)
                if widget is not None and widget.count() > 0:
                    widget.setCurrentIndex(0)
                    selected[0] = 0

        # Publish explicit targets only after visual restoration is complete.
        # Restore the secondary visible column first and column 0 last, keeping
        # startup/profile behavior deterministic while still preloading both
        # chats when split screen is enabled.
        columns = [0]
        if self.is_split_screen_enabled():
            columns.insert(0, 1)
        for col_idx in columns:
            widget = self.window.ui.layout.get_tabs_by_idx(col_idx)
            if widget is None or widget.count() == 0:
                continue
            idx = selected.get(col_idx, widget.currentIndex())
            if idx is None or idx < 0:
                continue
            self.handler.on_tab_changed(int(idx), int(col_idx))

        if titles_changed:
            self.window.core.tabs.save()
        self.debug()

    def move_tab(self, idx: int, column_idx: int, new_column_idx: int, new_idx: int = None):
        tab = self.window.core.tabs.get_tab_by_index(idx, column_idx)
        if tab is None:
            return None
        pid = tab.pid
        self.lock()
        try:
            with self.suspend_tab_events():
                self.window.core.tabs.move_tab(tab, int(new_column_idx), new_idx=new_idx)
        finally:
            self.unlock()
        moved = self.window.core.tabs.get_tab_by_pid(pid)
        self._state.drop_pid(pid)
        old_widget = self.window.ui.layout.get_tabs_by_idx(int(column_idx))
        if old_widget is not None and old_widget.count() > 0:
            old_idx = old_widget.currentIndex()
            old_current = self.window.core.tabs.get_tab_by_index(old_idx, int(column_idx))
            self._state.remember(
                int(column_idx),
                max(0, old_idx),
                getattr(old_current, "pid", None) if old_current else None,
            )
        if moved is not None:
            self.activate_tab(moved)
        self.debug()
        return moved

    def is_current_by_type(self, type: int) -> bool:
        for column_idx in range(self.window.core.tabs.NUM_COLS):
            tab = self.get_current_by_column(column_idx)
            if tab is not None and tab.type == type:
                return True
        return False

    def is_current_tool(self, tool_id: str) -> bool:
        for column_idx in range(self.window.core.tabs.NUM_COLS):
            tab = self.get_current_by_column(column_idx)
            if tab is not None and tab.tool_id == tool_id:
                return True
        return False

    def get_current_by_column(self, column_idx: int) -> Optional[Tab]:
        """Return the logical selection for one column, with Qt as fallback."""
        column_idx = int(column_idx)
        pid = self._state.current_pid(column_idx)
        if pid is not None:
            tab = self.window.core.tabs.get_tab_by_pid(pid)
            if tab is not None and int(tab.column_idx) == column_idx:
                return tab

        # Startup/rebuild fallback: state is intentionally empty until the
        # persisted QTabWidget selections have been restored. Import that one
        # concrete selection into TabState, then use PID identity afterwards.
        tabs = self.window.ui.layout.get_tabs_by_idx(column_idx)
        if tabs is None:
            return None
        idx = tabs.currentIndex()
        if idx < 0:
            return None
        tab = self.window.core.tabs.get_tab_by_index(idx, column_idx)
        if tab is not None:
            self._state.remember(column_idx, idx, tab.pid)
        return tab

    def get_tabs_by_tool(self, tool_id: str) -> list:
        tabs = [
            tab for tab in self.window.core.tabs.pids.values()
            if tab is not None and tab.type == Tab.TAB_TOOL and tab.tool_id == tool_id
        ]
        return sorted(tabs, key=lambda tab: tab.pid if tab.pid is not None else 10**9)

    def is_tool(self, tool_id: str) -> bool:
        return bool(self.get_tabs_by_tool(tool_id))

    def get_first_tab_by_tool(self, tool_id: str) -> Optional[Tab]:
        tabs = self.get_tabs_by_tool(tool_id)
        return tabs[0] if tabs else None

    def switch_to_first_tab_by_tool(self, tool_id: str):
        tab = self.get_first_tab_by_tool(tool_id)
        if tab is not None:
            self.activate_tab(tab)

    def get_tool_column(self, tool_id: str) -> Optional[int]:
        for column_idx in range(self.window.core.tabs.NUM_COLS):
            tab = self.get_current_by_column(column_idx)
            if tab is not None and tab.tool_id == tool_id:
                return column_idx
        return None
