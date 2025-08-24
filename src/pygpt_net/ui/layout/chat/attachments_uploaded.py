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

import os

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel, Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QWidget

from pygpt_net.ui.widget.element.button import SyncButton
from pygpt_net.ui.widget.element.labels import HelpLabel
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
        empty_widget = QWidget(self.window)

        self.window.ui.nodes['attachments_uploaded.sync.tip'] = HelpLabel(trans('attachments_uploaded.sync.tip'), self.window)
        self.window.ui.nodes['attachments_uploaded.sync.tip'].setWordWrap(False)
        self.window.ui.nodes['attachments_uploaded.sync.tip'].setAlignment(Qt.AlignCenter)

        self.window.ui.nodes['tip.input.attachments.uploaded'] = HelpLabel(trans('tip.input.attachments.uploaded'),
                                                                           self.window)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.window.ui.nodes['attachments_uploaded.btn.sync'])
        buttons_layout.addWidget(self.window.ui.nodes['attachments_uploaded.btn.clear'])
        buttons_layout.addWidget(empty_widget)
        buttons_layout.addWidget(self.window.ui.nodes['attachments_uploaded.sync.tip'])
        buttons_layout.addStretch()

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['tip.input.attachments.uploaded'])
        layout.addWidget(self.window.ui.nodes['attachments_uploaded'])
        layout.addLayout(buttons_layout)

        return layout

    def setup_attachments(self):
        """
        Setup attachments uploaded list
        """
        self.window.ui.nodes[self.id] = UploadedFileList(self.window)

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
        model = self.window.ui.models[self.id]
        store_names = self.window.core.assistants.store.get_names()
        thread_only_label = trans("assistant.store.thread_only")
        fs = self.window.core.filesystem

        model.beginResetModel()
        model.setRowCount(0)
        count = len(data)
        if count:
            model.setRowCount(count)
            for i, item in enumerate(data.values()):
                path = item.path
                if item.size is not None:
                    size_str = fs.sizeof_fmt(item.size)
                else:
                    size_str = "-"
                    if path:
                        try:
                            st = os.stat(path)
                        except OSError:
                            pass
                        else:
                            size_str = fs.sizeof_fmt(st.st_size)

                store_name = store_names.get(item.store_id, thread_only_label)

                idx0 = model.index(i, 0)
                model.setData(idx0, item.name)
                model.setData(idx0, f"file_id: {item.file_id}", QtCore.Qt.ToolTipRole)
                model.setData(model.index(i, 1), path)
                model.setData(model.index(i, 2), size_str)
                model.setData(model.index(i, 3), store_name)
        model.endResetModel()