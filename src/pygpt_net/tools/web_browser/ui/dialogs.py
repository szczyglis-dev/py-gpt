#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import Qt
from pygpt_net.ui.widget.dialog.base import BaseDialog

from pygpt_net.core.tabs.tab import Tab

from .widgets import ToolWidget


class Tool:
    """Frontend wrapper for one independent Canvas runtime."""

    def __init__(self, window=None, tool=None, surface_kind="tab"):
        self.window = window
        self.tool = tool
        self.surface_kind = surface_kind
        self.widget = ToolWidget(window, tool, surface_kind=surface_kind)
        self.layout = None

    def as_tab(self) -> ToolWidget:
        return self.widget

    def set_tab(self, tab: Tab):
        self.widget.set_tab(tab)

    def setup(self):
        """Build the navigation controls and browser viewport."""
        self.layout = self.widget.setup()
        return self.layout

    def get_widget(self) -> ToolWidget:
        return self.widget

    def get_tab(self) -> QVBoxLayout:
        return self.layout


class CanvasDialog(BaseDialog):
    """Independent Canvas window registered alongside tab runtimes."""

    def __init__(self, window, dialog_id, runtime, manager):
        super().__init__(window, dialog_id)
        self.shared_id = manager.dialog_id
        self.runtime = runtime
        self.manager = manager
        self._released = False
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("Web/Canvas")
        self.resize(1000, 700)
        self.frontend = Tool(window, runtime, surface_kind="dialog")
        self.setLayout(self.frontend.setup())
        runtime.viewport.attach_surface(self.frontend.widget)

    def closeEvent(self, event):
        super().closeEvent(event)
        if event.isAccepted():
            self._release()

    def done(self, result):
        # Escape/reject also closes a QDialog without invoking closeEvent.
        self._release()
        super().done(result)

    def _release(self):
        if self._released:
            return
        self._released = True
        self.frontend.widget._disconnect_viewport_hooks()
        self.window.ui.dialog.pop(self.id, None)
        self.manager.release_runtime(self.runtime)
