#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.19 01:00:00                  #
# ================================================== #
import os

from PySide6.QtWidgets import QPlainTextEdit, QPushButton, QHBoxLayout, QLabel, QVBoxLayout

from pygpt_net.ui.widget.dialog.editor_file import EditorFileDialog
from pygpt_net.ui.widget.element.labels import TitleLabel
from pygpt_net.ui.widget.textarea.editor import CodeEditor
from pygpt_net.utils import trans


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

        self.window.ui.editor[id] = CodeEditor(self.window)
        self.window.ui.editor[id].setReadOnly(False)
        self.window.ui.editor[id].setProperty('class', 'code-editor')

        self.window.ui.nodes['editor.btn.default'] = QPushButton(trans("dialog.editor.btn.defaults"))
        self.window.ui.nodes['editor.btn.save'] = QPushButton(trans("dialog.editor.btn.save"))
        self.window.ui.nodes['editor.btn.default'].clicked.connect(
            lambda: self.window.core.settings.load_default_editor())
        self.window.ui.nodes['editor.btn.save'].clicked.connect(
            lambda: self.window.core.settings.save_editor())

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['editor.btn.default'])
        bottom_layout.addWidget(self.window.ui.nodes['editor.btn.save'])

        self.window.ui.paths[id] = TitleLabel("")

        self.window.ui.nodes['dialog.editor.label'] = QLabel(trans('dialog.editor.label'))

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['dialog.editor.label'])
        layout.addWidget(self.window.ui.paths[id])
        layout.addWidget(self.window.ui.editor['config'])
        layout.addLayout(bottom_layout)

        self.window.ui.dialog['config.editor'] = EditorFileDialog(self.window)
        self.window.ui.dialog['config.editor'].setLayout(layout)
        self.window.ui.dialog['config.editor'].setWindowTitle(trans('dialog.editor.title'))


class CustomEditor:
    def __init__(self, window=None):
        """
        Custom Editor dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self, id: str = None) -> EditorFileDialog:
        """
        Setup custom file editor dialog instance

        :param id: editor id
        :return: EditorFileDialog instance
        """
        self.window.ui.editor[id] = CodeEditor(self.window)
        self.window.ui.editor[id].setReadOnly(False)
        self.window.ui.editor[id].setProperty('class', 'code-editor')
        self.window.ui.editor[id].textChanged.connect(
            lambda: self.on_changed(id))

        self.window.ui.nodes['editor.custom.btn.default'] = QPushButton(trans("action.refresh"))
        self.window.ui.nodes['editor.custom.btn.save'] = QPushButton(trans("dialog.editor.btn.save"))
        self.window.ui.nodes['editor.custom.btn.default'].clicked.connect(
            lambda: self.window.core.filesystem.editor.restore(id))
        self.window.ui.nodes['editor.custom.btn.save'].clicked.connect(
            lambda: self.window.core.filesystem.editor.save(id))

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['editor.custom.btn.default'])
        bottom_layout.addWidget(self.window.ui.nodes['editor.custom.btn.save'])

        self.window.ui.paths[id] = TitleLabel("")
        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.paths[id])
        layout.addWidget(self.window.ui.editor[id])
        layout.addLayout(bottom_layout)

        dialog = EditorFileDialog(self.window)
        dialog.disable_geometry_store = True  # disable geometry store
        dialog.id = id
        dialog.setLayout(layout)
        dialog.setWindowTitle('')

        return dialog

    def on_changed(self, id: str):
        """
        On content changed event

        :param id: dialog id
        """
        if id in self.window.ui.dialog:
            self.window.ui.dialog[id].update_file_title()


