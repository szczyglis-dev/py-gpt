#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.23 19:55:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout

from pygpt_net.core.tabs.tab import Tab

from .widgets import ToolWidget


class Tool:
    """Tab-only UI wrapper for the persistent Canvas and HTML runtime."""

    def __init__(self, window=None, tool=None, surface_kind="tab"):
        self.window = window
        self.tool = tool
        self.surface_kind = "tab"
        self.widget = ToolWidget(window, tool, surface_kind="tab")
        self.layout = None

    def as_tab(self) -> ToolWidget:
        return self.widget

    def set_tab(self, tab: Tab):
        self.widget.set_tab(tab)

    def setup(self):
        """Build tab contents only; Canvas and HTML has no dialog frontend."""
        self.layout = self.widget.setup()
        return self.layout

    def get_widget(self) -> ToolWidget:
        return self.widget

    def get_tab(self) -> QVBoxLayout:
        return self.layout
