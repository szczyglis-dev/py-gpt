#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.01 17:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLabel

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc

class ExpertsEditor(QWidget):
    def __init__(self, window=None):
        """
        Experts select menu

        :param window: main window
        """
        super(ExpertsEditor, self).__init__(window)
        self.window = window
        self.id = "preset.experts"
        self.layout = self.setup()
        self.window.ui.models["preset.experts.available"] = self.create_model(self.window)
        self.window.ui.nodes["preset.experts.available"].setModel(self.window.ui.models["preset.experts.available"])
        self.window.ui.nodes["preset.experts.available"].selectionModel().selectionChanged.connect(
            lambda: self.window.controller.presets.editor.experts.change_available()
        )
        self.window.ui.models["preset.experts.selected"] = self.create_model(self.window)
        self.window.ui.nodes["preset.experts.selected"].setModel(self.window.ui.models["preset.experts.selected"])
        self.window.ui.nodes["preset.experts.selected"].selectionModel().selectionChanged.connect(
            lambda: self.window.controller.presets.editor.experts.change_selected()
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
        self.window.ui.nodes["preset.experts.add"] = QPushButton(">")
        self.window.ui.nodes["preset.experts.add"].clicked.connect(
            lambda: self.window.controller.presets.editor.experts.add_expert()
        )
        self.window.ui.nodes["preset.experts.remove"] = QPushButton("<")
        self.window.ui.nodes["preset.experts.remove"].clicked.connect(
            lambda: self.window.controller.presets.editor.experts.remove_expert()
        )
        arrows_layout.addWidget(self.window.ui.nodes["preset.experts.add"])
        arrows_layout.addWidget(self.window.ui.nodes["preset.experts.remove"])

        self.window.ui.nodes["preset.experts.available.label"] = QLabel(trans("preset.experts.available.label"))
        self.window.ui.nodes["preset.experts.available"] = BaseList(self.window)
        self.window.ui.nodes["preset.experts.available"].clicked.disconnect()

        self.window.ui.nodes["preset.experts.selected.label"] = QLabel(trans("preset.experts.selected.label"))
        self.window.ui.nodes["preset.experts.selected"] = BaseList(self.window)
        self.window.ui.nodes["preset.experts.selected"].clicked.disconnect()

        available_layout = QVBoxLayout()
        available_layout.addWidget(self.window.ui.nodes["preset.experts.available.label"])
        available_layout.addWidget(self.window.ui.nodes["preset.experts.available"])

        selected_layout = QVBoxLayout()
        selected_layout.addWidget(self.window.ui.nodes["preset.experts.selected.label"])
        selected_layout.addWidget(self.window.ui.nodes["preset.experts.selected"])

        layout.addLayout(available_layout)
        layout.addLayout(arrows_layout)
        layout.addLayout(selected_layout)
        return layout

    def update_available(self, data):
        """
        Update available experts

        :param data: Data to update
        """
        id = "preset.experts.available"
        self.window.ui.nodes[id].backup_selection()
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = data[n].name + "  [" + data[n].filename + "]"
            index = self.window.ui.models[id].index(i, 0)
            tooltip = data[n].model + ", " + n
            self.window.ui.models[id].setData(index, tooltip, QtCore.Qt.ToolTipRole)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1
        self.window.ui.nodes[id].restore_selection()

    def update_selected(self, data):
        """
        Update selected experts

        :param data: Data to update
        """
        id = "preset.experts.selected"
        self.window.ui.nodes[id].backup_selection()
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = data[n].name + "  [" + data[n].filename + "]"
            index = self.window.ui.models[id].index(i, 0)
            tooltip = data[n].model + ", " + n
            self.window.ui.models[id].setData(index, tooltip, QtCore.Qt.ToolTipRole)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1
        self.window.ui.nodes[id].restore_selection()

    def update_lists(self, available: dict, selected: dict):
        """
        Update lists

        :param available: data with available experts
        :param selected: data with selected experts
        """
        self.update_available(available)
        self.update_selected(selected)
