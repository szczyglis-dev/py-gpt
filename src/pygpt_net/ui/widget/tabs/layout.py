#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.25 18:00:00                  #
# ================================================== #

from typing import Optional
import weakref

from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QSplitter, QSizePolicy

from pygpt_net.ui.widget.tabs.output import OutputTabs


class OutputColumn(QWidget):
    def __init__(self, window=None, idx: Optional[int] = None):
        """
        Output column

        :param window: window instance
        """
        super(OutputColumn, self).__init__(window)
        self.window = window
        self.idx = -1
        if idx is not None:
            self.idx = idx
        self.tabs = OutputTabs(self.window, column=self)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tabs)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.filter = FocusEventFilter(self, self.on_focus)
        self.installEventFilter(self.filter)
        self.setFocusPolicy(Qt.StrongFocus)

    def on_focus(self, widget):
        """
        On widget clicked

        :param widget: widget
        """
        self.window.controller.ui.tabs.on_column_focus(self.idx)
        if widget is not None and not widget.hasFocus():
            widget.setFocus()

    def set_idx(self, idx: int):
        """
        Set index

        :param idx: int
        """
        self.idx = idx

    def get_idx(self) -> int:
        """
        Get index

        :return: int
        """
        return self.idx

    def set_tabs(self, tabs: QTabWidget):
        """
        Set tabs widget

        :param tabs: QTabWidget
        """
        self.tabs = tabs

    def get_tabs(self) -> OutputTabs:
        """
        Get tabs

        :return: OutputTabs
        """
        return self.tabs


class OutputLayout(QWidget):
    def __init__(self, window=None):
        """
        Output layout

        :param window: window instance
        """
        super(OutputLayout, self).__init__(window)
        self.window = window
        self.columns = []
        self._was_width_zero = None

        column1 = OutputColumn(self.window, idx=0)
        column2 = OutputColumn(self.window, idx=1)
        self.add_column(column1)
        self.add_column(column2)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        for column in self.columns:
            self.splitter.addWidget(column)
        self.splitter.splitterMoved.connect(self.handle_splitter_moved)

        self.window.ui.splitters['columns'] = self.splitter

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.splitter, stretch=1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def handle_splitter_moved(self, pos, index):
        """
        Handle splitter moved event
        :param pos: Position of the splitter
        :param index: Index of the widget that was moved
        """
        if self.splitter.count() > 1:
            sizes = self.splitter.sizes()
            current_width = sizes[1] if len(sizes) > 1 else 0
            if current_width == 0:
                if self._was_width_zero is not True:
                    self._was_width_zero = True
                    self.window.controller.ui.tabs.on_split_screen_changed(False)
            else:
                if self._was_width_zero is not False:
                    self._was_width_zero = False
                    self.window.controller.ui.tabs.on_split_screen_changed(True)

    def get_next_idx(self) -> int:
        """
        Get next index

        :return: int
        """
        return len(self.columns)

    def add_column(self, column: OutputColumn):
        """
        Add column

        :param column: OutputColumn
        """
        idx = self.get_next_idx()
        column.set_idx(idx)
        self.columns.append(column)

    def get_tabs_by_idx(self, idx: int) -> Optional[OutputTabs]:
        """
        Get tabs by column index

        :param idx: int
        :return: OutputTabs
        """
        column = self.get_column_by_idx(idx)
        return column.tabs if column is not None else None

    def get_active_tabs(self) -> OutputTabs:
        """
        Get active tabs

        :return: OutputTabs
        """
        current = self.window.controller.ui.tabs.get_current_column_idx()
        column = self.get_column_by_idx(current)
        if column is not None:
            return column.tabs

    def get_column_by_idx(self, idx: int) -> Optional[OutputColumn]:
        """
        Get column by index

        :param idx: int
        :return: OutputColumn
        """
        if 0 <= idx < len(self.columns):
            column = self.columns[idx]
            if column.idx == idx:
                return column
        for column in self.columns:
            if column.idx == idx:
                return column
        return None

    def get_active_column(self) -> OutputColumn:
        """
        Get active column

        :return: OutputColumn
        """
        current = self.window.controller.ui.tabs.get_current_column_idx()
        return self.get_column_by_idx(current)


class FocusEventFilter(QObject):
    def __init__(self, column, callback):
        """
        Column event filter

        :param column: parent column
        :param callback: callback
        """
        super().__init__(column)
        self._column_ref = weakref.ref(column)
        self._callback = weakref.WeakMethod(callback) if hasattr(callback, "__self__") and callback.__self__ is not None else callback

    def eventFilter(self, obj, event):
        """
        Click event filter

        :param obj: object
        :param event: event
        """
        t = event.type()
        if t in (QEvent.MouseButtonPress, QEvent.FocusIn):
            col = self._column_ref()
            if col is not None:
                if isinstance(self._callback, weakref.WeakMethod):
                    cb = self._callback()
                else:
                    cb = self._callback
                if cb is not None:
                    cb(obj)
            return False
        return False