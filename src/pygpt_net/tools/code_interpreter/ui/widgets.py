#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.10 23:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit, QApplication, QVBoxLayout, QLabel, QCheckBox, QPushButton, QWidget, QSplitter, \
    QHBoxLayout

from pygpt_net.ui.widget.textarea.editor import BaseCodeEditor

from pygpt_net.utils import trans
import pygpt_net.icons_rc


class ToolWidget:
    def __init__(self, window=None, tool=None):
        """
        Python Code Interpreter

        :param window: Window instance
        :param tool: Tool instance
        """
        self.window = window # window instance
        self.tool = tool  # tool instance
        self.history = None # history
        self.input = None  # input
        self.output = None  # output
        self.checkbox_all = None  # all checkbox
        self.checkbox_auto_clear = None  # auto clear checkbox
        self.checkbox_ipython = None  # IPython checkbox
        self.btn_send = None  # send button
        self.btn_clear = None  # clear button
        self.label_output = None  # output label
        self.label_history = None  # history label

    def set_tab(self, tab):
        """
        Set tab

        :param tab: Tab
        """
        self.output.set_tab(tab)
        self.input.set_tab(tab)

    def setup(self, all: bool = True) -> QVBoxLayout:
        """
        Setup widget body

        :param all: with all widgets
        :return: QVBoxLayout
        """
        self.output = PythonOutput(self.window, self.tool)
        self.output.setReadOnly(True)

        if all:
            self.history = PythonOutput(self.window, self.tool)
            self.history.textChanged.connect(
                lambda: self.tool.store_history(self)
            )
            self.history.setReadOnly(False)
            self.history.excluded_copy_to = ["interpreter_edit"]

        self.label_output = QLabel(trans("interpreter.edit_label.output"))
        self.label_history = QLabel(trans("interpreter.edit_label.edit"))

        if all:
            self.checkbox_all = QCheckBox(trans("interpreter.all"))
            self.checkbox_all.setChecked(True)
            self.checkbox_all.clicked.connect(
                lambda: self.tool.toggle_all(self)
            )

        self.checkbox_auto_clear = QCheckBox(trans("interpreter.auto_clear"))
        self.checkbox_auto_clear.setChecked(False)
        self.checkbox_auto_clear.clicked.connect(
            lambda: self.tool.toggle_auto_clear(self)
        )

        self.checkbox_ipython = QCheckBox("IPython")
        self.checkbox_ipython.setChecked(True)
        self.checkbox_ipython.clicked.connect(
            lambda: self.tool.toggle_ipython(self)
        )

        self.btn_clear = QPushButton(trans("interpreter.btn.clear"))
        self.btn_clear.clicked.connect(
            lambda: self.tool.clear(self)
        )

        self.btn_send = QPushButton(trans("interpreter.btn.send"))
        self.btn_send.clicked.connect(
            lambda: self.tool.send_input(self)
        )

        self.input = PythonInput(self.window, self.tool, self)
        self.input.setPlaceholderText(trans("interpreter.input.placeholder"))
        self.input.excluded_copy_to = ["interpreter_input"]

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.label_output)
        left_layout.addWidget(self.output)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        self.window.ui.splitters['interpreter.columns'] = QSplitter(Qt.Horizontal)
        self.window.ui.splitters['interpreter.columns'].addWidget(left_widget)

        if all:
            right_layout = QVBoxLayout()
            right_layout.addWidget(self.label_history)
            right_layout.addWidget(self.history)
            right_layout.setContentsMargins(0, 0, 0, 0)
            right_widget = QWidget()
            right_widget.setLayout(right_layout)
            right_widget.setMinimumWidth(300)
            self.window.ui.splitters['interpreter.columns'].addWidget(right_widget)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.btn_clear)
        bottom_layout.addWidget(self.checkbox_ipython)
        bottom_layout.addWidget(self.checkbox_auto_clear)
        bottom_layout.addStretch()
        if all:
            bottom_layout.addWidget(self.checkbox_all)
        bottom_layout.addWidget(self.btn_send)

        edit_layout = QVBoxLayout()
        edit_layout.addWidget(self.window.ui.splitters['interpreter.columns'])
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_widget = QWidget()
        edit_widget.setLayout(edit_layout)

        self.window.ui.splitters['interpreter'] = QSplitter(Qt.Vertical)
        self.window.ui.splitters['interpreter'].addWidget(edit_widget)
        self.window.ui.splitters['interpreter'].addWidget(self.input)
        self.window.ui.splitters['interpreter'].setStretchFactor(0, 4)
        self.window.ui.splitters['interpreter'].setStretchFactor(1, 1)

        # connect signals
        self.tool.signals.update.connect(self.set_output)
        self.tool.signals.update_history.connect(self.set_history)
        self.tool.signals.clear_history.connect(self.clear_history)
        self.tool.signals.clear_output.connect(self.clear_output)
        self.tool.signals.focus_input.connect(self.set_focus)
        self.tool.signals.append_input.connect(self.append_to_input)
        self.tool.signals.update_input.connect(self.set_input)
        self.tool.signals.set_checkbox_all.connect(self.set_checkbox_all)
        self.tool.signals.set_checkbox_auto_clear.connect(self.set_checkbox_auto_clear)
        self.tool.signals.set_checkbox_ipython.connect(self.set_checkbox_ipython)
        self.tool.signals.toggle_all_visible.connect(self.toggle_all_visible)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.splitters['interpreter'])
        layout.addLayout(bottom_layout)
        return layout

    @Slot(str, str)
    def set_output(self, output: str, type="stdout", live: bool = True):
        """
        Set output content

        :param output: Content
        :param type: Output type
        :param live: Live output
        """
        area = self.output
        if type == "stdin":
            data = ">> " + str(output)
        else:
            data = str(output)
        if live:
            cur = area.textCursor()
            cur.movePosition(QTextCursor.End)
            s = data + "\n"
            while s:
                head, sep, s = s.partition("\n")
                cur.insertText(head)
                if sep:  # New line if LF
                    cur.insertText("\n")
            area.setTextCursor(cur)
        else:
            area.setPlainText(data)

    @Slot()
    def set_history(self, data: str):
        """
        Set history

        :param data: history data
        """
        if not self.history:
            return
        self.history.setPlainText(data)
        cur = self.history.textCursor()
        cur.movePosition(QTextCursor.End)
        self.history.setTextCursor(cur)

    @Slot()
    def append_to_input(self, data: str):
        """
        Append data to input

        :param data: Data
        """
        current = self.input.toPlainText()
        if current:
            current += "\n"
        current += data
        self.input.setPlainText(current)

    @Slot(str)
    def set_input(self, data: str):
        """
        Set input

        :param data: Data
        """
        self.input.setPlainText(data)

    @Slot()
    def clear_history(self):
        """Clear input"""
        if not self.history:
            return
        self.history.clear()

    @Slot()
    def clear_output(self):
        """Clear output"""
        self.output.clear()

    @Slot()
    def set_focus(self):
        """Set focus to input"""
        self.input.setFocus()

    @Slot(bool)
    def set_checkbox_all(self, value: bool):
        """
        Set checkbox all

        :param value: Value
        """
        if not self.checkbox_all:
            return
        self.checkbox_all.setChecked(value)

    @Slot(bool)
    def set_checkbox_auto_clear(self, value: bool):
        """
        Set checkbox auto clear

        :param value: Value
        """
        self.checkbox_auto_clear.setChecked(value)

    @Slot(bool)
    def set_checkbox_ipython(self, value: bool):
        """
        Set checkbox IPython

        :param value: Value
        """
        self.checkbox_ipython.setChecked(value)

    @Slot(bool)
    def toggle_all_visible(self, value: bool):
        """
        Toggle all visible

        :param value: Value
        """
        if not self.checkbox_all:
            return
        if value:
            self.checkbox_all.setVisible(True)
        else:
            self.checkbox_all.setVisible(False)


