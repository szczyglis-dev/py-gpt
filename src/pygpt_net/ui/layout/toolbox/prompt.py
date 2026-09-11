#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 11:00:00                  #
# ================================================== #

from PySide6.QtGui import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy, QComboBox

from pygpt_net.core.types import MODE_AGENT_V2
from pygpt_net.ui.widget.element.labels import HelpLabel, TitleLabel
from pygpt_net.ui.widget.option.prompt import PromptTextarea
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
from pygpt_net.utils import trans


AGENT_V2_MODE_CONFIG_KEY = "agent.v2.mode"
AGENT_V2_MODE_DEFAULT = "chat"

class Prompt:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def _on_agent_v2_mode_changed(self, index: int) -> None:
        """Persist the selected Agents v2 runtime strategy."""
        combo = self.window.ui.nodes.get('agent.v2.mode')
        if combo is None:
            return
        value = combo.itemData(index) or AGENT_V2_MODE_DEFAULT
        self.window.core.config.set(AGENT_V2_MODE_CONFIG_KEY, str(value))
        self.window.core.config.save()

    def setup(self) -> QWidget:
        """
        Setup system prompt

        :return: QWidget
        """
        w = self.window
        nodes = w.ui.nodes

        nodes['toolbox.prompt.label'] = TitleLabel(trans("toolbox.prompt"))

        nodes['cmd.enabled'] = ToggleLabel(
            trans('cmd.enabled'),
            label_position="left",
            parent=w
        )
        box = nodes['cmd.enabled'].box
        box.toggled.connect(w.controller.chat.common.toggle_cmd)
        box.setToolTip(trans('cmd.tip'))

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.addWidget(nodes['toolbox.prompt.label'])
        header_layout.addStretch(1)
        header_layout.addWidget(nodes['cmd.enabled'])
        header_layout.setContentsMargins(5, 0, 10, 0)

        option = w.controller.presets.editor.get_option('prompt')
        nodes['preset.prompt'] = PromptTextarea(w, 'preset', 'prompt', option)
        nodes['preset.prompt'].setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Agents v2 runtime strategy selector. Persist machine-friendly values in
        # config while keeping the internal PRIMARY_AGENT strategy user-facing as
        # ``Chat``. The whole row is visible only in Agents v2 mode.
        mode_label = TitleLabel(trans("agent.v2.mode.label"))
        mode_combo = QComboBox()
        for text, data in (
            (trans("agent.v2.mode.chat"), "chat"),
            (trans("agent.v2.mode.orchestrator"), "orchestrator"),
            (trans("agent.v2.mode.swarm"), "swarm"),
        ):
            mode_combo.addItem(text, data)
        mode_combo.setMinimumWidth(40)

        configured_mode = str(
            w.core.config.get(AGENT_V2_MODE_CONFIG_KEY, AGENT_V2_MODE_DEFAULT) or AGENT_V2_MODE_DEFAULT
        ).strip().lower()
        # Compatibility with internal/legacy strategy names if a config was
        # edited manually before the UI selector existed.
        if configured_mode in ("primary", "primary_agent", "primary-agent"):
            configured_mode = "chat"
        mode_index = mode_combo.findData(configured_mode)
        if mode_index < 0:
            mode_index = mode_combo.findData(AGENT_V2_MODE_DEFAULT)
        if mode_index >= 0:
            mode_combo.setCurrentIndex(mode_index)

        mode_combo.currentIndexChanged.connect(self._on_agent_v2_mode_changed)
        nodes['agent.v2.mode.label'] = mode_label
        nodes['agent.v2.mode'] = mode_combo

        mode_tip = HelpLabel(trans('agent.v2.mode.tip'), w)
        mode_tip.setAlignment(Qt.AlignCenter)
        mode_tip.setVisible(bool(w.core.config.get('layout.tooltips')))
        nodes['agent.v2.mode.tip'] = mode_tip

        mode_widget = QWidget()
        mode_layout = QVBoxLayout(mode_widget)

        mode_select_widget = QWidget()
        mode_select_layout = QHBoxLayout(mode_select_widget)
        mode_select_layout.addWidget(mode_label, 0)
        mode_select_layout.addWidget(mode_combo, 1)
        mode_select_layout.setContentsMargins(0, 0, 0, 0)

        mode_layout.addWidget(mode_select_widget)
        mode_layout.addWidget(mode_tip)
        mode_layout.setContentsMargins(3, 0, 5, 0)
        mode_widget.setVisible(w.core.config.get("mode") == MODE_AGENT_V2)
        nodes['agent.v2.mode.widget'] = mode_widget

        nodes['tip.toolbox.prompt'] = HelpLabel(trans('tip.toolbox.prompt'), w)
        nodes['tip.toolbox.prompt'].setAlignment(Qt.AlignCenter)

        layout_widget = QWidget()
        layout = QVBoxLayout(layout_widget)
        layout.addWidget(header_widget)
        layout.addWidget(nodes['preset.prompt'])
        layout.addWidget(nodes['tip.toolbox.prompt'])
        layout.addWidget(nodes['agent.v2.mode.widget'])
        layout.setContentsMargins(2, 5, 5, 5)

        layout_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return layout_widget