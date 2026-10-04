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
"""Files tool lifecycle and project-aware explorer ownership."""
from PySide6.QtGui import QAction, QIcon

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.tools.base import BaseTool, ToolMenuAction, ToolToolbarItem
from pygpt_net.utils import trans
from .core.operations import Operations
from .core.transfers import Transfers
from .core.paths import Paths
from .core.chat import Chat
from .ui.explorer import FileExplorer


class Files(BaseTool):
    def __init__(self):
        super().__init__()
        self.id = 'files'
        self.allow_tab = True
        self.allow_dialog = False
        self.multi_tab = False
        self.on_menu_click = ToolMenuAction.ALWAYS_TAB
        self.tab_title = 'output.tab.files'
        self.tab_icon = ':/icons/folder_filled.svg'
        self.explorer = None
        self.operations = Operations(self)
        self.transfers = Transfers(self)
        self.paths = Paths(self)
        self.chat = Chat(self)

    def get_toolbar(self):
        return [ToolToolbarItem(
            icon=':/icons/folder.svg', title=self.tab_title,
            handler=lambda: self.window.controller.toolbar.toggle_tool(Tab.TAB_TOOL, self.id),
        )]

    def as_tab(self, tab):
        root = self.window.core.filesystem.get_data_dir()
        self.explorer = FileExplorer(self, root, {})
        self.explorer.set_tab(tab)
        self.register_surface(self, self.explorer, tab=tab)
        return self.explorer

    def open(self, path=None):
        """Reveal Files and optionally select a path in the explorer."""
        self.open_tab()
        if path and self.explorer is not None:
            self.explorer.navigate_directory(path)
        return self.explorer

    def create_surface(self):
        self.open_tab()
        return self

    def refresh(self, reload=False):
        """Refresh indexing state; update the project root without reopening a closed tab."""
        self.refresh_tooltips()
        explorer = self.explorer
        if explorer is None:
            return
        explorer.index_data = {}
        if reload:
            explorer.directory = self.window.core.filesystem.get_data_dir()
            explorer.update_view()
        explorer.model.update_idx_status({})
        explorer.refresh_empty_state()

    def get_tab_tooltip(self, tab):
        root = self.window.core.filesystem.get_data_dir(create=False)
        return f"{trans('output.tab.files.workdir')}: {root}" if root else ''

    def refresh_tooltips(self):
        for tab in self.window.controller.tabs.get_tabs_by_tool(self.id):
            tab.tooltip = self.get_tab_tooltip(tab)
            tabs = self.window.ui.layout.get_tabs_by_idx(tab.column_idx)
            if tabs is not None and tab.idx is not None and 0 <= tab.idx < tabs.count():
                tabs.setTabToolTip(tab.idx, tab.tooltip)

    def on_reload(self):
        self.chat.reset()
        self.refresh(reload=True)

    def on_exit(self):
        if self.explorer is not None:
            self.explorer.stop()

    def setup_theme(self):
        if self.explorer is not None:
            viewer = self.explorer.preview.viewer
            if hasattr(viewer, 'restore_zoom'):
                viewer.restore_zoom()

    def apply_lang_mappings(self):
        super().apply_lang_mappings()
        if self.explorer is not None:
            self.explorer.retranslate()
        self.refresh_tooltips()

    def populate_tab_menu(self, menu, tab):
        action = menu.addAction(QIcon(':/icons/reload.svg'), trans('action.refresh'))
        action.triggered.connect(lambda checked=False: self.refresh())
        menu.addSeparator()

    def setup_menu(self):
        action = QAction(QIcon(self.tab_icon), trans(self.tab_title), self.window)
        action.triggered.connect(self.on_menu_action)
        self.add_lang_mapping(action, self.tab_title)
        return {self.id: action}
