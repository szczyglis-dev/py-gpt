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

from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication

from pygpt_net.core.events import AppEvent
from pygpt_net.core.tabs.tab import Tab


class TabEventHandler:
    """Central entrypoint for all Qt/output-tab events."""

    def __init__(self, tabs):
        self.tabs = tabs

    @property
    def window(self):
        return self.tabs.window

    def _resolve(self, idx: int, column_idx: int) -> Optional[Tab]:
        if idx is None or int(idx) < 0:
            return None
        return self.window.core.tabs.get_tab_by_index(int(idx), int(column_idx))

    def _select_state(self, tab: Tab, idx: int, column_idx: int) -> None:
        t = self.tabs
        previous = t._state.target()
        if (t._selection_previous_target is None and previous is not None
                and (previous.pid != getattr(tab, "pid", None)
                     or previous.column_idx != int(column_idx))):
            t._selection_previous_target = previous
        t._state.activate(column_idx, idx, getattr(tab, "pid", None))


    def on_created(
        self,
        tab: Tab,
        *,
        activate: bool = True,
        create_chat_context: bool = True,
        data_id: Optional[int] = None,
    ):
        """Finalize one tab creation after the structural mutation has ended."""
        if tab is None:
            return None
        if tab.type == Tab.TAB_CHAT and data_id is not None:
            self.tabs.bind_chat(tab, data_id)

        if activate:
            self.tabs.activate_tab(tab, sync_context=(data_id is None))

        if (tab.type == Tab.TAB_CHAT and data_id is None
                and create_chat_context and tab.data_id is None):
            self.tabs.create_chat_context(tab)

        self.tabs.debug()
        return tab

    def on_deleted(
        self,
        pid: int,
        column_idx: int,
        idx_after: Optional[int],
        *,
        activate_column: bool,
    ):
        """Finalize one deletion without changing an unrelated active column."""
        t = self.tabs
        t._state.drop_pid(pid)
        tabs_widget = self.window.ui.layout.get_tabs_by_idx(column_idx)
        if tabs_widget is not None and tabs_widget.count() > 0:
            if idx_after is None:
                idx_after = min(max(0, tabs_widget.currentIndex()), tabs_widget.count() - 1)
            idx_after = max(0, min(int(idx_after), tabs_widget.count() - 1))
            if activate_column:
                t.switch_tab_by_idx(idx_after, column_idx)
            else:
                tab = self._resolve(idx_after, column_idx)
                t._state.remember(
                    column_idx,
                    idx_after,
                    getattr(tab, "pid", None) if tab else None,
                )
        else:
            t._state.clear_column_pid(column_idx)
            if activate_column and column_idx != 0:
                self.on_column_focus(0)

        self.on_changed()
        t.update_current()
        t.debug()

    def on_tab_changed(self, idx: int, column_idx: int = 0):
        """Apply a concrete QTabWidget currentChanged event."""
        t = self.tabs
        if (idx == -1 or not t.is_initialized() or t.is_widget_loading()
                or t.are_tab_events_suppressed()):
            return
        if column_idx != 0 and not t.is_split_screen_enabled():
            return

        tab = self._resolve(idx, column_idx)
        if tab is None:
            return

        prev = t._selection_previous_target or t._state.target()
        self._select_state(tab, idx, column_idx)
        t._selection_previous_target = None

        w = self.window
        w.controller.ui.mode.update()
        w.controller.ui.vision.update()

        if tab.type == Tab.TAB_NOTEPAD:
            w.controller.notepad.opened_once = True
            w.controller.notepad.on_open(idx, column_idx)
        elif tab.type == Tab.TAB_CHAT:
            if not t._request_active() and not t.is_context_sync_suppressed():
                meta_id = getattr(tab, "data_id", None)
                if meta_id is not None:
                    w.core.ctx.output.prepare_meta(tab)
                    meta = w.core.ctx.get_meta_by_id(meta_id)
                    if meta is not None:
                        pid_data = w.controller.chat.render.get_pid_data(tab.pid)
                        if not pid_data or not pid_data.loaded:
                            w.controller.ctx.load(meta.id, tab_pid=tab.pid)
                        else:
                            w.controller.ctx.select_on_list_only(meta.id)

            QTimer.singleShot(0, lambda pid=tab.pid: w.controller.chat.render.remeasure_user_messages(pid))
            QTimer.singleShot(120, lambda pid=tab.pid: w.controller.chat.render.remeasure_user_messages(pid))
        elif tab.type == Tab.TAB_TOOL_PAINTER:
            if w.core.config.get('vision.capture.enabled'):
                w.controller.camera.enable_capture()
        elif tab.type == Tab.TAB_TOOL_CALENDAR:
            w.controller.calendar.update()
            w.controller.calendar.update_ctx_counters()

        if prev is None or prev.pid != tab.pid or prev.column_idx != column_idx:
            w.dispatch(AppEvent(AppEvent.TAB_SELECTED))

        self.on_changed(tab)
        w.controller.ui.update()
        t.update_current()
        t._sync_chat_input_width()
        t.debug()

    def on_changed(self, tab: Optional[Tab] = None):
        if tab is None:
            tab = self.tabs.get_current_tab()
        if tab is None:
            return
        self.window.controller.audio.on_tab_changed(tab)
        self.tabs.debug()

    def on_column_changed(self, column_idx: Optional[int] = None):
        """Synchronize one explicit column; never infer it from focus."""
        t = self.tabs
        if t.is_locked():
            return
        if column_idx is None:
            column_idx = t.get_current_column_idx()
        column_idx = int(column_idx)
        if not t.is_split_screen_enabled():
            column_idx = 0

        layout = self.window.ui.layout
        tabs_widget = layout.get_tabs_by_idx(column_idx)
        if tabs_widget is None:
            return
        tabs_widget.set_active(True)
        second = layout.get_tabs_by_idx(1 if column_idx == 0 else 0)
        if second is not None:
            second.set_active(False)

        idx = tabs_widget.currentIndex()
        tab = self._resolve(idx, column_idx)
        if tab is None:
            t._state.activate(column_idx, max(0, idx), None)
            return
        self._select_state(tab, idx, column_idx)
        t._selection_previous_target = None

        if not t._request_active() and tab.type == Tab.TAB_CHAT and tab.data_id is not None:
            current_ctx = self.window.core.ctx.get_current()
            if current_ctx != tab.data_id:
                pid_data = self.window.controller.chat.render.get_pid_data(tab.pid)
                if column_idx == 1 and not getattr(tab, "loaded", False):
                    meta = self.window.core.ctx.get_meta_by_id(tab.data_id)
                    if meta is not None:
                        self.window.controller.ctx.load(meta.id, no_fresh=True, tab_pid=tab.pid)
                    tab.loaded = True
                elif pid_data and pid_data.loaded:
                    self.window.controller.ctx.select_on_list_only(tab.data_id)

        self.window.controller.ui.update()
        t.update_current()
        t._sync_chat_input_width()
        t.debug()

    def on_tab_clicked(self, idx: int, column_idx: int = 0):
        tab = self._resolve(idx, column_idx)
        if tab is None:
            return
        widget = self.window.ui.layout.get_tabs_by_idx(column_idx)
        self._select_state(tab, idx, column_idx)
        if widget is not None and widget.currentIndex() != idx:
            widget.setCurrentIndex(idx)
            return
        self.on_column_changed(column_idx)
        self.on_changed(tab)

    def on_column_focus(self, column_idx: int):
        t = self.tabs
        column_idx = int(column_idx)
        if not t.is_split_screen_enabled():
            column_idx = 0
        if column_idx == t.get_current_column_idx():
            t.clear_pending_focus_column()
            return
        t.set_pending_focus_column(column_idx)
        if t._focus_sync_scheduled:
            return
        t._focus_sync_scheduled = True
        QTimer.singleShot(0, self._apply_column_focus)

    def _apply_column_focus(self):
        t = self.tabs
        t._focus_sync_scheduled = False
        column_idx = t.get_pending_focus_column()
        t.clear_pending_focus_column()
        if column_idx is None:
            return
        if not t.is_split_screen_enabled():
            column_idx = 0
        if column_idx == t.get_current_column_idx():
            return

        app = QGuiApplication.instance()
        focused_widget = app.focusWidget() if app else None
        widget = self.window.ui.layout.get_tabs_by_idx(column_idx)
        idx = widget.currentIndex() if widget is not None else 0
        tab = self._resolve(idx, column_idx)
        t._state.activate(column_idx, max(0, idx), getattr(tab, "pid", None) if tab else None)
        self.on_column_changed(column_idx)
        self.on_changed(tab)

        if focused_widget and focused_widget.isVisible() and not focused_widget.hasFocus():
            try:
                focused_widget.setFocus(Qt.OtherFocusReason)
            except Exception:
                pass

    def on_tab_dbl_clicked(self, idx: int, column_idx: int = 0):
        self.on_tab_changed(idx, column_idx)

    def on_tab_closed(self, idx: int, column_idx: int = 0):
        t = self.tabs
        if t.is_locked():
            return
        tab = self._resolve(idx, column_idx)
        if tab is None:
            return
        closing_pid = tab.pid
        activate_column = t.get_current_column_idx() == int(column_idx)

        tabs_widget = self.window.ui.layout.get_tabs_by_idx(column_idx)
        current_before = tabs_widget.currentIndex() if tabs_widget is not None else idx
        if current_before == idx:
            idx_after = idx - 1 if idx > 0 else (0 if tabs_widget is not None and tabs_widget.count() > 1 else None)
        else:
            idx_after = current_before - 1 if current_before > idx else current_before

        with t.suspend_tab_events():
            self.window.core.tabs.remove_tab_by_idx(idx, column_idx)
        self.on_deleted(
            closing_pid,
            column_idx,
            idx_after,
            activate_column=activate_column,
        )

    def on_tab_moved(self, idx: int, column_idx: int = 0):
        if self.tabs.is_locked() or self.tabs.are_tab_events_suppressed():
            return
        self.window.core.tabs.update_column(column_idx)
        widget = self.window.ui.layout.get_tabs_by_idx(column_idx)
        current_idx = widget.currentIndex() if widget is not None else -1
        tab = self._resolve(current_idx, column_idx)
        if tab is not None:
            self.tabs._state.remember(column_idx, current_idx, tab.pid)
        self.tabs.update_current()
        self.tabs.debug()
