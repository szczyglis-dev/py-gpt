#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.14 13:55:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy, QComboBox, QPushButton

from pygpt_net.core.types import MODE_AGENT_V2
from pygpt_net.ui.widget.element.labels import HelpLabel, TitleLabel
from pygpt_net.ui.widget.option.prompt import PromptTextarea
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
from pygpt_net.utils import trans


AGENT_V2_MODE_CONFIG_KEY = "agent.v2.mode"
AGENT_V2_MODE_DEFAULT = "chat"
AGENT_V2_STEP_BY_STEP_CONFIG_KEY = "agent.v2.step_by_step"
AGENT_V2_STEP_BY_STEP_DEFAULT = False

class Prompt:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window
        # Logical hover sections exposed to ToolboxMain. Keep visual-state
        # grouping independent from layout grouping.
        self.hover_sections = []

    def _on_agent_v2_mode_changed(self, index: int) -> None:
        """Persist the selected Agents v2 runtime strategy."""
        combo = self.window.ui.nodes.get('agent.v2.mode')
        if combo is None:
            return
        value = combo.itemData(index) or AGENT_V2_MODE_DEFAULT
        self.window.core.config.set(AGENT_V2_MODE_CONFIG_KEY, str(value))
        self.window.core.config.save()

    def _on_agent_v2_step_by_step_changed(self, checked: bool) -> None:
        """Persist optional step-by-step prompting for Chat with Agents."""
        self.window.core.config.set(AGENT_V2_STEP_BY_STEP_CONFIG_KEY, bool(checked))
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
        for agent in w.core.agents_v2.editor.get_agents():
            if agent.get("built_in"):
                text = trans(str(agent.get("label_key") or ""))
            else:
                text = str(agent.get("name") or agent.get("id") or "")
            mode_combo.addItem(text, agent["id"])
        mode_combo.setMinimumWidth(40)
        mode_combo.setToolTip(trans("agent.v2.mode.tooltip"))

        configured_mode = str(
            w.core.config.get(AGENT_V2_MODE_CONFIG_KEY, AGENT_V2_MODE_DEFAULT) or AGENT_V2_MODE_DEFAULT
        ).strip()
        configured_mode, _, _ = w.core.agents_v2.editor.resolve_selection(configured_mode)
        mode_index = mode_combo.findData(configured_mode)
        if mode_index < 0:
            mode_index = mode_combo.findData(AGENT_V2_MODE_DEFAULT)
        if mode_index >= 0:
            mode_combo.setCurrentIndex(mode_index)

        mode_combo.currentIndexChanged.connect(self._on_agent_v2_mode_changed)
        nodes['agent.v2.mode.label'] = mode_label
        nodes['agent.v2.mode'] = mode_combo

        step_by_step = ToggleLabel(
            trans("agent.v2.step_by_step"),
            parent=w,
        )
        step_by_step.setChecked(bool(
            w.core.config.get(
                AGENT_V2_STEP_BY_STEP_CONFIG_KEY,
                AGENT_V2_STEP_BY_STEP_DEFAULT,
            )
        ))
        step_tooltip = trans("agent.v2.step_by_step.tooltip")
        step_by_step.setToolTip(step_tooltip)
        step_by_step.box.setToolTip(step_tooltip)
        step_by_step.label.setToolTip(step_tooltip)
        step_by_step.box.toggled.connect(self._on_agent_v2_step_by_step_changed)
        nodes['agent.v2.step_by_step'] = step_by_step

        manage_agents = QPushButton(QIcon(":/icons/settings.svg"), "")
        icon_size = 20
        manage_agents.setFlat(True)
        manage_agents.setStyleSheet("QPushButton { border: none; padding: 0; }")
        manage_agents.setIconSize(QSize(icon_size, icon_size))
        manage_agents.setFixedSize(icon_size, icon_size)
        manage_agents.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        manage_agents.setFocusPolicy(Qt.NoFocus)
        manage_agents.setCursor(Qt.PointingHandCursor)
        manage_agents.setToolTip(trans("toolbox.agent.v2.manage.tooltip"))
        manage_agents.clicked.connect(w.controller.agents_v2.editor.open)
        nodes['agent.v2.manage'] = manage_agents

        mode_widget = QWidget()
        mode_layout = QVBoxLayout(mode_widget)

        mode_select_widget = QWidget()
        mode_select_layout = QHBoxLayout(mode_select_widget)
        mode_select_layout.addWidget(mode_label, 0)
        mode_select_layout.addWidget(mode_combo, 1)
        mode_select_layout.setContentsMargins(0, 0, 0, 0)

        step_widget = QWidget()
        step_layout = QHBoxLayout(step_widget)
        step_layout.addWidget(step_by_step, 1)
        step_layout.addWidget(manage_agents, 0, Qt.AlignRight | Qt.AlignVCenter)
        step_layout.setContentsMargins(0, 0, 0, 0)

        mode_layout.addWidget(mode_select_widget)
        mode_layout.addWidget(step_widget)
        mode_layout.setContentsMargins(3, 0, 5, 0)
        mode_widget.setVisible(w.core.config.get("mode") == MODE_AGENT_V2)
        nodes['agent.v2.mode.widget'] = mode_widget

        nodes['tip.toolbox.prompt'] = HelpLabel(trans('tip.toolbox.prompt'), w)
        nodes['tip.toolbox.prompt'].setAlignment(Qt.AlignCenter)

        # Keep System prompt and Agents v2 runtime mode as separate logical
        # hover areas. The outer widget is layout-only and is deliberately not
        # registered as a hover section.
        prompt_section = QWidget()
        prompt_section_layout = QVBoxLayout(prompt_section)
        prompt_section_layout.addWidget(header_widget)
        prompt_section_layout.addWidget(nodes['preset.prompt'])
        prompt_section_layout.addWidget(nodes['tip.toolbox.prompt'])
        prompt_section_layout.setContentsMargins(0, 0, 0, 0)
        nodes['toolbox.prompt.section'] = prompt_section

        layout_widget = QWidget()
        layout = QVBoxLayout(layout_widget)
        layout.addWidget(prompt_section)
        layout.addWidget(nodes['agent.v2.mode.widget'])
        layout.setContentsMargins(2, 5, 5, 5)

        self.hover_sections = [
            prompt_section,
            nodes['agent.v2.mode.widget'],
        ]

        layout_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return layout_widget