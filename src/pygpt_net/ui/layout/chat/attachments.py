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
from functools import partial

from PySide6.QtGui import QStandardItemModel, QIcon
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QCheckBox, QWidget

from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.lists.attachment import AttachmentList
from pygpt_net.utils import trans

class Attachments:
    def __init__(self, window=None):
        """
        Attachments UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'attachments'

    def setup(self) -> QVBoxLayout:
        """
        Setup attachments list

        :return: QVBoxLayout
        """
        self.setup_attachments()
        self.setup_buttons()

        empty_widget = QWidget(self.window)
        self.window.ui.nodes['input.attachments.options.label'] = HelpLabel(trans("attachments.options.label"), self.window)

        buttons = QHBoxLayout()
        nodes = self.window.ui.nodes
        buttons.addWidget(nodes['attachments.btn.add'])
        buttons.addWidget(nodes['attachments.btn.add_url'])
        buttons.addWidget(nodes['attachments.btn.clear'])
        buttons.addWidget(empty_widget)
        buttons.addWidget(nodes['input.attachments.options.label'])
        buttons.addWidget(self.setup_auto_index())
        buttons.addWidget(self.setup_send_clear())
        buttons.addWidget(self.setup_capture_clear())
        buttons.addStretch()

        self.window.ui.nodes['tip.input.attachments'] = HelpLabel(trans('tip.input.attachments'), self.window)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['tip.input.attachments'])
        layout.addWidget(self.window.ui.nodes['attachments'])
        layout.addLayout(buttons)

        return layout

    def _centered_container(self, child: QWidget) -> QWidget:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(child)
        widget = QWidget(self.window)
        widget.setLayout(layout)
        return widget

    def setup_send_clear(self) -> QWidget:
        """
        Setup send clear checkbox

        :return: QWidget
        """
        return self._centered_container(self.window.ui.nodes['attachments.send_clear'])

    def setup_capture_clear(self) -> QWidget:
        """
        Setup after capture clear checkbox

        :return: QWidget
        """
        return self._centered_container(self.window.ui.nodes['attachments.capture_clear'])

    def setup_auto_index(self) -> QWidget:
        """
        Setup auto index checkbox

        :return: QWidget
        """
        return self._centered_container(self.window.ui.nodes['attachments.auto_index'])

    def setup_buttons(self):
        """
        Setup buttons
        """
        nodes = self.window.ui.nodes
        ctrl = self.window.controller.attachment

        icon_add = QIcon(":/icons/add.svg")
        icon_close = QIcon(":/icons/close.svg")

        nodes['attachments.btn.add'] = QPushButton(icon_add, trans('attachments.btn.add'), self.window)
        nodes['attachments.btn.add_url'] = QPushButton(icon_add, trans('attachments.btn.add_url'), self.window)
        nodes['attachments.btn.clear'] = QPushButton(icon_close, trans('attachments.btn.clear'), self.window)

        nodes['attachments.btn.add'].clicked.connect(ctrl.open_add)
        nodes['attachments.btn.add_url'].clicked.connect(ctrl.open_add_url)
        nodes['attachments.btn.clear'].clicked.connect(partial(ctrl.clear, remove_local=True))

        nodes['attachments.send_clear'] = QCheckBox(trans('attachments.send_clear'), self.window)
        nodes['attachments.send_clear'].toggled.connect(ctrl.toggle_send_clear)

        nodes['attachments.capture_clear'] = QCheckBox(trans('attachments.capture_clear'), self.window)
        nodes['attachments.capture_clear'].toggled.connect(ctrl.toggle_capture_clear)

        nodes['attachments.auto_index'] = QCheckBox(trans('attachments.auto_index'), self.window)
        nodes['attachments.auto_index'].toggled.connect(ctrl.toggle_auto_index)

    def setup_attachments(self):
        """
        Setup attachments list
        """
        self.window.ui.nodes[self.id] = AttachmentList(self.window)
        self.window.ui.models[self.id] = self.create_model(self.window)
        self.window.ui.nodes[self.id].setModel(self.window.ui.models[self.id])

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        model = QStandardItemModel(0, 4, parent)
        model.setHorizontalHeaderLabels([
            trans('attachments.header.name'),
            trans('attachments.header.path'),
            trans('attachments.header.size'),
            trans('attachments.header.ctx'),
        ])
        return model

    def update(self, data):
        """
        Update list

        :param data: Data to update
        """
        model = self.window.ui.models[self.id]
        rows = len(data)
        model.setRowCount(rows)

        exists = os.path.exists
        getsize = os.path.getsize
        sizeof_fmt = self.window.core.filesystem.sizeof_fmt

        model.beginResetModel()
        for i, (_, item) in enumerate(data.items()):
            path = item.path
            if item.type == AttachmentItem.TYPE_FILE and path and exists(path):
                size = sizeof_fmt(getsize(path))
            else:
                size = ""
            ctx_str = "YES" if item.ctx else ""

            model.setData(model.index(i, 0), item.name)
            model.setData(model.index(i, 1), path)
            model.setData(model.index(i, 2), size)
            model.setData(model.index(i, 3), ctx_str)
        model.endResetModel()

        if rows:
            model.dataChanged.emit(model.index(0, 0), model.index(rows - 1, 3), [])