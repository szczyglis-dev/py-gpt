#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel, Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QSizePolicy

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_EXPERT,
)
from pygpt_net.ui.widget.element.labels import HelpLabel, TitleLabel
from pygpt_net.ui.widget.lists.preset import PresetList

from pygpt_net.ui.layout.toolbox.footer import Footer
from pygpt_net.utils import trans

class Presets:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        self.footer = Footer(window)
        self.id = 'preset.presets'

    def setup(self) -> QWidget:
        """
        Setup presets

        :return: QWidget
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
        nodes = self.window.ui.nodes

        nodes['preset.presets.new'] = QPushButton(QIcon(":/icons/add.svg"), "")
        nodes['preset.presets.new'].clicked.connect(
            lambda _=False: self.window.controller.presets.editor.edit()
        )

        nodes['preset.presets.label'] = TitleLabel(trans("toolbox.presets.label"))
        nodes['preset.agents.label'] = TitleLabel(trans("toolbox.agents.label"))
        nodes['preset.experts.label'] = TitleLabel(trans("toolbox.experts.label"))
        nodes['preset.presets.label'].setVisible(False)
        nodes['preset.agents.label'].setVisible(False)
        nodes['preset.experts.label'].setVisible(False)

        header = QHBoxLayout()
        header.addWidget(nodes['preset.presets.label'])
        header.addWidget(nodes['preset.agents.label'])
        header.addWidget(nodes['preset.experts.label'])
        header.addWidget(nodes['preset.presets.new'], alignment=Qt.AlignRight)
        header.setContentsMargins(5, 0, 0, 0)

        nodes[self.id] = PresetList(self.window, self.id)
        nodes[self.id].selection_locked = self.window.controller.presets.preset_change_locked
        nodes[self.id].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        nodes['tip.toolbox.presets'] = HelpLabel(trans('tip.toolbox.presets'), self.window)
        nodes['tip.toolbox.presets'].setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addLayout(header)
        layout.addWidget(nodes[self.id], 1)
        layout.addWidget(nodes['tip.toolbox.presets'])
        layout.setContentsMargins(2, 5, 5, 5)

        self.window.ui.models[self.id] = self.create_model(self.window)
        nodes[self.id].setModel(self.window.ui.models[self.id])

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
        nodes = self.window.ui.nodes
        models = self.window.ui.models

        view = nodes[self.id]
        model = models.get(self.id)

        view.backup_selection()

        if model is None:
            model = self.create_model(self.window)
            models[self.id] = model
            view.setModel(model)

        view.setUpdatesEnabled(False)
        try:
            if not data:
                model.setRowCount(0)
            else:
                count = len(data)
                model.setRowCount(count)

                is_expert_mode = (mode == MODE_EXPERT)
                is_agent_mode = (mode == MODE_AGENT)
                count_experts = self.window.core.experts.count_experts if is_agent_mode else None
                startswith_current = "current."

                index_fn = model.index
                set_item_data = model.setItemData
                display_role = QtCore.Qt.DisplayRole
                tooltip_role = QtCore.Qt.ToolTipRole

                for i, (key, item) in enumerate(data.items()):
                    name = item.name
                    if is_expert_mode and item.enabled and not key.startswith(startswith_current):
                        name = f"[x] {name}"
                    elif is_agent_mode:
                        num_experts = count_experts(key)
                        if num_experts > 0:
                            name = f"{name} ({num_experts} experts)"

                    prompt = str(item.prompt)
                    tooltip = prompt if len(prompt) <= 80 else f"{prompt[:80]}..."

                    idx = index_fn(i, 0)
                    set_item_data(idx, {display_role: name, tooltip_role: tooltip})
        finally:
            view.setUpdatesEnabled(True)

        view.restore_selection()