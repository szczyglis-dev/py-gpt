#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QPlainTextEdit, QPushButton, QHBoxLayout, QLabel, QVBoxLayout

from core.ui.widgets import FileEditorDialog
from core.utils import trans


class Editor:
    def __init__(self, window=None):
        """
        Editor dialog

        :param window: main window object
        """
        self.window = window

    def setup(self):
        """Setups config editor dialog"""
        id = 'config'

        self.window.editor[id] = QPlainTextEdit()
        self.window.editor[id].setReadOnly(False)

        self.window.data['editor.btn.default'] = QPushButton(trans("dialog.editor.btn.defaults"))
        self.window.data['editor.btn.save'] = QPushButton(trans("dialog.editor.btn.save"))
        self.window.data['editor.btn.default'].clicked.connect(
            lambda: self.window.settings.load_default_editor())
        self.window.data['editor.btn.save'].clicked.connect(
            lambda: self.window.settings.save_editor())

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.data['editor.btn.default'])
        bottom_layout.addWidget(self.window.data['editor.btn.save'])

        self.window.path_label[id] = QLabel("")
        self.window.path_label[id].setStyleSheet(self.window.controller.theme.get_style('text_bold'))

        self.window.data['dialog.editor.label'] = QLabel(trans('dialog.editor.label'))

        layout = QVBoxLayout()
        layout.addWidget(self.window.data['dialog.editor.label'])
        layout.addWidget(self.window.path_label[id])
        layout.addWidget(self.window.editor['config'])
        layout.addLayout(bottom_layout)

        self.window.dialog['config.editor'] = FileEditorDialog(self.window)
        self.window.dialog['config.editor'].setLayout(layout)
        self.window.dialog['config.editor'].setWindowTitle(trans('dialog.editor.title'))
