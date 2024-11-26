#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.29 16:00:00                  #
# ================================================== #

import os

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel, Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QCheckBox, QLabel, QWidget

from pygpt_net.ui.widget.element.button import SyncButton
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.lists.uploaded import UploadedFileList
from pygpt_net.utils import trans

import pygpt_net.icons_rc

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
        empty_widget = QWidget()

        self.window.ui.nodes['attachments_uploaded.sync.tip'] = HelpLabel(trans('attachments_uploaded.sync.tip'))
        self.window.ui.nodes['attachments_uploaded.sync.tip'].setWordWrap(False)
        self.window.ui.nodes['attachments_uploaded.sync.tip'].setAlignment(Qt.AlignCenter)

        self.window.ui.nodes['tip.input.attachments.uploaded'] = HelpLabel(trans('tip.input.attachments.uploaded'),
                                                                           self.window)

        # buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.window.ui.nodes['attachments_uploaded.btn.sync'])
        buttons_layout.addWidget(self.window.ui.nodes['attachments_uploaded.btn.clear'])
        buttons_layout.addWidget(empty_widget)
        buttons_layout.addWidget(self.window.ui.nodes['attachments_uploaded.sync.tip'])
        buttons_layout.addStretch()


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
        self.window.ui.nodes['attachments_uploaded.btn.sync'] = SyncButton(trans('attachments_uploaded.btn.sync'), self.window)
        self.window.ui.nodes['attachments_uploaded.btn.clear'] = QPushButton(QIcon(":/icons/close.svg"), trans('attachments_uploaded.btn.clear'))
        self.window.ui.nodes['attachments_uploaded.btn.clear'].clicked.connect(
            lambda: self.window.controller.assistant.files.clear()
        )

        self.window.ui.models[self.id] = self.create_model(self.window)
        self.window.ui.nodes[self.id].setModel(self.window.ui.models[self.id])

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        model = QStandardItemModel(0, 4, parent)
        model.setHeaderData(0, Qt.Horizontal, trans('attachments.header.name'))
        model.setHeaderData(1, Qt.Horizontal, trans('attachments.header.path'))
        model.setHeaderData(2, Qt.Horizontal, trans('attachments.header.size'))
        model.setHeaderData(3, Qt.Horizontal, trans('attachments.header.store'))
        return model

    def update(self, data):
        """
        Update list

        :param data: Data to update
        """
        store_names = self.window.core.assistants.store.get_names()
        self.window.ui.models[self.id].removeRows(0, self.window.ui.models[self.id].rowCount())
        i = 0
        for id in data:
            item = data[id]
            size = "-"
            path = item.path

            # size
            if item.size is not None:
                size = self.window.core.filesystem.sizeof_fmt(item.size)
            else:
                if path and os.path.exists(path):
                    size = self.window.core.filesystem.sizeof_fmt(os.path.getsize(path))

            # vector stores
            if item.store_id is not None and item.store_id in store_names:
                vector_store = store_names[item.store_id]
            else:
                vector_store = trans("assistant.store.thread_only")

            self.window.ui.models[self.id].insertRow(i)
            index = self.window.ui.models[self.id].index(i, 0)
            self.window.ui.models[self.id].setData(index, "file_id: " + str(item.file_id), QtCore.Qt.ToolTipRole)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 0), item.name)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 1), path)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 2), size)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 3), vector_store)
            i += 1
