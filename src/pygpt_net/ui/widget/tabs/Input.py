#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.17 20:05:00                  #
# ================================================== #

from PySide6.QtWidgets import QTabWidget, QMenu, QWidget, QStyle
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans


class InputTabs(QTabWidget):
    def __init__(self, window=None):
        super().__init__(window)
        self.window = window
        self._attachments_tab_index = 1
        self._compact_tab_tooltips = {
            1: 'attachments.tab',
            2: 'attachments_uploaded.tab',
            3: 'attachments_uploaded.tab',
        }
        self._context_menu = QMenu(self)
        self._action_clear = QAction(QIcon(":/icons/delete.svg"), trans('attachments.btn.clear'), self)
        self._action_clear.triggered.connect(self._on_clear_triggered)
        self._context_menu.addAction(self._action_clear)
        self._header_widget = None

    def _current_page_hint_height(self, minimum: bool = False) -> int:
        """Return a vertical hint based only on the currently visible page.

        QTabWidget normally includes hidden pages when calculating its minimum
        size. Attachments/Uploaded are intentionally taller than ChatInput, so
        keeping that default would make the vertical output/input splitter stay
        locked at the files-tab minimum after switching back to Input.
        """
        page = self.currentWidget()
        page_h = 0
        if page is not None:
            try:
                hint = page.minimumSizeHint() if minimum else page.sizeHint()
                page_h = max(0, int(hint.height()))
            except Exception:
                page_h = 0

        tab_h = 0
        try:
            tab_h = max(0, int(self.tabBar().sizeHint().height()))
        except Exception:
            pass

        if self._header_widget is not None:
            try:
                tab_h = max(tab_h, int(self._header_widget.sizeHint().height()))
            except Exception:
                pass

        frame = 0
        try:
            frame = 2 * max(0, int(self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)))
        except Exception:
            pass

        return max(0, page_h + tab_h + frame)

    def minimumSizeHint(self) -> QSize:
        """Do not let a taller hidden files page constrain the input pane."""
        base = super().minimumSizeHint()
        height = max(self.minimumHeight(), self._current_page_hint_height(minimum=True))
        return QSize(base.width(), height)

    def sizeHint(self) -> QSize:
        """Prefer the active page height instead of the tallest hidden page."""
        base = super().sizeHint()
        height = max(self.minimumHeight(), self._current_page_hint_height(minimum=False))
        return QSize(base.width(), height)

    def set_compact_tab_count(self, index: int, count: int = 0):
        """Show only an optional numeric count next to a compact icon tab."""
        try:
            count = int(count)
        except (TypeError, ValueError):
            count = 0
        self.setTabText(index, str(count) if count > 0 else '')
        key = self._compact_tab_tooltips.get(index)
        if key is not None:
            self.setTabToolTip(index, trans(key))

    def retranslate_compact_tabs(self):
        """Refresh tooltips without restoring verbose tab labels."""
        for index, key in self._compact_tab_tooltips.items():
            self.setTabToolTip(index, trans(key))

    def set_header_widget(self, widget: QWidget):
        """
        Place a widget in the input tab bar row.

        :param widget: widget to display next to the tabs
        """
        self._header_widget = widget
        self.setCornerWidget(widget, Qt.TopRightCorner)

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: QMouseEvent
        """
        if event.button() == Qt.RightButton:
            tb = self.tabBar()
            pos_in_tabbar = tb.mapFrom(self, event.pos())
            if tb.tabAt(pos_in_tabbar) == self._attachments_tab_index:
                self.show_context_menu(event.globalPos())

        super().mousePressEvent(event)

    def show_context_menu(self, global_pos):
        """
        Show context menu for attachments tab

        :param global_pos: QPoint
        """
        self._action_clear.setText(trans('attachments.btn.clear'))
        self._context_menu.exec(global_pos)

    def _on_clear_triggered(self, checked=False):
        self.window.controller.attachment.clear()