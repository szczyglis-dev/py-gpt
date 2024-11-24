#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 03:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel, Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QWidget

from pygpt_net.ui.widget.element.labels import HelpLabel, TitleLabel
from pygpt_net.ui.widget.lists.assistant import AssistantList
from pygpt_net.utils import trans
import pygpt_net.icons_rc

class Assistants:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'assistants'

    def setup(self) -> QWidget:
        """
        Setup assistants

        :return: QWidget
        """
        layout = self.setup_assistants()

        self.window.ui.nodes['assistants.widget'] = QWidget()
        self.window.ui.nodes['assistants.widget'].setLayout(layout)
        self.window.ui.nodes['assistants.widget'].setMinimumHeight(180)

        return self.window.ui.nodes['assistants.widget']

    def setup_assistants(self) -> QVBoxLayout:
        """
        Setup list of assistants

        :return: QVBoxLayout
        """
        # new
        self.window.ui.nodes['assistants.new'] = QPushButton(QIcon(":/icons/add.svg"), "")
        self.window.ui.nodes['assistants.new'].clicked.connect(
            lambda: self.window.controller.assistant.editor.edit())

        # import
        self.window.ui.nodes['assistants.import'] = QPushButton(trans('assistant.import'))
        self.window.ui.nodes['assistants.import'].clicked.connect(
            lambda: self.window.controller.assistant.batch.import_assistants()
        )

        # label
        self.window.ui.nodes['assistants.label'] = TitleLabel(trans("toolbox.assistants.label"))

        # header
        header = QHBoxLayout()
        header.addWidget(self.window.ui.nodes['assistants.label'])
        header.addStretch(1)

        header.addWidget(self.window.ui.nodes['assistants.new'], alignment=Qt.AlignRight)
        header.addWidget(self.window.ui.nodes['assistants.import'], alignment=Qt.AlignRight)
        header.setContentsMargins(5, 0, 0, 0)
        header_widget = QWidget()
        header_widget.setLayout(header)

        # list
        self.window.ui.nodes[self.id] = AssistantList(self.window, self.id)
        self.window.ui.nodes[self.id].selection_locked = self.window.controller.assistant.change_locked
        self.window.ui.nodes[self.id].setMinimumWidth(40)

        self.window.ui.nodes['tip.toolbox.assistants'] = HelpLabel(trans('tip.toolbox.assistants'), self.window)
        self.window.ui.nodes['tip.toolbox.assistants'].setAlignment(Qt.AlignCenter)

        # rows
        layout = QVBoxLayout()
        layout.addWidget(header_widget)
        layout.addWidget(self.window.ui.nodes[self.id])
        layout.addWidget(self.window.ui.nodes['tip.toolbox.assistants'])
        layout.setContentsMargins(2, 5, 5, 5)

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
        Update list of assistants

        :param data: Data to update
        """
        # store previous selection
        self.window.ui.nodes[self.id].backup_selection()

        self.window.ui.models[self.id].removeRows(0, self.window.ui.models[self.id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[self.id].insertRow(i)
            name = data[n].name
            index = self.window.ui.models[self.id].index(i, 0)
            self.window.ui.models[self.id].setData(index, "ID: " + data[n].id, QtCore.Qt.ToolTipRole)
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 0), name)
            i += 1

        # restore previous selection
        self.window.ui.nodes[self.id].restore_selection()
