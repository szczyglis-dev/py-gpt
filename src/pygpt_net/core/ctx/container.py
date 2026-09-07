#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.08 11:15:00                  #
# ================================================== #

from typing import List

from PySide6.QtWidgets import QVBoxLayout, QWidget

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.ui.widget.textarea.output import ChatOutput
from pygpt_net.item.ctx import CtxItem

from .bag import Bag


class Container:
    def __init__(self, window=None):
        """
        Context output container

        :param window: Window
        """
        self.window = window
        self.bags = {0: Bag(window)}

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
        nodes = self.window.ui.nodes

        if tab.pid in nodes['output_plain']:
            nodes['output_plain'][tab.pid].on_delete()  # clean up
            nodes['output_plain'][tab.pid] = None
            del nodes['output_plain'][tab.pid]
        if tab.pid in nodes['output']:
            nodes['output'][tab.pid].on_delete()  # clean up
            nodes['output'][tab.pid] = None
            del nodes['output'][tab.pid]

        self.window.controller.chat.render.remove_pid(tab.pid)  # remove pid data from renderer registry
        self.window.core.ctx.output.remove_pid(tab.pid)  # remove pid from ctx output mapping

    def get_active_pid(self) -> int:
        """
        Get PID of the chat that owns the active context.

        An in-flight request is authoritative. Once a render target has been
        pinned, context reads/writes must stay on that chat even if another chat
        in the second column receives focus. Without this, the shared Ctx core
        can start reading the second tab's Bag while the first request is still
        running, which makes histories/responses bleed between both WebViews.

        :return: chat-tab PID
        """
        core = self.window.core
        tabs = core.tabs
        ctx = getattr(core, "ctx", None)
        output = getattr(ctx, "output", None) if ctx is not None else None
        meta = ctx.get_current_meta() if ctx is not None else None

        # A top-level request owner is stronger than both global context and UI
        # focus. It also exists before a new/empty chat has a CtxMeta.
        if output is not None:
            chat_pid = output.get_request_pid()
            if chat_pid is not None:
                return chat_pid

        # Request/render pin has priority over UI focus, including focus on a
        # *different chat tab*. This is the important split-view isolation rule.
        if output is not None and meta is not None:
            chat_pid = output.get_pinned_pid(meta)
            if chat_pid is not None:
                return chat_pid

        # Normal idle case: the focused chat owns its own Bag.
        pid = self.window.controller.ui.tabs.get_current_pid()
        tab = tabs.get_tab_by_pid(pid) if pid is not None else None
        if tab is not None and tab.type == Tab.TAB_CHAT:
            return pid

        # Focus is on a non-chat tab (Code Interpreter, Files, etc.). Resolve
        # the current meta's mapped chat instead of allocating a Bag for tool PID.
        if output is not None and meta is not None:
            chat_pid = output.get_pid(meta)
            chat_tab = tabs.get_tab_by_pid(chat_pid) if chat_pid is not None else None
            if chat_tab is not None and chat_tab.type == Tab.TAB_CHAT:
                return chat_pid

        if output is not None:
            chat_pid = output.get_last_chat_pid()
            chat_tab = tabs.get_tab_by_pid(chat_pid) if chat_pid is not None else None
            if chat_tab is not None and chat_tab.type == Tab.TAB_CHAT:
                return chat_pid

        first_chat = tabs.get_first_tab_by_type(Tab.TAB_CHAT)
        if first_chat is not None:
            return first_chat.pid

        return 0

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
