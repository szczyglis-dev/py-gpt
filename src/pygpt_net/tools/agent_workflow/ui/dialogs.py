#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.17 14:45:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout

from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.utils import trans

from .widgets import WorkflowWidget


class Tool:
    def __init__(self, window=None, tool=None):
        self.window = window
        self.tool = tool
        self.widget = WorkflowWidget(window, tool)

    def as_tab(self):
        return self.widget

    def set_tab(self, tab):
        self.widget.set_tab(tab)

    def setup(self):
        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        layout.setContentsMargins(6, 6, 6, 6)
        self.window.ui.dialog["agent_workflow"] = ToolDialog(self.window)
        self.window.ui.dialog["agent_workflow"].setLayout(layout)
        self.window.ui.dialog["agent_workflow"].setWindowTitle(trans("dialog.agent_workflow.title"))
        self.window.ui.dialog["agent_workflow"].resize(900, 650)


class ToolDialog(BaseDialog):
    def __init__(self, window=None, id="agent_workflow"):
        super().__init__(window, id)
        self.window = window

    def closeEvent(self, event):
        tool = self.window.tools.get("agent_workflow")
        if tool is not None:
            tool.opened = False
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)
