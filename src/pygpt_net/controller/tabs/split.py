#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.25 11:30:00                  #
# ================================================== #

from PySide6.QtCore import QTimer, QVariantAnimation, QAbstractAnimation, QObject, QSignalBlocker

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSplitter

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.types.animation import PANEL_ANIMATION_DURATION_MS, PANEL_ANIMATION_EASING


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

    def _equalize_split_screen_columns(self):
        """Set both visible output columns to the same final width.

        ``setSizes([1, 1])`` is enough to reveal the collapsed second column,
        but the shared Chat input can be reparented immediately afterwards and
        change one column's size hint.  Apply the 50/50 geometry once that
        layout update has reached the event loop.
        """
        if not self.is_split_screen_enabled():
            return
        animation = getattr(self, "_split_animation", None)
        if animation is not None and animation.state() == QAbstractAnimation.Running:
            return

        splitter = self.window.ui.splitters.get('columns')
        if splitter is None or splitter.count() < 2:
            return

        try:
            sizes = splitter.sizes()
            total = sum(int(size) for size in sizes[:2])
            if total <= 0:
                total = max(2, int(splitter.width()) - int(splitter.handleWidth()))

            left = total // 2
            right = total - left
            splitter.setSizes([left, right])
        except (RuntimeError, TypeError, ValueError):
            return

    def _schedule_equal_split_screen_columns(self):
        """Equalize columns after Qt has processed split-screen layout changes."""
        QTimer.singleShot(0, self._equalize_split_screen_columns)

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
        self.sync_split_buttons()
        self._sync_chat_input_width()

    def _enable_split_screen(self, update_switch: bool = False):
        """
        Enable split screen mode

        :param update_switch: True if switch should be updated
        """
        if self.is_split_screen_enabled():
            return

        splitter = self.window.ui.splitters['columns']
        if isinstance(splitter, QSplitter):
            splitter.widget(1).show()
        splitter.setSizes([1, 1])
        self.window.core.config.set("layout.split", True)
        self.window.core.config.save()
        self._schedule_revealed_split_chat_restore()
        self.update_current()
        self._schedule_equal_split_screen_columns()
        self.sync_split_buttons()
        self._sync_chat_input_width()

        if update_switch:
            self.window.ui.nodes['layout.split'].box.setChecked(True)

    def _disable_split_screen(self):
        """
        Disable split screen mode
        """
        self.window.ui.splitters['columns'].setSizes([1, 0])
        self.set_current_column_idx(0)
        self.on_column_changed()
        self.window.core.config.set("layout.split", False)
        self.window.core.config.save()
        self.update_current()
        self.sync_split_buttons()
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

    def sync_split_buttons(self):
        """Display split screen only in the rightmost visible output tab bar."""
        state = self.is_split_screen_enabled()
        legacy = self.window.ui.nodes.get('layout.split')
        if legacy is not None and isinstance(legacy.box, QObject):
            blocker = QSignalBlocker(legacy.box)
            legacy.box.setChecked(state)
            del blocker
        splitter = self.window.ui.splitters.get('columns')
        if isinstance(splitter, QSplitter):
            splitter.widget(1).setVisible(state)
        column = 1 if state else 0
        for idx in (0, 1):
            button = self.window.ui.nodes.get(f'layout.split.button.{idx}')
            if button is not None:
                button.setIcon(QIcon(":/icons/right_double.svg" if state else ":/icons/split_screen.svg"))
                button.setVisible(idx == column)
                controls = button.parentWidget()
                controls.setVisible(idx == column or any(
                    not controls.layout().itemAt(i).widget().isHidden()
                    for i in range(controls.layout().count())
                ))

    def enable_split_screen(self, update_switch: bool = False):
        return self.set_split_screen(True, update_switch=update_switch)

    def disable_split_screen(self):
        return self.set_split_screen(False)

    def toggle_split_screen_animated(self, checked=False):
        animation = getattr(self, '_split_animation', None)
        running = animation is not None and animation.state() == QAbstractAnimation.Running
        state = self._split_animation_target if running else self.is_split_screen_enabled()
        return self.set_split_screen(not state, update_switch=True)

    def set_split_screen(self, state: bool, *, animated: bool = True,
                         update_switch: bool = True):
        """Shared right-column transition for toolbar, tools and automatic reveals."""
        splitter = self.window.ui.splitters['columns']
        # Non-widget callers (including controller tests) can use the same API.
        if not animated or not isinstance(self.window, QObject):
            self._stop_split_animation()
            if state:
                return self._enable_split_screen(update_switch)
            return self._disable_split_screen()
        sizes = splitter.sizes()
        animation = getattr(self, '_split_animation', None)
        running = animation is not None and animation.state() == QAbstractAnimation.Running
        if running and self._split_animation_target == state:
            return
        if not running and self.is_split_screen_enabled() == state and (sizes[1] > 0) == state:
            return
        self._stop_split_animation()
        self._split_animation_target = state
        if state:
            self._enable_split_screen(update_switch)
            # Set logical state before tab activation, but animate from the old geometry.
            splitter.setSizes(sizes)
        animation = QVariantAnimation(self.window)
        self._split_animation = animation
        total = sum(sizes)
        animation.setDuration(PANEL_ANIMATION_DURATION_MS)
        animation.setEasingCurve(PANEL_ANIMATION_EASING)
        animation.setStartValue(sizes[1])
        animation.setEndValue(total // 2 if state else 0)
        animation.valueChanged.connect(
            lambda width: splitter.setSizes([max(0, total - int(width)), int(width)])
        )
        animation.finished.connect(lambda: self._finish_split_animation(state))
        animation.start()

    def _stop_split_animation(self):
        animation = getattr(self, '_split_animation', None)
        if animation is not None:
            animation.stop()
            animation.deleteLater()
            self._split_animation = None

    def _finish_split_animation(self, opening):
        if not opening:
            self._disable_split_screen()
        else:
            self.sync_split_buttons()
            self._sync_chat_input_width()
