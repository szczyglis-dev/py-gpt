#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.19 01:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QLineEdit, QCheckBox, QWidget

from pygpt_net.utils import trans
from .base import BaseDialog
from ..element.labels import HelpLabel
from ..option.input import DirectoryInput


class ProfileDialog(BaseDialog):
    def __init__(self, window=None, id=None):
        """
        Profile dialog

        :param window: main window
        :param id: settings id
        """
        super(ProfileDialog, self).__init__(window, id)
        self.window = window
        self.id = id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.window.controller.settings.profile.dialog = False
        self.window.controller.settings.profile.update_menu()
        super(ProfileDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()  # close dialog when the Esc key is pressed.
        else:
            super(ProfileDialog, self).keyPressEvent(event)

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
        super(ProfileEditDialog, self).__init__(window)
        self.window = window
        self.id = id
        self.uuid = None
        self.path = None
        self.name = ""
        self.mode = "create"  # create | update
        self.input = ProfileNameInput(window, id)
        self.input.setMinimumWidth(400)

        self.window.ui.nodes['dialog.profile.item.btn.update'] = QPushButton(trans('dialog.profile.item.btn.update'))
        self.window.ui.nodes['dialog.profile.item.btn.update'].clicked.connect(
            lambda: self.window.controller.settings.profile.handle_update(
                self.mode,
                self.input.text(),
                self.workdir.text(),
                self.uuid,
            )
        )

        self.window.ui.nodes['dialog.profile.item.btn.dismiss'] = QPushButton(trans('dialog.profile.item.btn.dismiss'))
        self.window.ui.nodes['dialog.profile.item.btn.dismiss'].clicked.connect(
            lambda: self.window.controller.settings.profile.dismiss_update()
        )

        bottom = QHBoxLayout()
        bottom.addWidget(self.window.ui.nodes['dialog.profile.item.btn.dismiss'])
        bottom.addWidget(self.window.ui.nodes['dialog.profile.item.btn.update'])

        self.window.ui.nodes['dialog.profile.name.label'] = QLabel(trans("dialog.profile.name.label"))
        self.window.ui.nodes['dialog.profile.workdir.label'] = QLabel(trans("dialog.profile.workdir.label"))

        option = {
            'type': 'text',
            'label': 'Directory',
            'value': "",
        }
        self.workdir = DirectoryInput(self.window, 'profile', 'item', option)

        self.window.ui.nodes['dialog.profile.checkbox.switch'] = QCheckBox(trans("dialog.profile.checkbox.switch"))
        self.window.ui.nodes['dialog.profile.checkbox.switch'].setChecked(True)
        self.window.ui.nodes['dialog.profile.checkbox.db'] = QCheckBox(trans("dialog.profile.checkbox.include_db"))
        self.window.ui.nodes['dialog.profile.checkbox.db'].setChecked(True)
        self.window.ui.nodes['dialog.profile.checkbox.data'] = QCheckBox(trans("dialog.profile.checkbox.include_datadir"))
        self.window.ui.nodes['dialog.profile.checkbox.data'].setChecked(True)

        # checkboxes layout
        checkboxes_layout = QHBoxLayout()
        checkboxes_layout.setContentsMargins(0, 0, 0, 0)
        checkboxes_layout.addWidget(self.window.ui.nodes['dialog.profile.checkbox.db'])
        checkboxes_layout.addWidget(self.window.ui.nodes['dialog.profile.checkbox.data'])
        self.checkboxes = QWidget()
        self.checkboxes.setLayout(checkboxes_layout)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['dialog.profile.name.label'])
        layout.addWidget(self.input)
        layout.addWidget(self.window.ui.nodes['dialog.profile.workdir.label'])
        layout.addWidget(self.workdir)
        layout.addWidget(self.checkboxes)
        layout.addWidget(self.window.ui.nodes['dialog.profile.checkbox.switch'])
        layout.addLayout(bottom)

        self.setLayout(layout)

    def prepare(self):
        """Prepare dialog before show"""
        if self.mode == 'create':
            self.window.ui.nodes['dialog.profile.item.btn.update'].setText(trans('dialog.profile.item.btn.create'))
        elif self.mode == 'edit':
            self.window.ui.nodes['dialog.profile.item.btn.update'].setText(trans("dialog.profile.item.btn.update"))
        elif self.mode == 'duplicate':
            self.window.ui.nodes['dialog.profile.item.btn.update'].setText(trans("dialog.profile.item.btn.duplicate"))

        self.workdir.setText(self.path)


class ProfileNameInput(QLineEdit):
    def __init__(self, window=None, id=None):
        """
        Profile name dialog input

        :param window: main window
        :param id: info window id
        """
        super(ProfileNameInput, self).__init__(window)

        self.window = window
        self.id = id

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(ProfileNameInput, self).keyPressEvent(event)

        # save on Enter
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            self.window.controller.settings.profile.handle_update(
                self.window.ui.dialog['profile.item'].mode,
                self.window.ui.dialog['profile.item'].input.text(),
                self.window.ui.dialog['profile.item'].workdir.text(),
                self.window.ui.dialog['profile.item'].uuid,
            )
