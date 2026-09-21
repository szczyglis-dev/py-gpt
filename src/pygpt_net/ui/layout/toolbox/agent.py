#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.21 15:45:00                  #
# ================================================== #

from PySide6.QtWidgets import (
    QLabel,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

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

        # Flow: run-control switches.
        flow_page = QWidget(container)
        flow_layout = QVBoxLayout(flow_page)
        flow_layout.addWidget(cfg['agent.auto_stop'])
        flow_layout.addWidget(cfg['agent.continue'])
        flow_layout.setContentsMargins(0, 4, 0, 0)

        # Steps: iteration limit controls.
        steps_page = QWidget(container)
        steps_layout = QVBoxLayout(steps_page)
        steps_layout.addWidget(nodes['agent.iterations.label'])
        steps_layout.addWidget(cfg['agent.iterations'])
        steps_layout.setContentsMargins(0, 10, 0, 0)

        # Let Qt calculate the tab block height directly from its pages.  This
        # block lives in the fixed toolbox footer, so no manual height syncing
        # or custom sizeHint/minimumSizeHint handling is necessary here.
        tabs = QTabWidget(container)
        tabs.setObjectName('agentOptionsTabs')
        tabs.setDocumentMode(True)
        tabs.tabBar().setObjectName('agentOptionsTabBar')
        tabs.tabBar().setExpanding(True)
        tabs.tabBar().setDrawBase(False)
        tabs.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        tabs.addTab(flow_page, trans("toolbox.agent.tab.flow"))
        tabs.addTab(steps_page, trans("toolbox.agent.tab.steps"))
        nodes['agent.options.tabs'] = tabs

        rows = QVBoxLayout(container)
        rows.addWidget(tabs)
        rows.setContentsMargins(0, 0, 0, 0)

        container.setContentsMargins(0, 0, 0, 0)
        container.setMinimumWidth(0)
        container.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        nodes['agent.options'] = container

        return container
