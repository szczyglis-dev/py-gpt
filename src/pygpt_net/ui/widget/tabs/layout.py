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
import weakref

from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtWidgets import QApplication, QTabWidget, QWidget, QVBoxLayout, QSplitter, QSizePolicy

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

        # Each output column owns its own vertical splitter.  The lower pane is
        # only a host for the *shared* Chat input widget; no editor/input state
        # is duplicated between columns.  OutputLayout moves that one widget to
        # the focused chat column and collapses the host in the other column.
        self.input_host = QWidget(self)
        self.input_host.setObjectName(f'chatInputHost{self.idx}')
        self.input_host_layout = QVBoxLayout(self.input_host)
        self.input_host_layout.setContentsMargins(0, 0, 0, 0)
        self.input_host_layout.setSpacing(0)
        self.input_host.hide()

        self.splitter = QSplitter(Qt.Vertical, self)
        self.splitter.addWidget(self.tabs)
        self.splitter.addWidget(self.input_host)
        self.splitter.setCollapsible(1, True)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.splitter)
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
        self.window.controller.tabs.on_column_focus(self.idx)
        if widget is not None and not widget.hasFocus():
            widget.setFocus()

    def set_idx(self, idx: int):
        """
        Set index

        :param idx: int
        """
        self.idx = idx
        self.input_host.setObjectName(f'chatInputHost{idx}')

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

    def get_input_splitter(self) -> QSplitter:
        """Return this column's output/input splitter."""
        return self.splitter

    def contains_input(self, widget: QWidget) -> bool:
        """Return True when ``widget`` is mounted in this column's input host."""
        if widget is None:
            return False
        return widget.parentWidget() is self.input_host or self.input_host.isAncestorOf(widget)

    def mount_input(self, widget: QWidget):
        """Mount the shared Chat input widget in this column."""
        if widget is None:
            return
        if widget.parentWidget() is not self.input_host:
            old_parent = widget.parentWidget()
            if old_parent is not None and old_parent.layout() is not None:
                old_parent.layout().removeWidget(widget)
            widget.setParent(self.input_host)
            self.input_host_layout.addWidget(widget)
        self.input_host.show()
        widget.show()

    def hide_input(self):
        """Collapse this column's lower input host without destroying it."""
        self.input_host.hide()

    def unmount_input(self, widget: QWidget):
        """Detach the shared input from this host before moving it elsewhere."""
        if widget is None or not self.contains_input(widget):
            self.hide_input()
            return
        self.input_host_layout.removeWidget(widget)
        self.hide_input()


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

        # Promote interaction with the shared composer to the column that
        # currently owns it. Use QApplication.focusChanged instead of a global
        # event filter: focusChanged is emitted after Qt has completed the focus
        # transition, and tabs.on_column_focus() is itself deferred/coalesced.
        # This avoids mutating/reparenting the widget tree from inside a raw
        # MouseButtonPress/FocusIn event, which can crash Qt at C++ level.
        app = QApplication.instance()
        if app is not None:
            app.focusChanged.connect(self._on_app_focus_changed)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.splitter, stretch=1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def get_input_splitter(self, idx: int) -> Optional[QSplitter]:
        """Return the vertical output/input splitter for a column."""
        column = self.get_column_by_idx(idx)
        return column.get_input_splitter() if column is not None else None

    def get_input_column_idx(self, widget: QWidget) -> Optional[int]:
        """Return the column currently hosting the shared Chat input."""
        for column in self.columns:
            if column.contains_input(widget):
                return column.get_idx()
        return None

    def mount_chat_input(self, widget: QWidget, column_idx: int) -> Optional[QSplitter]:
        """Move the single Chat input widget under ``column_idx``.

        ``main.output`` remains a compatibility alias used by the existing
        input sizing code.  It always points at the splitter that currently
        owns the shared input widget.
        """
        column = self.get_column_by_idx(column_idx)
        if column is None or widget is None:
            return None

        for other in self.columns:
            if other is not column:
                other.unmount_input(widget)

        column.mount_input(widget)
        splitter = column.get_input_splitter()
        self.window.ui.splitters['main.output'] = splitter
        return splitter

    def hide_chat_input(self, widget: QWidget) -> Optional[QSplitter]:
        """Hide the lower input pane while keeping its owning column known."""
        column_idx = self.get_input_column_idx(widget)
        column = self.get_column_by_idx(column_idx) if column_idx is not None else None
        if column is None:
            return None
        column.hide_input()
        splitter = column.get_input_splitter()
        self.window.ui.splitters['main.output'] = splitter
        return splitter

    def _on_app_focus_changed(self, _old, current):
        """Route composer focus to the column that currently hosts it.

        The column switch is requested only after Qt has finished changing
        focus.  tabs.on_column_focus() performs the actual switch on the next
        event-loop turn, so no input widget is reparented while its focus event
        is still being dispatched.
        """
        if current is None or not isinstance(current, QWidget):
            return

        root = self.window.ui.nodes.get('input.root')
        if root is None or not root.isVisible():
            return

        try:
            inside = current is root or root.isAncestorOf(current)
        except RuntimeError:
            return
        if not inside:
            return

        column_idx = self.get_input_column_idx(root)
        if column_idx is not None:
            self.window.controller.tabs.on_column_focus(column_idx)

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
                    self.window.controller.tabs.on_split_screen_changed(False)
            else:
                if self._was_width_zero is not False:
                    self._was_width_zero = False
                    self.window.controller.tabs.on_split_screen_changed(True)

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
        current = self.window.controller.tabs.get_current_column_idx()
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
        current = self.window.controller.tabs.get_current_column_idx()
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