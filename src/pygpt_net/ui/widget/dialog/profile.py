#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QLineEdit, QCheckBox, QWidget

from pygpt_net.utils import trans
from .base import BaseDialog
from ..option.input import DirectoryInput


class ProfileDialog(BaseDialog):
    def __init__(self, window=None, id=None):
        """
        Profile dialog

        :param window: main window
        :param id: settings id
        """
        super().__init__(window, id)
        self.window = window
        self.id = id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.window.controller.settings.profile.dialog = False
        self.window.controller.settings.profile.update_menu()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def cleanup(self):
        """
        Cleanup on close
        """
        self.window.controller.settings.profile.dialog = False
        self.window.controller.settings.profile.update_menu()


class ProfileEditDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Profile item edit dialog

        :param window: main window
        """
        super().__init__(window)
        self.window = window
        self.id = id
        self.uuid = None
        self.path = None
        self.name = ""
        self.mode = "create"  # create | update
        self.input = ProfileNameInput(window, id)
        self.input.setParent(self)
        self.input.setMinimumWidth(400)

        nodes = self.window.ui.nodes

        self.btn_update = QPushButton(trans('dialog.profile.item.btn.update'), self)
        self.btn_update.clicked.connect(self._on_update_clicked)
        nodes['dialog.profile.item.btn.update'] = self.btn_update

        self.btn_dismiss = QPushButton(trans('dialog.profile.item.btn.dismiss'), self)
        self.btn_dismiss.clicked.connect(self._on_dismiss_clicked)
        nodes['dialog.profile.item.btn.dismiss'] = self.btn_dismiss

        bottom = QHBoxLayout()
        bottom.addWidget(nodes['dialog.profile.item.btn.dismiss'])
        bottom.addWidget(nodes['dialog.profile.item.btn.update'])

        nodes['dialog.profile.name.label'] = QLabel(trans("dialog.profile.name.label"), self)
        nodes['dialog.profile.workdir.label'] = QLabel(trans("dialog.profile.workdir.label"), self)

        option = {
            'type': 'text',
            'label': 'Directory',
            'value': "",
        }
        self.workdir = DirectoryInput(self.window, 'profile', 'item', option)
        self.workdir.setParent(self)

        nodes['dialog.profile.checkbox.switch'] = QCheckBox(trans("dialog.profile.checkbox.switch"), self)
        nodes['dialog.profile.checkbox.switch'].setChecked(True)

        self.checkboxes = QWidget(self)
        checkboxes_layout = QHBoxLayout()
        checkboxes_layout.setContentsMargins(0, 0, 0, 0)

        nodes['dialog.profile.checkbox.db'] = QCheckBox(trans("dialog.profile.checkbox.include_db"), self.checkboxes)
        nodes['dialog.profile.checkbox.db'].setChecked(True)
        nodes['dialog.profile.checkbox.data'] = QCheckBox(trans("dialog.profile.checkbox.include_datadir"), self.checkboxes)
        nodes['dialog.profile.checkbox.data'].setChecked(True)

        checkboxes_layout.addWidget(nodes['dialog.profile.checkbox.db'])
        checkboxes_layout.addWidget(nodes['dialog.profile.checkbox.data'])
        self.checkboxes.setLayout(checkboxes_layout)

        layout = QVBoxLayout()
        layout.addWidget(nodes['dialog.profile.name.label'])
        layout.addWidget(self.input)
        layout.addWidget(nodes['dialog.profile.workdir.label'])
        layout.addWidget(self.workdir)
        layout.addWidget(self.checkboxes)
        layout.addWidget(nodes['dialog.profile.checkbox.switch'])
        layout.addLayout(bottom)

        self.setLayout(layout)

    def _on_update_clicked(self):
        self.window.controller.settings.profile.handle_update(
            self.mode,
            self.input.text(),
            self.workdir.text(),
            self.uuid,
        )

    def _on_dismiss_clicked(self):
        self.window.controller.settings.profile.dismiss_update()

    def prepare(self):
        """Prepare dialog before show"""
        mapping = {
            'create': 'dialog.profile.item.btn.create',
            'edit': 'dialog.profile.item.btn.update',
            'duplicate': 'dialog.profile.item.btn.duplicate',
        }
        key = mapping.get(self.mode)
        if key:
            self.window.ui.nodes['dialog.profile.item.btn.update'].setText(trans(key))
        self.workdir.setText(self.path)


class ProfileNameInput(QLineEdit):
    def __init__(self, window=None, id=None):
        """
        Profile name dialog input

        :param window: main window
        :param id: info window id
        """
        super().__init__(window)
        self.window = window
        self.id = id

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super().keyPressEvent(event)
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.window.controller.settings.profile.handle_update(
                self.window.ui.dialog['profile.item'].mode,
                self.window.ui.dialog['profile.item'].input.text(),
                self.window.ui.dialog['profile.item'].workdir.text(),
                self.window.ui.dialog['profile.item'].uuid,
            )