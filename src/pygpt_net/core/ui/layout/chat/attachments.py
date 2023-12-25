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

from pygpt_net.core.ui.widget.lists.attachment import AttachmentList
from pygpt_net.core.utils import trans


class Attachments:
    def __init__(self, window=None):
        """
        Attachments UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'attachments'

    def setup(self):
        """
        Setup attachments list

        :return: QVBoxLayout
        :rtype: QVBoxLayout
        """
        self.setup_attachments()
        self.setup_buttons()

        # buttons layout
        buttons = QHBoxLayout()
        buttons.addWidget(self.window.ui.nodes['attachments.btn.add'])
        buttons.addWidget(self.window.ui.nodes['attachments.btn.clear'])
        buttons.addWidget(self.setup_send_clear())
        buttons.addWidget(self.setup_capture_clear())

        # layout
        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['attachments'])
        layout.addLayout(buttons)

        return layout

    def setup_send_clear(self):
        """
        Setup send clear checkbox

        :return: QWidget
        :rtype: QWidget
        """
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.window.ui.nodes['attachments.send_clear'])

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def setup_capture_clear(self):
        """
        Setup after capture clear checkbox

        :return: QWidget
        :rtype: QWidget
        """
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.window.ui.nodes['attachments.capture_clear'])

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def setup_buttons(self):
        """
        Setup buttons
        """
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

    def setup_attachments(self):
        """
        Setup attachments list
        """
        self.window.ui.nodes[self.id] = AttachmentList(self.window)
        self.window.ui.models[self.id] = self.create_model(self.window)
        self.window.ui.nodes[self.id].setModel(self.window.ui.models[self.id])

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

    def update(self, data):
        """
        Update list

        :param data: Data to update
        """
        self.window.ui.models[self.id].removeRows(0, self.window.ui.models[self.id].rowCount())
        i = 0
        for id in data:
            self.window.ui.models[self.id].insertRow(i)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 0), data[id].name)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 1), data[id].path)
            i += 1
