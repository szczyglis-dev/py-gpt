#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QPlainTextEdit, QPushButton, QHBoxLayout, QLabel, QVBoxLayout

from ..widget.dialog import FileEditorDialog
from ...utils import trans


class Editor:
    def __init__(self, window=None):
        """
        Editor dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup config editor dialog"""
        id = 'config'

        self.window.editor[id] = QPlainTextEdit()
        self.window.editor[id].setReadOnly(False)

        self.window.ui.nodes['editor.btn.default'] = QPushButton(trans("dialog.editor.btn.defaults"))
        self.window.ui.nodes['editor.btn.save'] = QPushButton(trans("dialog.editor.btn.save"))
        self.window.ui.nodes['editor.btn.default'].clicked.connect(
            lambda: self.window.app.settings.load_default_editor())
        self.window.ui.nodes['editor.btn.save'].clicked.connect(
            lambda: self.window.app.settings.save_editor())

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['editor.btn.default'])
        bottom_layout.addWidget(self.window.ui.nodes['editor.btn.save'])

        self.window.ui.paths[id] = QLabel("")
        self.window.ui.paths[id].setStyleSheet(self.window.controller.theme.get_style('text_bold'))

        self.window.ui.nodes['dialog.editor.label'] = QLabel(trans('dialog.editor.label'))

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['dialog.editor.label'])
        layout.addWidget(self.window.ui.paths[id])
        layout.addWidget(self.window.editor['config'])
        layout.addLayout(bottom_layout)

        self.window.dialog['config.editor'] = FileEditorDialog(self.window)
        self.window.dialog['config.editor'].setLayout(layout)
        self.window.dialog['config.editor'].setWindowTitle(trans('dialog.editor.title'))
