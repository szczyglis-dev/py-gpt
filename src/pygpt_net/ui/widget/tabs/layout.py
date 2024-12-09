#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.09 03:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtWidgets import QTabWidget, QWidget, QVBoxLayout, QSplitter, QSizePolicy

from pygpt_net.ui.widget.tabs.output import OutputTabs


class OutputColumn(QWidget):
    def __init__(self, window=None):
        """
        Output column

        :param window: window instance
        """
        super(OutputColumn, self).__init__(window)
        self.window = window
        self.idx = -1
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

        column1 = OutputColumn(self.window)
        column2 = OutputColumn(self.window)
        self.add_column(column1)
        self.add_column(column2)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        for column in self.columns:
            self.splitter.addWidget(column)

        self.window.ui.splitters['columns'] = self.splitter

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.splitter, stretch=1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

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

    def get_tabs_by_idx(self, idx: int) -> OutputTabs:
        """
        Get tabs by column index

        :param idx: int
        :return: OutputTabs
        """
        for column in self.columns:
            if column.idx == idx:
                return column.tabs
        return None

    def get_active_tabs(self) -> OutputTabs:
        """
        Get active tabs

        :return: OutputTabs
        """
        current = self.window.controller.ui.tabs.get_current_column_idx()
        for column in self.columns:
            if column.idx == current:
                return column.tabs

    def get_column_by_idx(self, idx: int) -> OutputColumn:
        """
        Get column by index

        :param idx: int
        :return: OutputColumn
        """
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
        for column in self.columns:
            if column.idx == current:
                return column

class FocusEventFilter(QObject):
    def __init__(self, column, callback):
        """
        Column event filter

        :param column: parent column
        :param callback: callback
        """
        super().__init__()
        self.column = column
        self.callback = callback

    def eventFilter(self, obj, event):
        """
        Click event filter

        :param obj: object
        :param event: event
        """
        if event.type() == QEvent.MouseButtonPress or event.type() == QEvent.FocusIn:
            widget = obj
            if widget is not None:
                self.callback(widget)
            return False
        return False
