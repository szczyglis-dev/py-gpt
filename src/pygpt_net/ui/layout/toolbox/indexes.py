#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.27 22:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel, Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QCheckBox, QSizePolicy

from pygpt_net.ui.widget.element.labels import HelpLabel, TitleLabel
from pygpt_net.ui.widget.lists.index import IndexList
from pygpt_net.ui.widget.lists.index_combo import IndexCombo
from pygpt_net.ui.widget.lists.llama_mode_combo import LlamaModeCombo
from pygpt_net.utils import trans
import pygpt_net.icons_rc


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
        layout = self.setup_idx()

        self.window.ui.nodes['indexes.widget'] = QWidget()
        self.window.ui.nodes['indexes.widget'].setLayout(layout)
        self.window.ui.nodes['indexes.widget'].setMinimumHeight(150)

        return self.window.ui.nodes['indexes.widget']

    def setup_idx(self) -> QVBoxLayout:
        """
        Setup list of indexes

        :return: QVBoxLayout
        """
        # new
        self.window.ui.nodes['indexes.new'] = QPushButton(QIcon(":/icons/settings.svg"), "")
        self.window.ui.nodes['indexes.new'].clicked.connect(
            lambda: self.window.controller.settings.open_section('llama-index'))

        # label
        self.window.ui.nodes['indexes.label'] = TitleLabel(trans("toolbox.indexes.label"))

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
        #layout.addWidget(self.window.ui.nodes['tip.toolbox.indexes'])

        # model
        self.window.ui.models[self.id] = self.create_model(self.window)
        self.window.ui.nodes[self.id].setModel(self.window.ui.models[self.id])

        return layout

    def setup_options(self) -> QWidget:
        """
        Setup idx options

        :return: QWidget
        :rtype: QWidget
        """
        # idx query only
        """
        self.window.ui.config['global']['llama.idx.raw'] = QCheckBox(trans("idx.query.raw"))
        self.window.ui.config['global']['llama.idx.raw'].stateChanged.connect(
            lambda: self.window.controller.idx.common.toggle_raw(
                self.window.ui.config['global']['llama.idx.raw'].isChecked()
            )
        )
        """

        # label
        # label = QLabel(trans("toolbox.llama_index.label"))

        # add options
        # cols = QHBoxLayout()
        # cols.addWidget(self.window.ui.config['global']['llama.idx.raw'])

        # indexes combo
        option = {
            "name": "current_index",
            "label": "toolbox.llama_index.current_index",
            "keys": [],
            "value": None,
        }
        self.window.ui.nodes['indexes.select'] = IndexCombo(
            self.window,
            'global',
            'current_index',
            option,
        )
        self.window.ui.nodes['indexes.select'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # mode select combo
        option = {
            "name": "llama.idx.mode",
            "label": "toolbox.llama_index.mode",
            "keys": self.window.controller.idx.get_modes_keys(),
            "value": "chat",
        }
        self.window.ui.nodes['llama_index.mode.select'] = LlamaModeCombo(
            self.window,
            'global',
            'llama.idx.mode',
            option,
        )
        self.window.ui.nodes['indexes.select'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.window.ui.nodes['llama_index.mode.select'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # tip
        # self.window.ui.nodes['tip.toolbox.indexes'] = HelpLabel(trans('tip.toolbox.indexes'), self.window)

        # new
        self.window.ui.nodes['indexes.new'] = QPushButton(QIcon(":/icons/settings.svg"), "")
        self.window.ui.nodes['indexes.new'].clicked.connect(
            lambda: self.window.controller.settings.open_section('llama-index'))

        # labels
        self.window.ui.nodes['indexes.label'] = TitleLabel(trans("toolbox.indexes.label"))
        self.window.ui.nodes['llama_index.mode.label'] = TitleLabel(trans("toolbox.llama_index.mode.label"))

        # idx select combo
        idx_layout = QHBoxLayout()
        idx_layout.addWidget(self.window.ui.nodes['indexes.label'])
        idx_layout.addWidget(self.window.ui.nodes['indexes.select'])
        idx_layout.addWidget(self.window.ui.nodes['indexes.new'], alignment=Qt.AlignRight)
        idx_layout.setContentsMargins(0, 0, 0, 10)
        idx_widget = QWidget()
        idx_widget.setLayout(idx_layout)
        idx_widget.setMinimumHeight(55)
        idx_widget.setMinimumWidth(275)

        # mode select combo
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(self.window.ui.nodes['llama_index.mode.label'])
        mode_layout.addWidget(self.window.ui.nodes['llama_index.mode.select'])
        mode_layout.setContentsMargins(0, 0, 0, 10)
        mode_widget = QWidget()
        mode_widget.setLayout(mode_layout)
        mode_widget.setMinimumHeight(55)
        mode_widget.setMinimumWidth(275)

        # rows
        rows = QVBoxLayout()
        # rows.addWidget(label)
        rows.addWidget(idx_widget)
        rows.addWidget(mode_widget)
        # rows.addLayout(cols)  # raw option
        # rows.addWidget(self.window.ui.nodes['tip.toolbox.indexes'])

        self.window.ui.nodes['idx.options'] = QWidget()
        self.window.ui.nodes['idx.options'].setLayout(rows)
        self.window.ui.nodes['idx.options'].setContentsMargins(0, 0, 0, 0)

        return self.window.ui.nodes['idx.options']

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
        # combo box
        combo_keys = []
        combo_keys.append({  # add empty
            "-": "---"
        })
        for item in data:
            name = item['name']
            if name == "":
                name = item['id']
            combo_keys.append({
                item['id']: name
            })
        self.window.ui.nodes['indexes.select'].set_keys(combo_keys)
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
