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
"""Notepad tool lifecycle and independent document frontends."""
from PySide6.QtGui import QAction, QIcon
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.tools.base import BaseTool, ToolMenuAction, ToolToolbarItem
from pygpt_net.utils import trans
from .core.documents import Documents
from .core.storage import Storage
from .core.tabs import Tabs
from .ui.widget import NotepadWidget

class Notepad(BaseTool):
    def __init__(self):
        super().__init__()
        self.id = 'notepad'
        self.allow_tab = True
        self.hide_in_tab_tools = True
        self.allow_dialog = False
        self.multi_tab = True
        self.on_menu_click = ToolMenuAction.ALWAYS_TAB
        self.tab_title = 'output.tab.notepad'
        self.tab_icon = ':/icons/note1.svg'
        self.storage = Storage(self)
        self.documents = Documents(self)
        self.tabs = Tabs(self)

    def attach(self, window):
        super().attach(window)
        self.storage.attach()

    def get_toolbar(self):
        return [ToolToolbarItem(
            icon=self.tab_icon, title=self.tab_title,
            handler=lambda: self.window.controller.toolbar.toggle_tool(Tab.TAB_TOOL, self.id),
        )]

    def as_tab(self, tab):
        document = self.documents.create(tab.data_id)
        document.loading = True
        widget = document.widget = NotepadWidget(document, self.window)
        tab.data_id = document.item.idx
        if not tab.title:
            tab.title = document.item.title or self.tabs.next_title()
        widget.set_tab(tab)
        widget.textarea.id = document.item.idx
        self.register_surface(document, widget, tab=tab)
        document.restore()
        return widget

    def get_tab_title(self, tab):
        return tab.title or self.tabs.next_title()

    def on_selected(self, tab):
        self.tabs.opened_once = True
        document = self.documents.opened.get(tab.data_id)
        if document is None:
            return
        if not document.opened and document.item.scroll_pos in (None, -1):
            document.widget.textarea.view.bottom()
        document.opened = True

    def on_exit(self):
        self.documents.save_all()

    def on_reload(self):
        self.tabs.opened_once = False
        # Tab reconstruction loads each document against the new profile already.
        # Never reload its text here: it may have been edited since reconstruction.

    def setup_theme(self):
        for widget in self.documents.widgets.values():
            widget.textarea.apply_theme_style()
            widget.textarea.value = self.window.core.config.get('font_size')
            widget.textarea.markers.apply_theme()

    def apply_lang_mappings(self):
        super().apply_lang_mappings()
        for widget in self.documents.widgets.values():
            widget.help_label.setText(trans('tip.output.tab.notepad'))
            widget.set_mic_state(self.window.controller.audio.ui.is_recording_in(widget))

    def get_tab_menu(self, parent, idx, column_idx, caller):
        action = QAction(QIcon(':/icons/add.svg'), trans('action.tab.add.notepad'), parent)
        action.triggered.connect(
            lambda checked=False: caller.add_tab(idx, column_idx, Tab.TAB_TOOL, self.id)
        )
        return [action]

    def populate_tab_menu(self, menu, tab):
        if self.tabs.count() > 1:
            action = menu.addAction(trans('action.tab.close_all.notepad'))
            action.triggered.connect(lambda checked=False: self.tabs.close_all(tab.column_idx))
            menu.addSeparator()

    def setup_menu(self):
        action = QAction(QIcon(self.tab_icon), trans(self.tab_title), self.window)
        action.triggered.connect(self.on_menu_action)
        self.add_lang_mapping(action, self.tab_title)
        return {self.id: action}
