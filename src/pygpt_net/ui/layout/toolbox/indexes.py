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

from PySide6.QtGui import QStandardItemModel, Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QCheckBox, QSizePolicy

from pygpt_net.ui.widget.element.labels import HelpLabel, TitleLabel
from pygpt_net.ui.widget.lists.index import IndexList
from pygpt_net.ui.widget.lists.index_combo import IndexCombo
from pygpt_net.ui.widget.lists.llama_mode_combo import LlamaModeCombo
from pygpt_net.utils import trans


class Indexes:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.id = 'indexes'
        self._settings_icon = QIcon(":/icons/settings.svg")
        self._last_combo_signature = None

    def setup(self) -> QWidget:
        """
        Setup indexes

        :return: QWidget
        """
        layout = self.setup_idx()
        nodes = self.window.ui.nodes

        nodes['indexes.widget'] = QWidget()
        nodes['indexes.widget'].setLayout(layout)
        nodes['indexes.widget'].setMinimumHeight(150)

        return nodes['indexes.widget']

    def setup_idx(self) -> QVBoxLayout:
        """
        Setup list of indexes

        :return: QVBoxLayout
        """
        nodes = self.window.ui.nodes
        nodes['indexes.new'] = QPushButton(self._settings_icon, "")
        nodes['indexes.new'].clicked.connect(self._open_llama_index_settings)

        nodes['indexes.label'] = TitleLabel(trans("toolbox.indexes.label"))

        header = QHBoxLayout()
        header.addWidget(nodes['indexes.label'])
        header.addStretch(1)
        header.addWidget(nodes['indexes.new'], alignment=Qt.AlignRight)
        header.setContentsMargins(5, 0, 0, 0)

        nodes[self.id] = IndexList(self.window, self.id)
        nodes[self.id].selection_locked = self.window.controller.idx.change_locked
        nodes[self.id].setMinimumWidth(40)

        nodes['tip.toolbox.indexes'] = HelpLabel(trans('tip.toolbox.indexes'), self.window)

        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(self.window.ui.nodes[self.id])
        layout.setContentsMargins(2, 5, 5, 5)

        self.window.ui.models[self.id] = self.create_model(self.window)
        nodes[self.id].setModel(self.window.ui.models[self.id])

        return layout

    def setup_options(self) -> QWidget:
        """
        Setup idx options

        :return: QWidget
        :rtype: QWidget
        """
        nodes = self.window.ui.nodes
        option = {
            "name": "current_index",
            "label": "toolbox.llama_index.current_index",
            "keys": [],
            "value": None,
        }
        nodes['indexes.select'] = IndexCombo(
            self.window,
            'global',
            'current_index',
            option,
        )
        nodes['indexes.select'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        option = {
            "name": "llama.idx.mode",
            "label": "toolbox.llama_index.mode",
            "keys": self.window.controller.idx.get_modes_keys(),
            "value": "chat",
        }
        nodes['llama_index.mode.select'] = LlamaModeCombo(
            self.window,
            'global',
            'llama.idx.mode',
            option,
        )
        nodes['llama_index.mode.select'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        nodes['indexes.new'] = QPushButton(self._settings_icon, "")
        nodes['indexes.new'].clicked.connect(self._open_llama_index_settings)

        nodes['indexes.label'] = TitleLabel(trans("toolbox.indexes.label"))
        nodes['llama_index.mode.label'] = TitleLabel(trans("toolbox.llama_index.mode.label"))

        idx_layout = QHBoxLayout()
        idx_layout.addWidget(nodes['indexes.label'])
        idx_layout.addWidget(nodes['indexes.select'])
        idx_layout.addWidget(nodes['indexes.new'], alignment=Qt.AlignRight)
        idx_layout.setContentsMargins(0, 0, 0, 10)
        idx_widget = QWidget()
        idx_widget.setLayout(idx_layout)
        idx_widget.setMinimumHeight(55)
        idx_widget.setMinimumWidth(275)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(nodes['llama_index.mode.label'])
        mode_layout.addWidget(nodes['llama_index.mode.select'])
        mode_layout.setContentsMargins(0, 0, 0, 10)
        mode_widget = QWidget()
        mode_widget.setLayout(mode_layout)
        mode_widget.setMinimumHeight(55)
        mode_widget.setMinimumWidth(275)

        rows = QVBoxLayout()
        rows.addWidget(idx_widget)
        rows.addWidget(mode_widget)

        nodes['idx.options'] = QWidget()
        nodes['idx.options'].setLayout(rows)
        nodes['idx.options'].setContentsMargins(0, 0, 0, 0)

        return nodes['idx.options']

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
        combo_keys = [{"-": "---"}] + [{item['id']: (item['name'] or item['id'])} for item in data]
        signature = tuple((item['id'], (item['name'] or item['id'])) for item in data)
        if self._last_combo_signature != signature:
            self.window.ui.nodes['indexes.select'].set_keys(combo_keys)
            self._last_combo_signature = signature
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
        """

    def _open_llama_index_settings(self):
        self.window.controller.settings.open_section('llama-index')