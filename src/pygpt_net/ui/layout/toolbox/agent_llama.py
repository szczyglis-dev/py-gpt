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

from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QWidget, QCheckBox

from pygpt_net.ui.widget.option.combo import OptionCombo
from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
from pygpt_net.utils import trans


class AgentLlama:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup agent llama options

        :return: QWidget
        """
        win = self.window
        ui = win.ui
        nodes = ui.nodes
        config_global = ui.config.setdefault('global', {})
        llama_opts = win.controller.agent.llama.options

        container = QWidget(win)

        nodes['agent.llama.loop.score'] = OptionSlider(
            win,
            'global',
            'agent.llama.loop.score',
            llama_opts["agent.llama.loop.score"],
        )
        nodes['agent.llama.loop.score'].setToolTip(trans("toolbox.agent.llama.loop.score.tooltip"))
        config_global['agent.llama.loop.score'] = nodes['agent.llama.loop.score']

        nodes['agent.llama.loop.mode.label'] = QLabel(trans("toolbox.agent.llama.loop.mode.label"), parent=win)
        nodes['agent.llama.loop.mode'] = OptionCombo(
            win,
            'global',
            'agent.llama.loop.mode',
            llama_opts["agent.llama.loop.mode"],
        )
        nodes['agent.llama.loop.mode'].setToolTip(trans("toolbox.agent.llama.loop.mode.tooltip"))
        config_global['agent.llama.loop.mode'] = nodes['agent.llama.loop.mode']

        nodes['agent.llama.loop.enabled'] = ToggleLabel(trans("toolbox.agent.llama.loop.enabled.label"), parent=win)
        nodes['agent.llama.loop.enabled'].box.toggled.connect(
            win.controller.agent.common.toggle_loop
        )
        config_global['agent.llama.loop.enabled'] = nodes['agent.llama.loop.enabled']

        nodes['agent.llama.loop.label'] = QLabel(trans("toolbox.agent.llama.loop.label"), parent=win)

        cols = QHBoxLayout()
        cols.addWidget(config_global['agent.llama.loop.enabled'])
        cols.addWidget(config_global['agent.llama.loop.score'])

        rows = QVBoxLayout()
        rows.addWidget(nodes['agent.llama.loop.label'])
        rows.addLayout(cols)
        rows.addWidget(nodes['agent.llama.loop.mode'])

        container.setLayout(rows)
        container.setContentsMargins(0, 0, 0, 0)

        nodes['agent_llama.options'] = container
        return nodes['agent_llama.options']