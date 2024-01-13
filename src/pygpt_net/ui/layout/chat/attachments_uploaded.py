#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.29 21:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel, Qt
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QCheckBox, QLabel, QWidget

from pygpt_net.ui.widget.element.help import HelpLabel
from pygpt_net.ui.widget.lists.uploaded import UploadedFileList
from pygpt_net.utils import trans


class AttachmentsUploaded:
    def __init__(self, window=None):
        """
        Attachments Uploaded UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'attachments_uploaded'

    def setup(self) -> QVBoxLayout:
        """
        Setup list

        :return: QVBoxLayout
        """
        self.setup_attachments()

        self.window.ui.nodes['attachments_uploaded.sync.tip'] = QLabel(trans('attachments_uploaded.sync.tip'))
        self.window.ui.nodes['attachments_uploaded.sync.tip'].setAlignment(Qt.AlignCenter)
        empty_widget = QWidget()

        self.window.ui.nodes['tip.input.attachments.uploaded'] = HelpLabel(trans('tip.input.attachments.uploaded'),
                                                                           self.window)

        # buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.window.ui.nodes['attachments_uploaded.btn.sync'])
        buttons_layout.addWidget(self.window.ui.nodes['attachments_uploaded.btn.clear'])
        buttons_layout.addWidget(empty_widget)
        buttons_layout.addWidget(self.window.ui.nodes['attachments_uploaded.sync.tip'])

        # layout
        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['tip.input.attachments.uploaded'])
        layout.addWidget(self.window.ui.nodes['attachments_uploaded'])
        layout.addLayout(buttons_layout)

        return layout

    def setup_attachments(self):
        """
        Setup attachments uploaded list
        """
        # attachments
        self.window.ui.nodes[self.id] = UploadedFileList(self.window)

        # buttons
        self.window.ui.nodes['attachments_uploaded.btn.sync'] = QPushButton(trans('attachments_uploaded.btn.sync'))
        self.window.ui.nodes['attachments_uploaded.btn.clear'] = QPushButton(trans('attachments_uploaded.btn.clear'))

        self.window.ui.nodes['attachments_uploaded.btn.sync'].clicked.connect(
            lambda: self.window.controller.assistant.files.sync())
        self.window.ui.nodes['attachments_uploaded.btn.clear'].clicked.connect(
            lambda: self.window.controller.assistant.files.clear_files())

        self.window.ui.models[self.id] = self.create_model(self.window)
        self.window.ui.nodes[self.id].setModel(self.window.ui.models[self.id])

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        model = QStandardItemModel(0, 2, parent)
        model.setHeaderData(0, Qt.Horizontal, trans('attachments.header.name'))
        model.setHeaderData(1, Qt.Horizontal, trans('attachments.header.path'))
        return model

    def update(self, data):
        """
        Update list

        :param data: Data to update
        """
        self.window.ui.models[self.id].removeRows(0, self.window.ui.models[self.id].rowCount())
        i = 0
        for id in data:
            if 'name' not in data[id] or 'path' not in data[id]:
                continue
            self.window.ui.models[self.id].insertRow(i)
            index = self.window.ui.models[self.id].index(i, 0)
            self.window.ui.models[self.id].setData(index, "ID: " + id, QtCore.Qt.ToolTipRole)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 0), data[id]['name'])
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 1), data[id]['path'])
            i += 1
