#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.09 23:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout

from pygpt_net.ui.widget.dialog.profile import ProfileDialog, ProfileEditDialog
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.lists.profile import ProfileList
from pygpt_net.utils import trans


class Profile:
    def __init__(self, window=None):
        """
        Profile editor dialog

        :param window: Window instance
        """
        self.window = window
        self.dialog_id = "profile.editor"

    def setup(self):
        """Setup presets editor dialog"""
        self.window.ui.nodes['profile.editor.btn.new'] = \
            QPushButton(trans("dialog.profile.new"))

        self.window.ui.nodes['profile.editor.btn.new'].clicked.connect(
            lambda: self.window.controller.settings.profile.new()
        )

        # set enter key to save button
        self.window.ui.nodes['profile.editor.btn.new'].setAutoDefault(False)

        # footer buttons
        footer = QHBoxLayout()
        footer.addWidget(self.window.ui.nodes['profile.editor.btn.new'])
        # footer.addWidget(self.window.ui.nodes[profile.editor.btn.save'])

        # list
        id = 'profile.list'
        self.window.ui.nodes[id] = ProfileList(self.window, id)
        self.window.ui.models[id] = self.create_model(self.window)
        self.window.ui.nodes[id].setModel(self.window.ui.models[id])

        # get
        data = self.window.controller.settings.profile.get_profiles()

        # update list
        self.update_list(id, data)

        self.window.ui.nodes['profile.editor.tip'] = HelpLabel(trans("dialog.profile.tip"))

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.window.ui.nodes[id])
        main_layout.addWidget(self.window.ui.nodes['profile.editor.tip'])

        layout = QVBoxLayout()
        layout.addLayout(main_layout)  # list
        layout.addLayout(footer)  # bottom buttons (save, new)

        self.window.ui.dialog[self.dialog_id] = ProfileDialog(self.window, self.dialog_id)
        self.window.ui.dialog[self.dialog_id].setLayout(layout)
        self.window.ui.dialog[self.dialog_id].setWindowTitle(trans('dialog.profile.editor'))

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        return QStandardItemModel(0, 1, parent)

    def update_list(self, id: str, data: dict):
        """
        Update list

        :param id: ID of the list
        :param data: Data to update
        """
        if id not in self.window.ui.models:
            return

        current = self.window.core.config.profile.get_current()
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = data[n]['name']
            if n == current:
                name += " " + trans("profile.current.suffix")
            index = self.window.ui.models[id].index(i, 0)
            self.window.ui.models[id].setData(index, name)
            i += 1

class ProfileEdit:
    def __init__(self, window=None):
        """
        Profile edit dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup dialog"""
        id = 'profile.item'
        self.window.ui.dialog[id] = ProfileEditDialog(self.window, id)
        self.window.ui.dialog[id].setWindowTitle(trans("dialog.profile.item.editor"))