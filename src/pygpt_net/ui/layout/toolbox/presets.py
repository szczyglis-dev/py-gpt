#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 03:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel, Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QSplitter, QWidget, QSizePolicy

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_EXPERT,
)
from pygpt_net.ui.widget.element.labels import HelpLabel, TitleLabel
from pygpt_net.ui.widget.lists.preset import PresetList
from pygpt_net.ui.layout.toolbox.footer import Footer
from pygpt_net.utils import trans
import pygpt_net.icons_rc

class Presets:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.footer = Footer(window)
        self.id = 'preset.presets'

    def setup(self) -> QSplitter:
        """
        Setup presets

        :return: QSplitter
        """
        presets = self.setup_presets()

        self.window.ui.nodes['presets.widget'] = QWidget()
        self.window.ui.nodes['presets.widget'].setLayout(presets)
        self.window.ui.nodes['presets.widget'].setMinimumHeight(180)
        self.window.ui.nodes['presets.widget'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        return self.window.ui.nodes['presets.widget']

    def setup_presets(self) -> QVBoxLayout:
        """
        Setup list

        :return: QVBoxLayout
        """
        self.window.ui.nodes['preset.presets.new'] = QPushButton(QIcon(":/icons/add.svg"), "")
        self.window.ui.nodes['preset.presets.new'].clicked.connect(
            lambda: self.window.controller.presets.editor.edit()
        )

        self.window.ui.nodes['preset.presets.label'] = TitleLabel(trans("toolbox.presets.label"))
        self.window.ui.nodes['preset.agents.label'] = TitleLabel(trans("toolbox.agents.label"))
        self.window.ui.nodes['preset.experts.label'] = TitleLabel(trans("toolbox.experts.label"))
        self.window.ui.nodes['preset.presets.label'].setVisible(False)
        self.window.ui.nodes['preset.agents.label'].setVisible(False)
        self.window.ui.nodes['preset.experts.label'].setVisible(False)

        header = QHBoxLayout()
        header.addWidget(self.window.ui.nodes['preset.presets.label'])
        header.addWidget(self.window.ui.nodes['preset.agents.label'])
        header.addWidget(self.window.ui.nodes['preset.experts.label'])
        header.addWidget(self.window.ui.nodes['preset.presets.new'], alignment=Qt.AlignRight)
        header.setContentsMargins(5, 0, 0, 0)

        self.window.ui.nodes[self.id] = PresetList(self.window, self.id)
        self.window.ui.nodes[self.id].selection_locked = self.window.controller.presets.preset_change_locked
        self.window.ui.nodes[self.id].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.window.ui.nodes['tip.toolbox.presets'] = HelpLabel(trans('tip.toolbox.presets'), self.window)
        self.window.ui.nodes['tip.toolbox.presets'].setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addLayout(header)
        layout.addWidget(self.window.ui.nodes[self.id], 1)
        layout.addWidget(self.window.ui.nodes['tip.toolbox.presets'])
        layout.setContentsMargins(2, 5, 5, 5)

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

    def update_presets(self, data):
        """
        Update presets list

        :param data: Data to update
        """
        mode = self.window.core.config.get('mode')
        view = self.window.ui.nodes[self.id]
        model = self.window.ui.models[self.id]

        view.backup_selection()

        if model is None:
            model = self.create_model(self.window)
            self.window.ui.models[self.id] = model
            view.setModel(model)

        blocker = QtCore.QSignalBlocker(model)

        rc = model.rowCount()
        if rc:
            model.removeRows(0, rc)

        count = len(data)
        if count:
            model.setRowCount(count)
            count_experts = self.window.core.experts.count_experts
            for i, (key, item) in enumerate(data.items()):
                name = item.name
                if mode == MODE_EXPERT and not key.startswith("current.") and item.enabled:
                    name = "[x] " + name
                elif mode == MODE_AGENT:
                    num_experts = count_experts(key)
                    if num_experts > 0:
                        name = f"{name} ({num_experts} experts)"

                prompt = str(item.prompt)
                tooltip = prompt if len(prompt) <= 80 else prompt[:80] + '...'

                index = model.index(i, 0)
                model.setData(index, name, QtCore.Qt.DisplayRole)
                model.setData(index, tooltip, QtCore.Qt.ToolTipRole)

        del blocker

        view.restore_selection()