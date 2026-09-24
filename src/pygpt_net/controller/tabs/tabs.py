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

from contextlib import contextmanager
from typing import Optional

from .state import TabState
from .handler import TabEventHandler
from .lifecycle import TabLifecycle
from .input import TabInput
from .split import TabSplit
from .titles import TabTitles
from .chat import ChatTabs
from .operations import TabOperations


class Tabs(TabLifecycle, TabSplit, TabInput, TabTitles, ChatTabs, TabOperations):
    """Public controller for output tabs.

    ``Controller.tabs`` is the only public entry point. Selection, PID routing
    and transient lifecycle flags are kept in one private ``TabState`` and are
    changed through methods instead of public writable attributes.
    """

    TAB_CHAT_MAX_CHARS = 15

    def __init__(self, window=None):
        self.window = window
        self._state = TabState()
        self.handler = TabEventHandler(self)

        # Non-selection lifecycle/UI state.
        self._focus_sync_scheduled = False
        self._context_sync_suppressed = 0
        self._tab_events_suppressed = 0
        self._selection_previous_target = None
        self._chat_input_suppressed = False
        self._chat_input_splitter_sizes = None

    # ---- lifecycle/state API ---------------------------------------------
    def lock(self):
        self._state.lock()

    def unlock(self):
        self._state.unlock()

    def is_locked(self) -> bool:
        return self._state.is_locked()

    def mark_initialized(self):
        self._state.mark_initialized()

    def mark_uninitialized(self):
        self._state.mark_uninitialized()

    def is_initialized(self) -> bool:
        return self._state.is_initialized()

    def begin_widget_loading(self):
        self._state.begin_widget_loading()

    def end_widget_loading(self):
        self._state.end_widget_loading()

    def is_widget_loading(self) -> bool:
        return self._state.is_widget_loading()

    def set_current_column_idx(self, column_idx: int):
        self._state.set_active_column(column_idx)

    def set_pending_focus_column(self, column_idx: Optional[int]):
        self._state.set_pending_focus_column(column_idx)

    def get_pending_focus_column(self) -> Optional[int]:
        return self._state.get_pending_focus_column()

    def get_column_pids(self) -> dict:
        return dict(self._state.pid_by_column)

    def clear_pending_focus_column(self):
        self._state.clear_pending_focus_column()

    @contextmanager
    def suspend_context_sync(self):
        """Prevent tab-selection events from recursively loading a context."""
        self._context_sync_suppressed += 1
        try:
            yield
        finally:
            self._context_sync_suppressed = max(0, self._context_sync_suppressed - 1)

    def is_context_sync_suppressed(self) -> bool:
        return self._context_sync_suppressed > 0

    @contextmanager
    def suspend_tab_events(self):
        """Ignore transient Qt tab signals during one structural mutation."""
        self._tab_events_suppressed += 1
        try:
            yield
        finally:
            self._tab_events_suppressed = max(0, self._tab_events_suppressed - 1)

    def are_tab_events_suppressed(self) -> bool:
        return self._tab_events_suppressed > 0

    # ---- single event API -------------------------------------------------
    def on_tab_changed(self, idx: int, column_idx: int = 0):
        return self.handler.on_tab_changed(idx, column_idx)

    def on_changed(self):
        return self.handler.on_changed()

    def on_column_changed(self):
        return self.handler.on_column_changed(self.get_current_column_idx())

    def on_tab_clicked(self, idx: int, column_idx: int = 0):
        return self.handler.on_tab_clicked(idx, column_idx)

    def on_column_focus(self, idx: int):
        return self.handler.on_column_focus(idx)

    def _apply_column_focus(self):
        return self.handler._apply_column_focus()

    def on_tab_dbl_clicked(self, idx: int, column_idx: int = 0):
        return self.handler.on_tab_dbl_clicked(idx, column_idx)

    def on_tab_closed(self, idx: int, column_idx: int = 0):
        return self.handler.on_tab_closed(idx, column_idx)

    def on_tab_moved(self, idx: int, column_idx: int = 0):
        return self.handler.on_tab_moved(idx, column_idx)
