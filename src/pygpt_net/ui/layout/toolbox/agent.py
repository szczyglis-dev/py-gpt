#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.27 05:00:00                  #
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
        # img variants
        option = self.window.controller.agent.options["agent.iterations"]
        self.window.ui.nodes['agent.iterations.label'] = QLabel(trans("toolbox.agent.iterations.label"))
        self.window.ui.config['global']['agent.iterations'] = \
            OptionSlider(
                self.window,
                'global',
                'agent.iterations',
                option,
            )

        # auto stop
        self.window.ui.config['global']['agent.auto_stop'] = QCheckBox(trans("toolbox.agent.auto_stop.label"))
        self.window.ui.config['global']['agent.auto_stop'].stateChanged.connect(
            lambda:
            self.window.controller.agent.common.toggle_auto_stop(
                self.window.ui.config['global']['agent.auto_stop'].isChecked())
        )

        # continue more
        self.window.ui.config['global']['agent.continue'] = QCheckBox(trans("toolbox.agent.continue.label"))
        self.window.ui.config['global']['agent.continue'].stateChanged.connect(
            lambda:
            self.window.controller.agent.common.toggle_continue(
                self.window.ui.config['global']['agent.continue'].isChecked())
        )

        # label
        label = QLabel(trans("toolbox.agent.iterations.label"))

        # options
        cols = QHBoxLayout()
        cols.addWidget(self.window.ui.config['global']['agent.auto_stop'])
        cols.addWidget(self.window.ui.config['global']['agent.continue'])

        # rows
        rows = QVBoxLayout()
        rows.addWidget(label)
        rows.addWidget(self.window.ui.config['global']['agent.iterations'])
        rows.addLayout(cols)

        self.window.ui.nodes['agent.options'] = QWidget()
        self.window.ui.nodes['agent.options'].setLayout(rows)
        self.window.ui.nodes['agent.options'].setContentsMargins(0, 0, 0, 0)

        return self.window.ui.nodes['agent.options']