class PythonInput(QTextEdit):
    def __init__(self, window=None, tool=None, widget=None):
        """
        Python interpreter input

        :param window: main window
        """
        super(PythonInput, self).__init__(window)
        self.window = window
        self.tool = tool
        self.widget = widget
        self.setAcceptRichText(False)
        self.value = 12
        self.max_font_size = 42
        self.min_font_size = 8
        self.setProperty('class', 'interpreter-input')
        self.default_stylesheet = ""
        self.setStyleSheet(self.default_stylesheet)
        self.textChanged.connect(
            lambda: self.tool.update_input()
        )
        self.setFocus()
        self.tab = None
        self.installEventFilter(self)

    def set_tab(self, tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if event.type() == event.Type.FocusIn:
            if self.tab is not None:
                col_idx = self.tab.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
        return super().eventFilter(source, event)

    def update_stylesheet(self, data: str):
        """
        Update stylesheet

        :param data: stylesheet CSS
        """
        self.setStyleSheet(self.default_stylesheet + data)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(PythonInput, self).keyPressEvent(event)
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            mode = self.window.core.config.get('send_mode')
            if mode > 0:  # Enter or Shift + Enter
                if mode == 2:  # Shift + Enter
                    modifiers = QApplication.keyboardModifiers()
                    if modifiers == QtCore.Qt.ShiftModifier:
                        self.tool.send_input(self.widget)
                else:  # Enter
                    modifiers = QApplication.keyboardModifiers()
                    if modifiers != QtCore.Qt.ShiftModifier:
                        self.tool.send_input(self.widget)
                self.setFocus()

    def wheelEvent(self, event):
        """
        Wheel event: set font size

        :param event: Event
        """
        if event.modifiers() & Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                if self.value < self.max_font_size:
                    self.value += 1
            else:
                if self.value > self.min_font_size:
                    self.value -= 1

            size_str = f"{self.value}px"
            self.update_stylesheet(f"font-size: {size_str};")
            event.accept()
        else:
            super(PythonInput, self).wheelEvent(event)


class PythonOutput(BaseCodeEditor):
    def __init__(self, window=None, tool=None):
        """
        Python interpreter output

        :param window: main window
        """
        super(PythonOutput, self).__init__(window)
        self.window = window
        self.tool = tool
        self.setReadOnly(True)
        self.value = 12
        self.max_font_size = 42
        self.min_font_size = 8
        self.setProperty('class', 'interpreter-output')
        self.default_stylesheet = ""
        self.setStyleSheet(self.default_stylesheet)
        self.tab = None
        self.installEventFilter(self)

    def set_tab(self, tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if event.type() == event.Type.FocusIn:
            if self.tab is not None:
                col_idx = self.tab.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
        return super().eventFilter(source, event)

    def clear_content(self):
        """Clear content"""
        super(PythonOutput, self).clear_content()
        self.tool.save_output()


class ToolSignals(QObject):
    update = Signal(str, str, bool)  # content, type, live
    update_history = Signal(str)  # content
    update_input = Signal(str) # content
    append_input = Signal(str) # content
    reload = Signal(str)  # path
    clear_history = Signal()
    clear_output = Signal()
    focus_input = Signal()
    set_checkbox_all = Signal(bool)
    set_checkbox_auto_clear = Signal(bool)
    set_checkbox_ipython = Signal(bool)
    toggle_all_visible = Signal(bool)