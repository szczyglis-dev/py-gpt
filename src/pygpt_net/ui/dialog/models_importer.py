#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.24 02:00:00                  #
# ================================================== #
from PySide6 import QtCore
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout, QLabel

from pygpt_net.ui.widget.lists.model_importer import ModelImporter
from pygpt_net.ui.widget.dialog.model_importer import ModelImporterOllamaDialog
from pygpt_net.utils import trans


class ModelsImporter:
    def __init__(self, window=None):
        """
        Models importer dialog

        :param window: Window instance
        """
        self.window = window
        self.dialog_id = "models.importer"

    def setup(self, idx=None):
        """
        Setup dialog

        :param idx: current model tab index
        """
        # models
        self.window.ui.nodes['models.importer.editor'] = ModelImporter(self.window)

        self.window.ui.nodes['models.importer.btn.refresh'] = \
            QPushButton(trans("dialog.models.importer.btn.refresh"))
        self.window.ui.nodes['models.importer.btn.cancel'] = \
            QPushButton(trans("dialog.models.importer.btn.cancel"))
        self.window.ui.nodes['models.importer.btn.save'] = \
            QPushButton(trans("dialog.models.importer.btn.save"))

        self.window.ui.nodes['models.importer.btn.refresh'].clicked.connect(
            lambda: self.window.controller.model.importer.refresh(reload=True))
        self.window.ui.nodes['models.importer.btn.cancel'].clicked.connect(
            lambda: self.window.controller.model.importer.cancel())
        self.window.ui.nodes['models.importer.btn.save'].clicked.connect(
            lambda: self.window.controller.model.importer.save())

        # set enter key to save button
        self.window.ui.nodes['models.importer.btn.refresh'].setAutoDefault(False)
        self.window.ui.nodes['models.importer.btn.cancel'].setAutoDefault(False)
        self.window.ui.nodes['models.importer.btn.save'].setAutoDefault(True)

        # footer buttons
        footer = QHBoxLayout()
        footer.addWidget(self.window.ui.nodes['models.importer.btn.refresh'])
        footer.addWidget(self.window.ui.nodes['models.importer.btn.cancel'])
        footer.addWidget(self.window.ui.nodes['models.importer.btn.save'])

        self.window.ui.nodes["models.importer.url"] = QLabel("S")
        self.window.ui.nodes["models.importer.url"].setAlignment(QtCore.Qt.AlignRight)
        self.window.ui.nodes["models.importer.url"].setContentsMargins(10, 10, 10, 10)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.window.ui.nodes["models.importer.url"])
        main_layout.addWidget(self.window.ui.nodes['models.importer.editor'])

        self.window.ui.nodes["models.importer.status"] = QLabel("S")
        self.window.ui.nodes["models.importer.status"].setAlignment(QtCore.Qt.AlignCenter)
        self.window.ui.nodes["models.importer.status"].setContentsMargins(10, 10, 10, 10)

        layout = QVBoxLayout()
        layout.addLayout(main_layout)  # list
        layout.addWidget(self.window.ui.nodes["models.importer.status"])
        layout.addLayout(footer)  # bottom buttons (save, defaults)

        self.window.ui.dialog[self.dialog_id] = ModelImporterOllamaDialog(self.window, self.dialog_id)
        self.window.ui.dialog[self.dialog_id].setLayout(layout)
        self.window.ui.dialog[self.dialog_id].setWindowTitle(trans('dialog.models.importer'))