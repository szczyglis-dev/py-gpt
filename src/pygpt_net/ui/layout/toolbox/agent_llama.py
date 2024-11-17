#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 03:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QWidget, QCheckBox

from pygpt_net.ui.widget.option.slider import OptionSlider
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
        # loop score
        option = self.window.controller.agent.options["agent.llama.loop.score"]
        self.window.ui.nodes['agent.llama.loop.score.label'] = QLabel(trans("toolbox.agent.llama.loop.score.label"))
        self.window.ui.nodes['agent.llama.loop.score'] = \
            OptionSlider(
                self.window,
                'global',
                'agent.llama.loop.score',
                option,
            )
        self.window.ui.nodes['agent.llama.loop.score'].setToolTip(trans("toolbox.agent.llama.loop.score.tooltip"))

        self.window.ui.config['global']['agent.llama.loop.score'] = self.window.ui.nodes['agent.llama.loop.score']

        # loop enabled
        self.window.ui.nodes['agent.llama.loop.enabled'] = QCheckBox(trans("toolbox.agent.llama.loop.enabled.label"))
        self.window.ui.nodes['agent.llama.loop.enabled'].stateChanged.connect(
            lambda:
            self.window.controller.agent.common.toggle_loop(
                self.window.ui.config['global']['agent.llama.loop.enabled'].isChecked())
        )
        self.window.ui.config['global']['agent.llama.loop.enabled'] = self.window.ui.nodes['agent.llama.loop.enabled']

        # label
        self.window.ui.nodes['agent.llama.loop.label'] = QLabel(trans("toolbox.agent.llama.loop.label"))

        # options
        cols = QHBoxLayout()
        cols.addWidget(self.window.ui.config['global']['agent.llama.loop.enabled'])
        cols.addWidget(self.window.ui.config['global']['agent.llama.loop.score'])

        # rows
        rows = QVBoxLayout()
        rows.addWidget(self.window.ui.nodes['agent.llama.loop.label'])
        rows.addLayout(cols)

        self.window.ui.nodes['agent_llama.options'] = QWidget()
        self.window.ui.nodes['agent_llama.options'].setLayout(rows)
        self.window.ui.nodes['agent_llama.options'].setContentsMargins(0, 0, 0, 0)

        return self.window.ui.nodes['agent_llama.options']
