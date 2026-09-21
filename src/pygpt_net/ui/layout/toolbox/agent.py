#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.21 11:05:00                  #
# ================================================== #

from PySide6.QtCore import QSize
from PySide6.QtWidgets import (
    QLabel,
    QSizePolicy,
    QStyle,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from pygpt_net.ui.widget.option.slider import OptionSlider
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
from pygpt_net.utils import trans


class AgentOptionsTabs(QTabWidget):
    """Compact tabs whose height follows only the currently visible page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.currentChanged.connect(lambda _index: self.updateGeometry())

    def _current_page_hint_height(self, minimum: bool = False) -> int:
        page = self.currentWidget()
        page_h = 0
        if page is not None:
            try:
                hint = page.minimumSizeHint() if minimum else page.sizeHint()
                page_h = max(0, int(hint.height()))
            except Exception:
                page_h = 0

        tab_h = 0
        try:
            tab_h = max(0, int(self.tabBar().sizeHint().height()))
        except Exception:
            pass

        frame = 0
        try:
            frame = 2 * max(0, int(self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)))
        except Exception:
            pass

        return max(0, page_h + tab_h + frame)

    def minimumSizeHint(self) -> QSize:
        base = super().minimumSizeHint()
        height = max(self.minimumHeight(), self._current_page_hint_height(minimum=True))
        return QSize(base.width(), height)

    def sizeHint(self) -> QSize:
        base = super().sizeHint()
        height = max(self.minimumHeight(), self._current_page_hint_height(minimum=False))
        return QSize(base.width(), height)


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

        # Flow: keep only the run-control toggles on one compact page.
        flow_page = QWidget(container)
        flow_layout = QVBoxLayout(flow_page)
        flow_layout.addWidget(cfg['agent.auto_stop'])
        flow_layout.addWidget(cfg['agent.continue'])
        flow_layout.setContentsMargins(0, 4, 0, 0)

        # Steps: keep the iteration description and slider together.
        steps_page = QWidget(container)
        steps_layout = QVBoxLayout(steps_page)
        steps_layout.addWidget(nodes['agent.iterations.label'])
        steps_layout.addWidget(cfg['agent.iterations'])
        steps_layout.setContentsMargins(0, 10, 0, 0)

        tabs = AgentOptionsTabs(container)
        tabs.setDocumentMode(True)
        tabs.tabBar().setExpanding(True)
        tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        tabs.addTab(flow_page, trans("toolbox.agent.tab.flow"))
        tabs.addTab(steps_page, trans("toolbox.agent.tab.steps"))
        nodes['agent.options.tabs'] = tabs

        rows = QVBoxLayout()
        rows.addWidget(tabs)
        rows.setContentsMargins(0, 0, 0, 0)

        nodes['agent.options'] = container
        nodes['agent.options'].setLayout(rows)
        nodes['agent.options'].setContentsMargins(0, 0, 0, 0)

        return nodes['agent.options']
