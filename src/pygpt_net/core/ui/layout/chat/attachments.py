#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 19:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel, Qt
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QCheckBox, QWidget

from ...widget.lists.attachment import AttachmentList
from ....utils import trans


class Attachments:
    def __init__(self, window=None):
        """
        Attachments UI

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """
        Setup attachments list

        :return: QVBoxLayout
        :rtype: QVBoxLayout
        """

        self.setup_attachments()

        centered_layout = {}
        centered_widget = {}
        centered_layout['attachments.send_clear'] = QHBoxLayout()
        centered_layout['attachments.send_clear'].setContentsMargins(0, 0, 0, 0)
        centered_layout['attachments.send_clear'].setAlignment(Qt.AlignCenter)
        centered_layout['attachments.send_clear'].addWidget(self.window.ui.nodes['attachments.send_clear'])
        centered_widget['attachments.send_clear'] = QWidget()
        centered_widget['attachments.send_clear'].setLayout(centered_layout['attachments.send_clear'])

        centered_layout['attachments.capture_clear'] = QHBoxLayout()
        centered_layout['attachments.capture_clear'].setContentsMargins(0, 0, 0, 0)
        centered_layout['attachments.capture_clear'].setAlignment(Qt.AlignCenter)
        centered_layout['attachments.capture_clear'].addWidget(self.window.ui.nodes['attachments.capture_clear'])
        centered_widget['attachments.capture_clear'] = QWidget()
        centered_widget['attachments.capture_clear'].setLayout(centered_layout['attachments.capture_clear'])

        # buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.window.ui.nodes['attachments.btn.add'])
        buttons_layout.addWidget(self.window.ui.nodes['attachments.btn.clear'])
        buttons_layout.addWidget(centered_widget['attachments.send_clear'])
        buttons_layout.addWidget(centered_widget['attachments.capture_clear'])

        # layout
        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['attachments'])
        layout.addLayout(buttons_layout)

        return layout

    def setup_attachments(self):
        """
        Setup attachments list
        """
        id = 'attachments'

        # attachments
        self.window.ui.nodes[id] = AttachmentList(self.window)

        # buttons
        self.window.ui.nodes['attachments.btn.add'] = QPushButton(trans('attachments.btn.add'))
        self.window.ui.nodes['attachments.btn.clear'] = QPushButton(trans('attachments.btn.clear'))

        self.window.ui.nodes['attachments.btn.add'].clicked.connect(
            lambda: self.window.controller.attachment.open_add())
        self.window.ui.nodes['attachments.btn.clear'].clicked.connect(
            lambda: self.window.controller.attachment.clear())

        self.window.ui.nodes['attachments.send_clear'] = QCheckBox(trans('attachments.send_clear'))
        self.window.ui.nodes['attachments.send_clear'].stateChanged.connect(
            lambda: self.window.controller.attachment.toggle_send_clear(
                self.window.ui.nodes['attachments.send_clear'].isChecked()))

        self.window.ui.nodes['attachments.capture_clear'] = QCheckBox(trans('attachments.capture_clear'))
        self.window.ui.nodes['attachments.capture_clear'].stateChanged.connect(
            lambda: self.window.controller.attachment.toggle_capture_clear(
                self.window.ui.nodes['attachments.capture_clear'].isChecked()))

        self.window.ui.models[id] = self.create_model(self.window)
        self.window.ui.nodes[id].setModel(self.window.ui.models[id])

    def create_model(self, parent):
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        :rtype: QStandardItemModel
        """
        model = QStandardItemModel(0, 2, parent)
        model.setHeaderData(0, Qt.Horizontal, trans('attachments.header.name'))
        model.setHeaderData(1, Qt.Horizontal, trans('attachments.header.path'))
        return model

    def update_list(self, id, data):
        """
        Update list

        :param id: ID of the list
        :param data: Data to update
        """
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for uuid in data:
            self.window.ui.models[id].insertRow(i)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), data[uuid].name)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 1), data[uuid].path)
            i += 1
