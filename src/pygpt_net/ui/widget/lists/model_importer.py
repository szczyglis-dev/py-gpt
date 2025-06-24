#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.24 02:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLabel, QCheckBox

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc

class ModelImporter(QWidget):
    def __init__(self, window=None):
        """
        Models importer widget

        :param window: main window
        """
        super(ModelImporter, self).__init__(window)
        self.window = window
        self.id = "models.importer"
        self.layout = self.setup()
        self.window.ui.models["models.importer.available"] = self.create_model(self.window)
        self.window.ui.nodes["models.importer.available"].setModel(self.window.ui.models["models.importer.available"])
        self.window.ui.nodes["models.importer.available"].selectionModel().selectionChanged.connect(
            lambda: self.window.controller.model.importer.change_available()
        )
        self.window.ui.models["models.importer.current"] = self.create_model(self.window)
        self.window.ui.nodes["models.importer.current"].setModel(self.window.ui.models["models.importer.current"])
        self.window.ui.nodes["models.importer.current"].selectionModel().selectionChanged.connect(
            lambda: self.window.controller.model.importer.change_current()
        )
        self.setLayout(self.layout)

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        return QStandardItemModel(0, 1, parent)

    def setup(self):
        """Setup layout"""
        layout = QHBoxLayout()
        arrows_layout = QVBoxLayout()
        self.window.ui.nodes["models.importer.add"] = QPushButton(">")
        self.window.ui.nodes["models.importer.add"].clicked.connect(
            lambda: self.window.controller.model.importer.add()
        )
        self.window.ui.nodes["models.importer.remove"] = QPushButton("<")
        self.window.ui.nodes["models.importer.remove"].clicked.connect(
            lambda: self.window.controller.model.importer.remove()
        )
        self.window.ui.nodes["models.importer.add"].setEnabled(False)  # initially disabled
        self.window.ui.nodes["models.importer.remove"].setEnabled(False)  # initially disabled
        arrows_layout.addWidget(self.window.ui.nodes["models.importer.add"])
        arrows_layout.addWidget(self.window.ui.nodes["models.importer.remove"])

        self.window.ui.nodes["models.importer.available.label"] = QLabel(trans("models.importer.available.label"))
        self.window.ui.nodes["models.importer.available"] = BaseList(self.window)
        self.window.ui.nodes["models.importer.available"].clicked.disconnect()

        self.window.ui.nodes["models.importer.current.label"] = QLabel(trans("models.importer.current.label"))
        self.window.ui.nodes["models.importer.current"] = BaseList(self.window)
        self.window.ui.nodes["models.importer.current"].clicked.disconnect()

        self.window.ui.nodes["models.importer.available.all"] = QCheckBox(trans("models.importer.all"), self.window)
        self.window.ui.nodes["models.importer.available.all"].clicked.connect(
            lambda: self.window.controller.model.importer.toggle_all(
                self.window.ui.nodes["models.importer.available.all"].isChecked())
        )

        available_layout = QVBoxLayout()
        available_layout.addWidget(self.window.ui.nodes["models.importer.available.label"])
        available_layout.addWidget(self.window.ui.nodes["models.importer.available"])
        available_layout.addWidget(self.window.ui.nodes["models.importer.available.all"])

        selected_layout = QVBoxLayout()
        selected_layout.addWidget(self.window.ui.nodes["models.importer.current.label"])
        selected_layout.addWidget(self.window.ui.nodes["models.importer.current"])

        layout.addLayout(available_layout)
        layout.addLayout(arrows_layout)
        layout.addLayout(selected_layout)
        return layout

    def update_available(self, data):
        """
        Update available models

        :param data: Data to update
        """
        id = "models.importer.available"
        self.window.ui.nodes[id].backup_selection()
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = data[n].id
            if data[n].name != data[n].id:
                name += f" --> {data[n].name}"
            index = self.window.ui.models[id].index(i, 0)
            tooltip = data[n].id
            self.window.ui.models[id].setData(index, tooltip, QtCore.Qt.ToolTipRole)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1
        self.window.ui.nodes[id].restore_selection()

    def update_current(self, data):
        """
        Update current models

        :param data: Data to update
        """
        id = "models.importer.current"
        self.window.ui.nodes[id].backup_selection()
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = data[n].id
            if data[n].name != data[n].id:
                name += f" --> {data[n].name}"
            if data[n].imported:
                name = "* " + name  # mark imported models
            index = self.window.ui.models[id].index(i, 0)
            tooltip = data[n].id
            self.window.ui.models[id].setData(index, tooltip, QtCore.Qt.ToolTipRole)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1
        self.window.ui.nodes[id].restore_selection()

    def update_lists(self, available: dict, current: dict):
        """
        Update lists

        :param available: data with available models
        :param current: data with current models
        """
        self.update_available(available)
        self.update_current(current)
