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


class Agent:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup agent options

        :return: QWidget
        """
        # iterations
        option = self.window.controller.agent.options["agent.iterations"]
        self.window.ui.nodes['agent.iterations.label'] = QLabel(trans("toolbox.agent.iterations.label"))
        self.window.ui.nodes['agent.iterations'] = \
            OptionSlider(
                self.window,
                'global',
                'agent.iterations',
                option,
            )
        self.window.ui.config['global']['agent.iterations'] = self.window.ui.nodes['agent.iterations']

        # auto stop
        self.window.ui.nodes['agent.auto_stop'] = QCheckBox(trans("toolbox.agent.auto_stop.label"))
        self.window.ui.nodes['agent.auto_stop'].stateChanged.connect(
            lambda:
            self.window.controller.agent.common.toggle_auto_stop(
                self.window.ui.config['global']['agent.auto_stop'].isChecked())
        )
        self.window.ui.config['global']['agent.auto_stop'] = self.window.ui.nodes['agent.auto_stop']

        # continue more
        self.window.ui.nodes['agent.continue'] = QCheckBox(trans("toolbox.agent.continue.label"))
        self.window.ui.nodes['agent.continue'].stateChanged.connect(
            lambda:
            self.window.controller.agent.common.toggle_continue(
                self.window.ui.config['global']['agent.continue'].isChecked())
        )
        self.window.ui.config['global']['agent.continue'] = self.window.ui.nodes['agent.continue']

        # options
        cols = QHBoxLayout()
        cols.addWidget(self.window.ui.config['global']['agent.auto_stop'])
        cols.addWidget(self.window.ui.config['global']['agent.continue'])

        # rows
        rows = QVBoxLayout()
        rows.addWidget(self.window.ui.nodes['agent.iterations.label'])
        rows.addWidget(self.window.ui.config['global']['agent.iterations'])
        rows.addLayout(cols)

        self.window.ui.nodes['agent.options'] = QWidget()
        self.window.ui.nodes['agent.options'].setLayout(rows)
        self.window.ui.nodes['agent.options'].setContentsMargins(0, 0, 0, 0)

        return self.window.ui.nodes['agent.options']
