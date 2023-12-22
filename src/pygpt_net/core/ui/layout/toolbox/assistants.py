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
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSplitter, QWidget

from ...widget.lists.assistant import AssistantList
from ....utils import trans


class Assistants:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """
        Setup assistants

        :return: QSplitter
        :rtype: QSplitter
        """
        layout = self.setup_assistants('assistants', trans("toolbox.assistants.label"))

        self.window.ui.models['assistants'] = self.create_model(self.window)
        self.window.ui.nodes['assistants'].setModel(self.window.ui.models['assistants'])

        self.window.ui.nodes['assistants.widget'] = QWidget()
        self.window.ui.nodes['assistants.widget'].setLayout(layout)
        self.window.ui.nodes['assistants.widget'].setMinimumHeight(150)

        return self.window.ui.nodes['assistants.widget']

    def setup_assistants(self, id, title):
        """
        Setup list of assistants

        :param id: ID of the list
        :param title: Title of the list
        :return: QVBoxLayout
        :rtype: QVBoxLayout
        """
        # new
        self.window.ui.nodes['assistants.new'] = QPushButton(trans('assistant.new'))
        self.window.ui.nodes['assistants.new'].clicked.connect(
            lambda: self.window.controller.assistant.edit())

        # import
        self.window.ui.nodes['assistants.import'] = QPushButton(trans('assistant.import'))
        self.window.ui.nodes['assistants.import'].clicked.connect(
            lambda: self.window.controller.assistant.import_assistants())

        # label
        self.window.ui.nodes['assistants.label'] = QLabel(title)
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
        self.window.ui.nodes[id] = AssistantList(self.window, id)
        self.window.ui.nodes[id].selection_locked = self.window.controller.assistant.assistant_change_locked
        self.window.ui.nodes[id].setMinimumWidth(40)

        # rows
        layout = QVBoxLayout()
        layout.addWidget(header_widget)
        layout.addWidget(self.window.ui.nodes[id])

        # model
        self.window.ui.models[id] = self.create_model(self.window)
        self.window.ui.nodes[id].setModel(self.window.ui.models[id])

        return layout

    def create_model(self, parent):
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        :rtype: QStandardItemModel
        """
        return QStandardItemModel(0, 1, parent)

    def update(self, id, data):
        """
        Update list of assistants

        :param id: ID of the list
        :param data: Data to update
        """
        # store previous selection
        self.window.ui.nodes[id].backup_selection()

        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = data[n].name
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1

        # restore previous selection
        self.window.ui.nodes[id].restore_selection()
