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

from PySide6.QtCore import QTimer

from pygpt_net.core.tabs.tab import Tab


class TabSplit:
    def _restore_revealed_split_chat(self, column_idx: int = 1):
        """Restore the selected chat when a previously hidden column is revealed.

        On startup with split-screen disabled, the hidden column's QTabWidget
        still restores its selected tab and the tab keeps its ``data_id``. The
        actual chat renderer is intentionally not populated, however, because
        hidden-column ``on_tab_changed`` events are ignored. When split-screen
        is enabled later, rebuild only that selected chat output without
        changing the globally selected context/focused column.

        :param column_idx: column that has just become visible
        """
        if self._request_active():
            # Never disturb request/render ownership while a response is in
            # flight. A later explicit focus/tab change will synchronize the
            # chat through the normal path.
            return

        w = self.window
        tabs = w.ui.layout.get_tabs_by_idx(column_idx)
        if tabs is None:
            return

        idx = tabs.currentIndex()
        if idx < 0:
            return

        tab = w.core.tabs.get_tab_by_index(idx, column_idx)
        if tab is None or tab.type != Tab.TAB_CHAT or tab.data_id is None:
            return

        meta = w.core.ctx.get_meta_by_id(tab.data_id)
        if meta is None:
            return

        # If this renderer already knows the PID, the chat has either been
        # rendered already or is currently loading. Do not reset it just because
        # the split view was toggled off and on again. Fresh application starts
        # with the hidden column absent from renderer state, which is the case we
        # need to repair here.
        if w.controller.chat.render.get_pid_data(tab.pid) is not None:
            return

        output = w.core.ctx.output
        previous_pid = output.get_pinned_pid(meta)
        pinned_pid = output.pin_render_pid(meta, pid=tab.pid, force=True)
        if pinned_pid != tab.pid:
            return

        try:
            w.controller.ctx.refresh_output(meta)
        finally:
            if previous_pid is not None:
                output.render_pids[meta.id] = previous_pid
            else:
                output.unpin_render_pid(meta=meta)

    def _schedule_revealed_split_chat_restore(self):
        """Restore column 2 after Qt has applied the new splitter geometry."""
        QTimer.singleShot(0, lambda: self._restore_revealed_split_chat(1))

    def is_split_screen_enabled(self) -> bool:
        """
        Check if split screen mode is enabled

        :return: True if split screen is enabled, False otherwise
        """
        return self.window.core.config.get("layout.split", False)

    def on_split_screen_changed(self, state: bool):
        """
        On split screen mode changed

        :param state: True if split screen is enabled
        """
        prev_state = self.is_split_screen_enabled()
        self.window.core.config.set("layout.split", state)
        if prev_state != state:
            if self.window.ui.nodes['layout.split'].box.isChecked() != state:
                self.window.ui.nodes['layout.split'].box.setChecked(state)
            self.window.core.config.save()
            if state:
                # This path also handles revealing the second column by
                # dragging the splitter instead of using the toolbar switch.
                self._schedule_revealed_split_chat_restore()
            self.update_current()
        self._sync_chat_input_width()

    def enable_split_screen(self, update_switch: bool = False):
        """
        Enable split screen mode

        :param update_switch: True if switch should be updated
        """
        if self.is_split_screen_enabled():
            return

        self.window.ui.splitters['columns'].setSizes([1, 1])
        self.window.core.config.set("layout.split", True)
        self.window.core.config.save()
        self._schedule_revealed_split_chat_restore()
        self.update_current()
        self._sync_chat_input_width()

        if update_switch:
            self.window.ui.nodes['layout.split'].box.setChecked(True)

    def disable_split_screen(self):
        """
        Disable split screen mode
        """
        self.window.ui.splitters['columns'].setSizes([1, 0])
        self.set_current_column_idx(0)
        self.on_column_changed()
        self.window.core.config.set("layout.split", False)
        self.window.core.config.save()
        self.update_current()
        self._sync_chat_input_width()

    def toggle_split_screen(self, state):
        """
        Toggle split screen mode

        :param state: True if split screen is enabled
        """
        if state:
            self.enable_split_screen()
        else:
            self.disable_split_screen()
