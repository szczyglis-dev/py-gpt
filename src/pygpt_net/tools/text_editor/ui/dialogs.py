#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.26 15:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout

from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.ui.widget.dialog.editor_file import EditorFileDialog
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans

from .widgets import TextFileEditor

class DialogSpawner:
    def __init__(self, window=None):
        """
        Editor dialog spawner

        :param window: Window instance
        """
        self.window = window

    def setup(self, id: str = None) -> BaseDialog:
        """
        Setup file editor dialog instance

        :param id: editor id
        :return: BaseDialog instance
        """
        self.window.ui.editor[id] = TextFileEditor(self.window)
        self.window.ui.editor[id].setReadOnly(False)
        self.window.ui.editor[id].setProperty('class', 'code-editor')
        self.window.ui.editor[id].textChanged.connect(
            lambda: self.on_changed(id)
        )

        self.window.ui.nodes['editor.custom.btn.restore'] = QPushButton(trans("action.restore"))
        self.window.ui.nodes['editor.custom.btn.save'] = QPushButton(trans("dialog.editor.btn.save"))
        self.window.ui.nodes['editor.custom.btn.restore'].clicked.connect(
            lambda: self.window.tools.get("editor").restore(id)
        )
        self.window.ui.nodes['editor.custom.btn.save'].clicked.connect(
            lambda: self.window.tools.get("editor").save(id)
        )

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['editor.custom.btn.restore'])
        bottom_layout.addWidget(self.window.ui.nodes['editor.custom.btn.save'])

        self.window.ui.paths[id] = HelpLabel("")
        self.window.ui.paths[id].setWordWrap(False)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.editor[id])
        layout.addWidget(self.window.ui.paths[id])
        layout.addLayout(bottom_layout)

        dialog = EditorFileDialog(self.window)
        dialog.disable_geometry_store = True  # disable geometry store
        dialog.id = id
        dialog.append_layout(layout)
        dialog.setWindowTitle("Text editor")

        return dialog

    def on_changed(self, id: str):
        """
        On content changed event

        :param id: dialog id
        """
        if id in self.window.ui.dialog:
            self.window.ui.dialog[id].update_file_title()