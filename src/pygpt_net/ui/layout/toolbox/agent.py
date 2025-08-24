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

from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
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
        window = self.window
        ui = window.ui
        nodes = ui.nodes
        cfg = ui.config['global']
        common = window.controller.agent.common

        container = QWidget(window)

        option = window.controller.agent.legacy.options["agent.iterations"]
        nodes['agent.iterations.label'] = QLabel(trans("toolbox.agent.iterations.label"), parent=container)
        nodes['agent.iterations'] = OptionSlider(window, 'global', 'agent.iterations', option)
        cfg['agent.iterations'] = nodes['agent.iterations']

        nodes['agent.auto_stop'] = ToggleLabel(trans("toolbox.agent.auto_stop.label"), parent=window)
        nodes['agent.auto_stop'].box.toggled.connect(common.toggle_auto_stop)
        cfg['agent.auto_stop'] = nodes['agent.auto_stop']

        nodes['agent.continue'] = ToggleLabel(trans("toolbox.agent.continue.label"), parent=window)
        nodes['agent.continue'].box.toggled.connect(common.toggle_continue)
        cfg['agent.continue'] = nodes['agent.continue']

        cols = QHBoxLayout()
        cols.addWidget(cfg['agent.auto_stop'])
        cols.addWidget(cfg['agent.continue'])

        rows = QVBoxLayout()
        rows.addWidget(nodes['agent.iterations.label'])
        rows.addWidget(cfg['agent.iterations'])
        rows.addLayout(cols)

        nodes['agent.options'] = container
        nodes['agent.options'].setLayout(rows)
        nodes['agent.options'].setContentsMargins(0, 0, 0, 0)

        return nodes['agent.options']