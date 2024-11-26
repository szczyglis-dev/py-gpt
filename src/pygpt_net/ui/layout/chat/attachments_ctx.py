#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.26 02:00:00                  #
# ================================================== #

import os

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel, Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QPushButton, QHBoxLayout, QWidget, QRadioButton

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.lists.attachment_ctx import AttachmentCtxList
from pygpt_net.utils import trans

import pygpt_net.icons_rc

class AttachmentsCtx:
    def __init__(self, window=None):
        """
        Attachments for CTX UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'attachments_ctx'

    def setup(self) -> QVBoxLayout:
        """
        Setup list

        :return: QVBoxLayout
        """
        self.setup_attachments()
        empty_widget = QWidget()

        self.window.ui.nodes['tip.input.attachments.ctx'] = HelpLabel(trans('tip.input.attachments.ctx'),
                                                                           self.window)

        self.window.ui.nodes['input.attachments.ctx.mode.label'] = HelpLabel(trans("attachments.ctx.label"))
        self.window.ui.nodes['input.attachments.ctx.mode.full'] = QRadioButton(trans("attachments.ctx.mode.full"))
        self.window.ui.nodes['input.attachments.ctx.mode.full'].clicked.connect(
            lambda: self.window.controller.chat.attachment.switch_mode(
                self.window.controller.chat.attachment.MODE_FULL_CONTEXT
            ))
        self.window.ui.nodes['input.attachments.ctx.mode.query'] = QRadioButton(trans("attachments.ctx.mode.query"))
        self.window.ui.nodes['input.attachments.ctx.mode.query'].clicked.connect(
            lambda: self.window.controller.chat.attachment.switch_mode(
                self.window.controller.chat.attachment.MODE_QUERY_CONTEXT
            ))
        self.window.ui.nodes['input.attachments.ctx.mode.query_summary'] = QRadioButton(trans("attachments.ctx.mode.summary"))
        self.window.ui.nodes['input.attachments.ctx.mode.query_summary'].clicked.connect(
            lambda: self.window.controller.chat.attachment.switch_mode(
                self.window.controller.chat.attachment.MODE_QUERY_CONTEXT_SUMMARY
            ))
        self.window.ui.nodes['input.attachments.ctx.mode.off'] = QRadioButton(trans("attachments.ctx.mode.off"))
        self.window.ui.nodes['input.attachments.ctx.mode.off'].clicked.connect(
            lambda: self.window.controller.chat.attachment.switch_mode(
                self.window.controller.chat.attachment.MODE_DISABLED
            ))

        # buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.window.ui.nodes['attachments_ctx.btn.clear'])
        buttons_layout.addWidget(empty_widget)
        # buttons_layout.addStretch()
        buttons_layout.addWidget(self.window.ui.nodes['input.attachments.ctx.mode.label'])
        buttons_layout.addWidget(self.window.ui.nodes['input.attachments.ctx.mode.full'])
        buttons_layout.addWidget(self.window.ui.nodes['input.attachments.ctx.mode.query'])
        buttons_layout.addWidget(self.window.ui.nodes['input.attachments.ctx.mode.query_summary'])
        buttons_layout.addWidget(self.window.ui.nodes['input.attachments.ctx.mode.off'])
        buttons_layout.addStretch()

        # layout
        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['tip.input.attachments.ctx'])
        layout.addWidget(self.window.ui.nodes['attachments_ctx'])
        layout.addLayout(buttons_layout)

        return layout

    def setup_attachments(self):
        """Setup attachments uploaded list"""
        # attachments
        self.window.ui.nodes[self.id] = AttachmentCtxList(self.window)

        # buttons
        self.window.ui.nodes['attachments_ctx.btn.clear'] = QPushButton(QIcon(":/icons/close.svg"), trans('attachments_uploaded.btn.clear'))
        self.window.ui.nodes['attachments_ctx.btn.clear'].clicked.connect(
            lambda: self.window.controller.chat.attachment.clear()
        )

        self.window.ui.models[self.id] = self.create_model(self.window)
        self.window.ui.nodes[self.id].setModel(self.window.ui.models[self.id])

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        model = QStandardItemModel(0, 5, parent)
        model.setHeaderData(0, Qt.Horizontal, trans('attachments.header.name'))
        model.setHeaderData(1, Qt.Horizontal, trans('attachments.header.path'))
        model.setHeaderData(2, Qt.Horizontal, trans('attachments.header.size'))
        model.setHeaderData(3, Qt.Horizontal, trans('attachments.header.length'))
        model.setHeaderData(4, Qt.Horizontal, trans('attachments.header.idx'))
        return model

    def update(self, data):
        """
        Update list

        :param data: Data to update
        """
        self.window.ui.models[self.id].removeRows(0, self.window.ui.models[self.id].rowCount())
        i = 0
        for item in data:
            indexed = False
            name = "No name"
            if 'name' in item:
                name = item['name']
            size = "-"
            path = "No path"
            if 'path' in item:
                path = item['path']
            uuid = ""
            if 'uuid' in item:
                uuid = item['uuid']
            length = "-"
            if 'length' in item:
                length = str(item['length'])
            if 'tokens' in item:
                length += ' / ~' + str(item['tokens'])
            if 'indexed' in item and item['indexed']:
                indexed = True

            idx_str = ""
            if indexed:
                idx_str = trans("attachments.ctx.indexed")

            if os.path.exists(path):
                size = self.window.core.filesystem.sizeof_fmt(os.path.getsize(path))
            elif 'size' in item:
                size = self.window.core.filesystem.sizeof_fmt(item['size'])

            self.window.ui.models[self.id].insertRow(i)
            index = self.window.ui.models[self.id].index(i, 0)
            self.window.ui.models[self.id].setData(index, "uuid: " + str(uuid), QtCore.Qt.ToolTipRole)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 0), name)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 1), path)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 2), size)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 3), length)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 4), idx_str)
            i += 1
