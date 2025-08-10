#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.05 21:00:00                  #
# ================================================== #

from typing import List

from PySide6.QtWidgets import QVBoxLayout, QWidget

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.ui.widget.textarea.output import ChatOutput

from .bag import Bag
from ...item.ctx import CtxItem


class Container:
    def __init__(self, window=None):
        """
        Context output container

        :param window: Window
        """
        self.window = window
        self.bags = {}
        self.bags[0] = Bag(window)  # always create initial bag

    def get(self, tab: Tab) -> QWidget:
        """
        Register and return output

        :param tab: Tab
        :return: Widget
        """
        # plain output
        output_plain = ChatOutput(self.window)
        output_plain.set_tab(tab)

        # web
        if self.window.core.config.get("render.engine") == "web":
            from pygpt_net.ui.widget.textarea.web import ChatWebOutput
            
            # build output
            output_html = ChatWebOutput(self.window)
            output_html.set_tab(tab)

            # connect signals
            output_html.signals.save_as.connect(self.window.controller.chat.render.handle_save_as)
            output_html.signals.audio_read.connect(self.window.controller.chat.render.handle_audio_read)
        else:
            # legacy
            output_html = ChatOutput(self.window)
            output_html.set_tab(tab)

        if 'output_plain' not in self.window.ui.nodes:
            self.window.ui.nodes['output_plain'] = {}
        if 'output' not in self.window.ui.nodes:
            self.window.ui.nodes['output'] = {}

        self.window.ui.nodes['output_plain'][tab.pid] = output_plain
        self.window.ui.nodes['output'][tab.pid] = output_html

        # show/hide plain/html
        if self.window.core.config.get("render.plain") is True:
            output_plain.setVisible(True)
            output_html.setVisible(False)
        else:
            output_plain.setVisible(False)
            output_html.setVisible(True)

        # add refs
        tab.add_ref(output_plain)
        tab.add_ref(output_html)
        tab.on_delete = self.cleanup  # set cleanup handler

        # build layout
        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['output_plain'][tab.pid])
        layout.addWidget(self.window.ui.nodes['output'][tab.pid])
        layout.setContentsMargins(0, 0, 0, 0)
        return self.window.core.tabs.from_layout(layout)

    def cleanup(self, tab: Tab):
        """
        Clean up on delete

        :param tab: Tab
        """
        if tab.pid in self.window.ui.nodes['output_plain']:
            self.window.ui.nodes['output_plain'][tab.pid].on_delete()  # clean up
            self.window.ui.nodes['output_plain'][tab.pid] = None
            del self.window.ui.nodes['output_plain'][tab.pid]
        if tab.pid in self.window.ui.nodes['output']:
            self.window.ui.nodes['output'][tab.pid].on_delete()  # clean up
            self.window.ui.nodes['output'][tab.pid] = None
            del self.window.ui.nodes['output'][tab.pid]

        self.window.controller.chat.render.remove_pid(tab.pid)  # remove pid data from renderer registry
        self.window.core.ctx.output.remove_pid(tab.pid)  # remove pid from ctx output mapping

    def get_active_pid(self) -> int:
        """
        Get active PID

        :return: PID
        """
        pid = self.window.controller.ui.tabs.get_current_pid()
        if pid is not None:
            return pid
        return 0  # default bag

    def get_active_tab_id(self) -> int:
        """
        Get active tab ID

        :return: Tab ID
        """
        return self.get_active_pid()

    def get_active_bag(self) -> Bag:
        """
        Get active bag

        :return: Bag
        """
        tab_id = self.get_active_tab_id()
        if tab_id not in self.bags:
            self.bags[tab_id] = Bag(self.window)  # crate new empty bag if not exists
        return self.bags[tab_id]

    def get_items(self) -> List[CtxItem]:
        """
        Get ctx items

        :return: Items
        """
        return self.get_active_bag().get_items()

    def set_items(self, items: List[CtxItem]):
        """
        Set ctx items

        :param items: Items
        """
        self.get_active_bag().set_items(items)

    def clear_items(self):
        """Clear ctx items"""
        self.get_active_bag().clear_items()

    def count_items(self) -> int:
        """
        Count ctx items

        :return: Items count
        """
        return self.get_active_bag().count_items()
