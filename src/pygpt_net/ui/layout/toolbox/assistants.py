#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel, Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QWidget

from pygpt_net.ui.widget.lists.assistant import AssistantList
from pygpt_net.utils import trans


class Assistants:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'assistants'

    def setup(self):
        """
        Setup assistants

        :return: QWidget
        :rtype: QWidget
        """
        layout = self.setup_assistants()

        self.window.ui.nodes['assistants.widget'] = QWidget()
        self.window.ui.nodes['assistants.widget'].setLayout(layout)
        self.window.ui.nodes['assistants.widget'].setMinimumHeight(150)

        return self.window.ui.nodes['assistants.widget']

    def setup_assistants(self):
        """
        Setup list of assistants

        :return: QVBoxLayout
        :rtype: QVBoxLayout
        """
        # new
        self.window.ui.nodes['assistants.new'] = QPushButton(trans('assistant.new'))
        self.window.ui.nodes['assistants.new'].clicked.connect(
            lambda: self.window.controller.assistant.editor.edit())

        # import
        self.window.ui.nodes['assistants.import'] = QPushButton(trans('assistant.import'))
        self.window.ui.nodes['assistants.import'].clicked.connect(
            lambda: self.window.controller.assistant.import_assistants())

        # label
        self.window.ui.nodes['assistants.label'] = QLabel(trans("toolbox.assistants.label"))
        self.window.ui.nodes['assistants.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))

        # header
        header = QHBoxLayout()
        header.addWidget(self.window.ui.nodes['assistants.label'])
        header.addWidget(self.window.ui.nodes['assistants.import'], alignment=Qt.AlignRight)
        header.addWidget(self.window.ui.nodes['assistants.new'], alignment=Qt.AlignRight)
        header.setContentsMargins(0, 0, 0, 0)
        header_widget = QWidget()
        header_widget.setLayout(header)

        # list
        self.window.ui.nodes[self.id] = AssistantList(self.window, self.id)
        self.window.ui.nodes[self.id].selection_locked = self.window.controller.assistant.change_locked
        self.window.ui.nodes[self.id].setMinimumWidth(40)

        # rows
        layout = QVBoxLayout()
        layout.addWidget(header_widget)
        layout.addWidget(self.window.ui.nodes[self.id])

        # model
        self.window.ui.models[self.id] = self.create_model(self.window)
        self.window.ui.nodes[self.id].setModel(self.window.ui.models[self.id])

        return layout

    def create_model(self, parent):
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        :rtype: QStandardItemModel
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
            self.window.ui.models[self.id].setData(self.window.ui.models[self.id].index(i, 0), name)
            i += 1

        # restore previous selection
        self.window.ui.nodes[self.id].restore_selection()
