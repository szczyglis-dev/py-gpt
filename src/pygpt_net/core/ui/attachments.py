#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.12.03 20:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QWidget, QHBoxLayout, QCheckBox

from ..ui.widgets import ContextSelectMenu, AttachmentSelectMenu
from ..utils import trans


class Attachments:
    def __init__(self, window=None):
        """
        Attachments UI

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """
        Setups list

        :return: QVBoxLayout
        """

        self.setup_attachments()

        # buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.window.data['attachments.btn.add'])
        buttons_layout.addWidget(self.window.data['attachments.btn.clear'])
        buttons_layout.addWidget(self.window.data['attachments.send_clear'])

        # layout
        layout = QVBoxLayout()
        layout.addLayout(buttons_layout)
        layout.addWidget(self.window.data['attachments'])

        return layout

    def setup_attachments(self):
        """
        Setup attachments list
        """
        id = 'attachments'

        # attachments
        self.window.data[id] = AttachmentSelectMenu(self.window)

        # buttons
        self.window.data['attachments.btn.add'] = QPushButton(trans('attachments.btn.add'))
        self.window.data['attachments.btn.clear'] = QPushButton(trans('attachments.btn.clear'))

        self.window.data['attachments.btn.add'].clicked.connect(
            lambda: self.window.controller.attachment.open_add())
        self.window.data['attachments.btn.clear'].clicked.connect(
            lambda: self.window.controller.attachment.clear())

        self.window.data['attachments.send_clear'] = QCheckBox(trans('attachments.send_clear'))
        self.window.data['attachments.send_clear'].setStyleSheet(
            self.window.controller.theme.get_style('checkbox'))  # Windows fix
        self.window.data['attachments.send_clear'].stateChanged.connect(
            lambda: self.window.controller.attachment.toggle_send_clear(self.window.data['attachments.send_clear'].isChecked()))

        self.window.models[id] = self.create_model(self.window)
        self.window.data[id].setModel(self.window.models[id])

    def create_model(self, parent):
        """
        Creates list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        model = QStandardItemModel(0, 2, parent)
        return model

    def update_list(self, id, data):
        """
        Updates list

        :param id: ID of the list
        :param data: Data to update
        """
        self.window.models[id].removeRows(0, self.window.models[id].rowCount())
        i = 0
        for uuid in data:
            self.window.models[id].insertRow(i)
            self.window.models[id].setData(self.window.models[id].index(i, 0), data[uuid].name)
            self.window.models[id].setData(self.window.models[id].index(i, 1), data[uuid].path)
            i += 1
