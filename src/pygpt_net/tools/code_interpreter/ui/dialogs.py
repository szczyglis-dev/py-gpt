#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 17:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QSplitter, QCheckBox, QLabel, QWidget, QMenuBar

from pygpt_net.tools.code_interpreter.ui.widgets import PythonInput, PythonOutput
from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.utils import trans

class Interpreter:
    def __init__(self, window=None):
        """
        Python interpreter dialog

        :param window: Window instance
        """
        self.window = window
        self.menu_bar = None
        self.menu = {}
        self.actions = {}  # menu actions

    def setup_menu(self) -> QMenuBar:
        """
        Setup dialog menu

        :return: QMenuBar
        """
        # create menu bar
        self.menu_bar = QMenuBar()
        self.menu["file"] = self.menu_bar.addMenu(trans("interpreter.menu.file"))
        self.menu["kernel"] = self.menu_bar.addMenu(trans("interpreter.menu.kernel"))

        self.actions["file.clear_output"] = QAction(QIcon(":/icons/close.svg"),
                                                    trans("interpreter.menu.file.clear_output"))
        self.actions["file.clear_output"].triggered.connect(
            lambda: self.window.tools.get("interpreter").clear_output()
        )
        self.actions["file.clear_history"] = QAction(QIcon(":/icons/close.svg"),
                                                    trans("interpreter.menu.file.clear_history"))
        self.actions["file.clear_history"].triggered.connect(
            lambda: self.window.tools.get("interpreter").clear_history()
        )
        self.actions["file.clear_all"] = QAction(QIcon(":/icons/close.svg"),
                                                   trans("interpreter.menu.file.clear_all"))
        self.actions["file.clear_all"].triggered.connect(
            lambda: self.window.tools.get("interpreter").clear_all()
        )

        self.actions["kernel.restart"] = QAction(QIcon(":/icons/reload.svg"),
                                                      trans("interpreter.menu.kernel.restart"))
        self.actions["kernel.restart"].triggered.connect(
            lambda: self.window.tools.get("interpreter").restart_kernel()
        )

        # add actions
        self.menu["file"].addAction(self.actions["file.clear_output"])
        self.menu["file"].addAction(self.actions["file.clear_history"])
        self.menu["file"].addAction(self.actions["file.clear_all"])
        self.menu["kernel"].addAction(self.actions["kernel.restart"])
        return self.menu_bar

    def setup(self):
        """Setup interpreter dialog"""
        self.window.interpreter = PythonOutput(self.window)
        self.window.interpreter.setReadOnly(True)

        self.window.ui.nodes['interpreter.code'] = PythonOutput(self.window)
        self.window.ui.nodes['interpreter.code'].textChanged.connect(
            lambda: self.window.tools.get("interpreter").store_history()
        )
        self.window.ui.nodes['interpreter.code'].setReadOnly(False)
        self.window.ui.nodes['interpreter.code'].excluded_copy_to = ["interpreter_edit"]

        self.window.ui.nodes['interpreter.output_label'] = QLabel(trans("interpreter.edit_label.output"))
        self.window.ui.nodes['interpreter.edit_label'] = QLabel(trans("interpreter.edit_label.edit"))

        self.window.ui.nodes['interpreter.all'] = QCheckBox(trans("interpreter.all"))
        self.window.ui.nodes['interpreter.all'].setChecked(True)
        self.window.ui.nodes['interpreter.all'].clicked.connect(
            lambda: self.window.tools.get("interpreter").toggle_all()
        )

        self.window.ui.nodes['interpreter.auto_clear'] = QCheckBox(trans("interpreter.auto_clear"))
        self.window.ui.nodes['interpreter.auto_clear'].setChecked(False)
        self.window.ui.nodes['interpreter.auto_clear'].clicked.connect(
            lambda: self.window.tools.get("interpreter").toggle_auto_clear()
        )

        self.window.ui.nodes['interpreter.ipython'] = QCheckBox("IPython")
        self.window.ui.nodes['interpreter.ipython'].setChecked(True)
        self.window.ui.nodes['interpreter.ipython'].clicked.connect(
            lambda: self.window.tools.get("interpreter").toggle_ipython()
        )

        self.window.ui.nodes['interpreter.btn.clear'] = QPushButton(trans("interpreter.btn.clear"))
        self.window.ui.nodes['interpreter.btn.clear'].clicked.connect(
            lambda: self.window.tools.get("interpreter").clear())

        self.window.ui.nodes['interpreter.btn.send'] = QPushButton(trans("interpreter.btn.send"))
        self.window.ui.nodes['interpreter.btn.send'].clicked.connect(
            lambda: self.window.tools.get("interpreter").send_input()
        )

        self.window.ui.nodes['interpreter.input'] = PythonInput(self.window)
        self.window.ui.nodes['interpreter.input'].setPlaceholderText(trans("interpreter.input.placeholder"))
        self.window.ui.nodes['interpreter.input'].excluded_copy_to = ["interpreter_input"]

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.window.ui.nodes['interpreter.output_label'])
        left_layout.addWidget(self.window.interpreter)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.window.ui.nodes['interpreter.edit_label'])
        right_layout.addWidget(self.window.ui.nodes['interpreter.code'])
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        right_widget.setMinimumWidth(300)

        self.window.ui.splitters['interpreter.columns'] = QSplitter(Qt.Horizontal)
        self.window.ui.splitters['interpreter.columns'].addWidget(left_widget)
        self.window.ui.splitters['interpreter.columns'].addWidget(right_widget)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['interpreter.btn.clear'])
        bottom_layout.addWidget(self.window.ui.nodes['interpreter.ipython'])
        bottom_layout.addWidget(self.window.ui.nodes['interpreter.auto_clear'])
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.window.ui.nodes['interpreter.all'])
        bottom_layout.addWidget(self.window.ui.nodes['interpreter.btn.send'])

        edit_layout = QVBoxLayout()
        edit_layout.addWidget(self.window.ui.splitters['interpreter.columns'])
        edit_layout.setContentsMargins(0, 0, 0, 0)

        edit_widget = QWidget()
        edit_widget.setLayout(edit_layout)

        self.window.ui.splitters['interpreter'] = QSplitter(Qt.Vertical)
        self.window.ui.splitters['interpreter'].addWidget(edit_widget)
        self.window.ui.splitters['interpreter'].addWidget(self.window.ui.nodes['interpreter.input'])
        self.window.ui.splitters['interpreter'].setStretchFactor(0, 4)
        self.window.ui.splitters['interpreter'].setStretchFactor(1, 1)

        layout = QVBoxLayout()
        layout.setMenuBar(self.setup_menu())  # add menu bar
        layout.addWidget(self.window.ui.splitters['interpreter'])
        layout.addLayout(bottom_layout)

        self.window.ui.dialog['interpreter'] = InterpreterDialog(self.window)
        self.window.ui.dialog['interpreter'].setLayout(layout)
        self.window.ui.dialog['interpreter'].setWindowTitle(trans("dialog.interpreter.title"))
        self.window.ui.dialog['interpreter'].resize(800, 500)


class InterpreterDialog(BaseDialog):
    def __init__(self, window=None, id="interpreter"):
        """
        Interpreter dialog

        :param window: main window
        :param id: logger id
        """
        super(InterpreterDialog, self).__init__(window, id)
        self.window = window

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.cleanup()
        super(InterpreterDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()  # close dialog when the Esc key is pressed.
        else:
            super(InterpreterDialog, self).keyPressEvent(event)

    def cleanup(self):
        """
        Cleanup on close
        """
        if self.window is None:
            return
        self.window.tools.get("interpreter").opened = False
        self.window.tools.get("interpreter").close()
        self.window.tools.get("interpreter").update()
