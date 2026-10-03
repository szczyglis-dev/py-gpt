#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 12:40:00                  #
# ================================================== #

from PySide6.QtWidgets import QTabWidget, QMenu, QWidget, QStyle
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans


class InputTabs(QTabWidget):
    def __init__(self, window=None):
        super().__init__(window)
        self.window = window
        self._attachments_tab_index = 1
        self._uploaded_tab_index = 3
        self._context_tab_index = None
        self._compact_tab_tooltips = {
            0: 'input.tab',
            1: 'attachments.tab',
            2: 'attachments_uploaded.tab',
            3: 'attachments_uploaded.tab',
        }
        self.tabBar().setObjectName('inputCompactTabs')
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
            tab_index = tb.tabAt(pos_in_tabbar)
            if tab_index in (self._attachments_tab_index, self._uploaded_tab_index):
                self._context_tab_index = tab_index
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
        if self._context_tab_index == self._uploaded_tab_index:
            self.window.controller.chat.attachment.clear()
        else:
            self.window.controller.attachment.clear()
        self._context_tab_index = None

class ChatComposer(QWidget):
    """Single chat input with compatibility hooks for legacy tab controllers.

    Attachment lists remain controller-owned state, never selectable pages.
    Media mode exposes a compact normal/negative prompt switch.
    """

    def __init__(self, window, page, extra):
        super().__init__(window)
        from PySide6.QtWidgets import QVBoxLayout, QTabBar, QStackedWidget
        self._page = page
        self.window = window
        self._extra = extra
        self._extra_enabled = False
        self._prompt_tabs = QTabBar(self)
        self._prompt_tabs.setExpanding(False)
        self._prompt_tabs.addTab(trans('input.tab'))
        self._prompt_tabs.addTab(trans('input.tab.extra.negative_prompt'))
        self._prompt_tabs.hide()
        self._stack = QStackedWidget(self)
        self._stack.addWidget(page)
        self._stack.addWidget(extra)
        self._prompt_tabs.currentChanged.connect(self._stack.setCurrentIndex)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._prompt_tabs)
        layout.addWidget(self._stack)

    def currentIndex(self):
        return 4 if self._stack.currentIndex() == 1 else 0

    def currentWidget(self):
        return self._stack.currentWidget()

    def setCurrentIndex(self, index):
        self._prompt_tabs.setCurrentIndex(1 if index == 4 and self._extra_enabled else 0)

    def isTabVisible(self, index):
        return index == 0 or (index == 4 and self._extra_enabled)

    def setTabVisible(self, index, visible):
        if index == 4:
            self._extra_enabled = bool(visible)
            self._prompt_tabs.setVisible(visible)
            if not visible:
                self.setCurrentIndex(0)
            self.layout().invalidate()
            self.updateGeometry()
            if self.window is not None:
                QTimer.singleShot(0, self._refresh_input_height)

    def _refresh_input_height(self):
        nodes = self.window.ui.nodes
        root = nodes.get('input.root')
        if root is not None:
            if self._extra_enabled:
                if not hasattr(self, '_root_minimum_before_media'):
                    self._root_minimum_before_media = root.minimumHeight()
                # The responsive composer positions its content manually;
                # minimumSizeHint alone does not constrain the outer pane.
                band = getattr(nodes['input'], '_attachment_row_height', 0)
                root.setMinimumHeight(max(root.minimumSizeHint().height(),
                                          135 + self._prompt_tabs.sizeHint().height() + band))
            elif hasattr(self, '_root_minimum_before_media'):
                root.setMinimumHeight(self._root_minimum_before_media)
                del self._root_minimum_before_media
        for key in ('input.container', 'input.root'):
            widget = nodes.get(key)
            if widget is not None:
                widget.updateGeometry()
        nodes['input'].fit_to_content()

    def setTabText(self, index, text):
        if index in (0, 4):
            self._prompt_tabs.setTabText(1 if index == 4 else 0, text)

    def set_compact_tab_count(self, index, count=0):
        pass

    def retranslate_compact_tabs(self):
        self.setTabText(0, trans('input.tab'))
        self.setTabText(4, trans('input.tab.extra.negative_prompt'))
