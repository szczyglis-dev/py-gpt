#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.16 06:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel, Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QWidget

from pygpt_net.ui.widget.element.help import HelpLabel
from pygpt_net.ui.widget.lists.index import IndexList
from pygpt_net.utils import trans


class Indexes:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'indexes'

    def setup(self) -> QWidget:
        """
        Setup indexes

        :return: QWidget
        """
        layout = self.setup_assistants()

        self.window.ui.nodes['indexes.widget'] = QWidget()
        self.window.ui.nodes['indexes.widget'].setLayout(layout)
        self.window.ui.nodes['indexes.widget'].setMinimumHeight(150)

        return self.window.ui.nodes['indexes.widget']

    def setup_assistants(self) -> QVBoxLayout:
        """
        Setup list of indexes

        :return: QVBoxLayout
        """
        # new
        self.window.ui.nodes['indexes.new'] = QPushButton(trans('idx.new'))
        self.window.ui.nodes['indexes.new'].clicked.connect(
            lambda: self.window.controller.settings.open_section('llama-index'))

        # label
        self.window.ui.nodes['indexes.label'] = QLabel(trans("toolbox.indexes.label"))
        self.window.ui.nodes['indexes.label'].setStyleSheet(self.window.controller.theme.style('text_bold'))

        # header
        header = QHBoxLayout()
        header.addWidget(self.window.ui.nodes['indexes.label'])
        header.addStretch(1)
        header.addWidget(self.window.ui.nodes['indexes.new'], alignment=Qt.AlignRight)
        header.setContentsMargins(0, 0, 0, 0)
        header_widget = QWidget()
        header_widget.setLayout(header)

        # list
        self.window.ui.nodes[self.id] = IndexList(self.window, self.id)
        self.window.ui.nodes[self.id].selection_locked = self.window.controller.idx.change_locked
        self.window.ui.nodes[self.id].setMinimumWidth(40)

        self.window.ui.nodes['tip.toolbox.indexes'] = HelpLabel(trans('tip.toolbox.indexes'), self.window)

        # rows
        layout = QVBoxLayout()
        layout.addWidget(header_widget)
        layout.addWidget(self.window.ui.nodes[self.id])
        layout.addWidget(self.window.ui.nodes['tip.toolbox.indexes'])

        # model
        self.window.ui.models[self.id] = self.create_model(self.window)
        self.window.ui.nodes[self.id].setModel(self.window.ui.models[self.id])

        return layout

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        return QStandardItemModel(0, 1, parent)

    def update(self, data):
        """
        Update list of indexes

        :param data: Data to update
        """
        # store previous selection
        self.window.ui.nodes[self.id].backup_selection()

        self.window.ui.models[self.id].removeRows(0, self.window.ui.models[self.id].rowCount())
        i = 0
        for item in data:
            self.window.ui.models[self.id].insertRow(i)
            name = item['name']
            index = self.window.ui.models[self.id].index(i, 0)
            self.window.ui.models[self.id].setData(index, "ID: " + item['id'], QtCore.Qt.ToolTipRole)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 0), name)
            i += 1

        # restore previous selection
        self.window.ui.nodes[self.id].restore_selection()
