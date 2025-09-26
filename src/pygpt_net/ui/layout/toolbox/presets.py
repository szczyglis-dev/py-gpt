#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.26 03:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel, QStandardItem, Qt, QIcon
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

        view: PresetList = nodes[self.id]
        model = models.get(self.id)

        # If view requested selection override, do NOT override it by backup
        selection_override_ids = getattr(view, "_selection_override_ids", None)
        if not selection_override_ids:
            view.backup_selection()

        if model is None:
            model = self.create_model(self.window)
            models[self.id] = model
            view.setModel(model)

        # Block user input during model rebuild to avoid crashes on quick clicks
        view.begin_model_update()

        # Turn off updates to avoid flicker and transient artifacts
        view.setUpdatesEnabled(False)
        try:
            # Rebuild model cleanly to avoid any stale items causing visual glitches
            model.clear()
            model.setColumnCount(1)

            if data:
                is_expert_mode = (mode == MODE_EXPERT)
                is_agent_mode = (mode == MODE_AGENT)
                count_experts = self.window.core.experts.count_experts if is_agent_mode else None
                startswith_current = "current."

                role_uuid = QtCore.Qt.UserRole + 1
                role_id = QtCore.Qt.UserRole + 2
                role_is_special = QtCore.Qt.UserRole + 3

                for i, (key, item) in enumerate(data.items()):
                    qitem = QStandardItem()

                    name = item.name
                    if is_expert_mode and item.enabled and not key.startswith(startswith_current):
                        name = f"[x] {name}"
                    elif is_agent_mode:
                        num_experts = count_experts(key)
                        if num_experts > 0:
                            name = f"{name} ({num_experts} experts)"

                    prompt = str(item.prompt)
                    tooltip = prompt if len(prompt) <= 80 else f"{prompt[:80]}..."

                    qitem.setText(name)
                    qitem.setToolTip(tooltip)
                    qitem.setData(item.uuid, role_uuid)
                    qitem.setData(key, role_id)
                    qitem.setData(key.startswith(startswith_current), role_is_special)

                    # Pin row 0 (no drag, no drop)
                    # Other rows: drag enabled only; drop is handled by view between rows
                    if i != 0 and not key.startswith(startswith_current):
                        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled
                    else:
                        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
                    qitem.setFlags(flags)

                    model.appendRow(qitem)
        finally:
            # Apply pending scroll (if any) before re-enabling updates
            view.apply_pending_scroll()
            view.setUpdatesEnabled(True)

        dnd_enabled = bool(self.window.core.config.get('presets.drag_and_drop.enabled'))
        view.set_dnd_enabled(dnd_enabled)

        # If override requested, force saved selection IDs to those override IDs
        if selection_override_ids:
            view._saved_selection_ids = list(selection_override_ids)
            view._selection_override_ids = None  # consume one-shot override

        # Restore selection by ID (so it follows the same item even if rows moved)
        view.restore_selection()
        # Force repaint in case Qt defers layout until next input
        view.viewport().update()

        # Re-enable user interaction after the rebuild is fully done
        view.end_model_update()