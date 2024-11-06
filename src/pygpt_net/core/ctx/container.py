#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .bag import Bag
from pygpt_net.ui.widget.tabs.output import OutputTabs
from pygpt_net.ui.widget.textarea.output import ChatOutput
from ...utils import trans


class Container:
    def __init__(self, window=None):
        """
        Context container
        """
        self.window = window
        self.bags = {}
        self.bags[0] = Bag(window)

    def register_output(self, id: int = 0):
        # plain output
        output_plain = ChatOutput(self.window)

        # web
        if self.window.core.config.get("render.engine") == "web":
            from pygpt_net.ui.widget.textarea.web import ChatWebOutput, CustomWebEnginePage
            # build output
            output_html = ChatWebOutput(self.window)
            output_html.setPage(
                CustomWebEnginePage(self.window, output_html)
            )
            # connect signals
            output_html.signals.save_as.connect(self.window.controller.chat.render.handle_save_as)
            output_html.signals.audio_read.connect(self.window.controller.chat.render.handle_audio_read)
        else:
            # legacy
            output_html = ChatOutput(self.window)

        if 'output_plain' not in self.window.ui.nodes:
            self.window.ui.nodes['output_plain'] = {}
        if 'output' not in self.window.ui.nodes:
            self.window.ui.nodes['output'] = {}
        self.window.ui.nodes['output_plain'][id] = output_plain
        self.window.ui.nodes['output'][id] = output_html

        # show/hide plain/html
        if self.window.core.config.get("render.plain") is True:
            output_plain.setVisible(True)
            output_html.setVisible(False)
        else:
            output_plain.setVisible(False)
            output_html.setVisible(True)

        # layout
        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['output_plain'][id])
        layout.addWidget(self.window.ui.nodes['output'][id])
        layout.setContentsMargins(0, 0, 0, 0)
        widget = self.window.core.tabs.from_layout(layout)

        # TODO: init here

        """
        idx = self.window.ui.tabs['output'].addTab(output_widget, trans('output.tab.chat'))

        self.window.ui.tabs['output'].setTabIcon(3, QIcon(":/icons/chat.svg"))
        self.window.ui.tabs['output'].setTabIcon(0, QIcon(":/icons/folder_filled.svg"))
        self.window.ui.tabs['output'].setTabIcon(1, QIcon(":/icons/schedule.svg"))
        self.window.ui.tabs['output'].setTabIcon(2, QIcon(":/icons/brush.svg"))
        """

        return widget

    def get_active_pid(self):
        return 0

    def get_active_tab_id(self):
        return 0

    def get_active_bag(self):
        tab_id = self.get_active_tab_id()
        if tab_id not in self.bags:
            self.bags[tab_id] = Bag(self.window)  # crate new empty bag if not exists
        return self.bags[tab_id]

    def get_items(self):
        return self.get_active_bag().get_items()

    def set_items(self, items):
        self.get_active_bag().set_items(items)

    def clear_items(self):
        self.get_active_bag().clear_items()

    def count_items(self):
        return self.get_active_bag().count_items()
