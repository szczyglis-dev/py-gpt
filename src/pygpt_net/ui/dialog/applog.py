#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.25 12:00:00                  #
# ================================================== #

import os

from PySide6.QtGui import QTextCursor, Qt
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout

from pygpt_net.ui.widget.dialog.applog import AppLogDialog
from pygpt_net.ui.widget.element.labels import TitleLabel
from pygpt_net.ui.widget.textarea.editor import CodeEditor


class AppLog:
    def __init__(self, window=None):
        """
        App log dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup app log dialog"""
        id = 'app.log'

        self.window.ui.editor[id] = CodeEditor(self.window)
        self.window.ui.editor[id].setReadOnly(True)
        self.window.ui.editor[id].setProperty('class', 'text-editor')

        self.window.ui.nodes['editor.app.log.btn.open'] = QPushButton("OPEN (EXTERNAL)")
        self.window.ui.nodes['editor.app.log.btn.clear'] = QPushButton("CLEAR")
        self.window.ui.nodes['editor.app.log.btn.reload'] = QPushButton("RELOAD")

        self.window.ui.nodes['editor.app.log.btn.open'].clicked.connect(
            lambda: self.open_external())
        self.window.ui.nodes['editor.app.log.btn.clear'].clicked.connect(
            lambda: self.clear())
        self.window.ui.nodes['editor.app.log.btn.reload'].clicked.connect(
            lambda: self.reload())

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['editor.app.log.btn.open'])
        bottom_layout.addWidget(self.window.ui.nodes['editor.app.log.btn.clear'])
        bottom_layout.addWidget(self.window.ui.nodes['editor.app.log.btn.reload'])

        self.window.ui.paths[id] = TitleLabel("")

        self.window.ui.nodes['dialog.app.log.label'] = QLabel(self.get_log_path())
        self.window.ui.nodes['dialog.app.log.level'] = QLabel("")
        self.window.ui.nodes['dialog.app.log.level'].setAlignment(Qt.AlignRight)
        self.update_log_level()

        top = QHBoxLayout()
        top.addWidget(self.window.ui.nodes['dialog.app.log.label'])
        top.addWidget(self.window.ui.nodes['dialog.app.log.level'])

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.window.ui.editor['app.log'])
        layout.addLayout(bottom_layout)

        self.window.ui.dialog['app.log'] = AppLogDialog(self.window)
        self.window.ui.dialog['app.log'].setLayout(layout)
        self.window.ui.dialog['app.log'].setWindowTitle("app.log")

    def update_log_level(self):
        """Update log level"""
        level = self.window.core.debug.get_log_level_name().upper()
        self.window.ui.nodes['dialog.app.log.level'].setText("Log level: " + level)

    def update(self):
        """Update app log dialog"""
        self.window.ui.nodes['dialog.app.log.label'].setText(self.get_log_path())
        self.update_log_level()
        self.reload(show=False)

    def reload(self, show: bool = True):
        """
        Reload app.log file

        :param show: show dialog
        """
        path = self.get_log_path()

        # load data from log file
        if os.path.exists(path):
            try:
                with open(path, 'rb') as file:
                    content_bytes = file.read()
                    content = content_bytes.decode('utf-8', errors='ignore')
                    self.window.ui.editor['app.log'].setPlainText(content)
            except Exception as e:
                print(e)

        if show:
            self.window.ui.dialog['app.log'].show()

        # scroll to the end
        cursor = self.window.ui.editor['app.log'].textCursor()
        cursor.movePosition(QTextCursor.End)
        self.window.ui.editor['app.log'].setTextCursor(cursor)

    def get_log_path(self) -> str:
        """
        Get log file path

        :return: log path
        """
        return os.path.join(self.window.core.config.get_user_path(), 'app.log')

    def clear(self, force: bool = False):
        """
        Clear app.log file

        :param force: force clear
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='app.log.clear',
                id=-1,
                msg="Clear app.log file?",
            )
            return

        path = self.get_log_path()
        if os.path.exists(path):
            with open(path, 'w', encoding="utf-8") as file:
                file.write('')

        self.reload()

    def open_external(self):
        """Open log file in external editor"""
        path = self.get_log_path()
        if os.path.exists(path):
            self.window.controller.files.open(path)
        else:
            print("Log file not found!")
