#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.08 22:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel, Qt
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QCheckBox

from .widget.select import AttachmentUploadedSelectMenu
from ..utils import trans


class AttachmentsUploaded:
    def __init__(self, window=None):
        """
        Attachments Uplaoded UI

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
        buttons_layout.addWidget(self.window.data['attachments.btn.sync'])
        buttons_layout.addWidget(self.window.data['attachments.btn.clear'])

        # layout
        layout = QVBoxLayout()
        layout.addWidget(self.window.data['attachments_uploaded'])
        layout.addLayout(buttons_layout)

        return layout

    def setup_attachments(self):
        """
        Setup attachments uploaded list
        """
        id = 'attachments_uploaded'

        # attachments
        self.window.data[id] = AttachmentUploadedSelectMenu(self.window)

        # buttons
        self.window.data['attachments.btn.sync'] = QPushButton(trans('attachments.btn.sync'))
        self.window.data['attachments.btn.clear'] = QPushButton(trans('attachments.btn.clear'))

        self.window.data['attachments.btn.sync'].clicked.connect(
            lambda: self.window.controller.assistant.sync_files())
        self.window.data['attachments.btn.clear'].clicked.connect(
            lambda: self.window.controller.assistant.clear_files())

        self.window.models[id] = self.create_model(self.window)
        self.window.data[id].setModel(self.window.models[id])

    def create_model(self, parent):
        """
        Creates list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        model = QStandardItemModel(0, 2, parent)
        model.setHeaderData(0, Qt.Horizontal, trans('attachments.header.name'))
        model.setHeaderData(1, Qt.Horizontal, trans('attachments.header.path'))
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
            self.window.models[id].setData(self.window.models[id].index(i, 0), data[uuid]['name'])
            self.window.models[id].setData(self.window.models[id].index(i, 1), data[uuid]['path'])
            i += 1
