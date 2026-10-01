#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 22:50:00                  #
# ================================================== #

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .input import Input
from .output import Output


class ChatMain:
    def __init__(self, window=None):
        """
        Chat UI

        :param window: Window instance
        """
        self.window = window
        self.input = Input(window)
        self.output = Output(window)

    def setup(self):
        """
        Setup chat main layout

        :return: QWidget
        :rtype: QWidget
        """
        input_widget = self.input.setup()
        output_widget = self.output.setup()

        # The shared input starts in column 0.  Tabs controller will move the
        # same widget to column 1 whenever a chat tab there gains focus.
        layout = self.window.ui.layout
        splitter = layout.mount_chat_input(input_widget, 0)
        if splitter is not None:
            splitter.splitterMoved.connect(self.on_splitter_moved)
            self.window.controller.ui.splitter_output_size_input = splitter.sizes()

        # Also observe the second column's splitter. It does not own the input
        # initially, but may become main.output later after a column-focus
        # switch. Connecting both once avoids reconnecting on every move.
        splitter_1 = layout.get_input_splitter(1)
        if splitter_1 is not None and splitter_1 is not splitter:
            splitter_1.splitterMoved.connect(self.on_splitter_moved)

        # Keep the application-wide status/footer outside the per-column
        # output/input splitters. Only input.root (composer + Plugins / MCP /
        # Skills / ctx) is mounted under a chat column.
        widget = QWidget()
        widget_layout = QVBoxLayout(widget)
        widget_layout.setContentsMargins(0, 0, 0, 0)
        widget_layout.setSpacing(0)
        widget_layout.addWidget(output_widget, 1)

        global_footer = self.window.ui.nodes.get('input.footer.container')
        if global_footer is not None:
            widget_layout.addWidget(global_footer, 0)

        return widget

    @Slot(int, int)
    def on_splitter_moved(self, pos, index):
        """
        Store the size of the output splitter when it is moved
        """
        tabs = self.window.ui.tabs
        if "input" not in tabs:
            return
        splitter = self.window.ui.splitters.get('main.output')
        if splitter is None:
            return
        idx = tabs['input'].currentIndex()
        sizes = splitter.sizes()
        if idx != 0:
            self.window.controller.ui.splitter_output_size_files = sizes
        else:
            self.window.controller.ui.splitter_output_size_input = sizes