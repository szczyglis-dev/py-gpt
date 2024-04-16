#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.17 01:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QPushButton, QLabel, QVBoxLayout, QMenuBar, QTabWidget, QHBoxLayout, QSplitter, QWidget

from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.option.combo import OptionCombo
from pygpt_net.ui.widget.textarea.editor import CodeEditor

from .browse import BrowseTab
from .ctx import CtxTab
from .files import FilesTab
from .web import WebTab

from pygpt_net.utils import trans

class DialogBuilder:
    def __init__(self, window=None):
        """
        Dialog builder

        :param window: Window instance
        """
        self.window = window
        self.menu_bar = None
        self.menu = {}
        self.actions = {}  # menu actions
        self.browse = BrowseTab(window)
        self.ctx = CtxTab(window)
        self.files = FilesTab(window)
        self.web = WebTab(window)

    def setup_menu(self) -> QMenuBar:
        """
        Setup dialog menu

        :return: QMenuBar
        """
        # create menu bar
        self.menu_bar = QMenuBar()
        self.menu["file"] = self.menu_bar.addMenu(trans("menu.file"))
        self.menu["config"] = self.menu_bar.addMenu(trans("menu.config"))

        self.actions["file.clear_log"] = QAction(QIcon(":/icons/close.svg"), trans("tool.indexer.menu.file.clear_log"))
        self.actions["file.clear_log"].triggered.connect(
            lambda: self.window.tools.get("indexer").clear_log()
        )

        self.actions["file.truncate_idx"] = QAction(QIcon(":/icons/delete.svg"), trans("tool.indexer.menu.file.remove_idx"))
        self.actions["file.truncate_idx"].triggered.connect(
            lambda: self.window.tools.get("indexer").truncate_idx()
        )

        self.actions["config.settings"] = QAction(QIcon(":/icons/settings.svg"), trans("tool.indexer.menu.config.settings"))
        self.actions["config.settings"].triggered.connect(
            lambda: self.window.tools.get("indexer").open_settings()
        )

        # add actions
        self.menu["file"].addAction(self.actions["file.clear_log"])
        self.menu["file"].addAction(self.actions["file.truncate_idx"])
        self.menu["config"].addAction(self.actions["config.settings"])
        return self.menu_bar

    def setup(self):
        """Setup dialog window"""
        browse = self.browse.setup()
        ctx = self.ctx.setup()
        files = self.files.setup()
        web = self.web.setup()

        # index select
        self.window.ui.nodes["tool.indexer.idx"] = OptionCombo(self.window, "tool.indexer", "idx", {
            "label": trans("tool.indexer.idx"),
            "keys": self.window.controller.config.placeholder.apply_by_id("idx"),
            "value": "base",
        })
        self.window.ui.add_hook("update.tool.indexer.idx", self.hook_idx_change)
        self.window.ui.nodes["tool.indexer.idx"].layout.setContentsMargins(0, 0, 0, 0)
        self.window.ui.nodes["tool.indexer.idx.label"] = QLabel(trans("tool.indexer.idx"))
        self.window.ui.nodes["tool.indexer.provider"] = HelpLabel(self.window.core.config.get("llama.idx.storage"))

        # set first index
        default_idx = None
        indexes = self.window.core.config.get("llama.idx.list")
        if indexes:
            default_idx = indexes[0]["id"]
        if default_idx:
            self.window.ui.nodes["tool.indexer.idx"].set_value(default_idx)

        idx_layout = QHBoxLayout()
        idx_layout.addWidget(self.window.ui.nodes["tool.indexer.provider"])
        idx_layout.addWidget(self.window.ui.nodes["tool.indexer.idx.label"], alignment=Qt.AlignRight)
        idx_layout.addWidget(self.window.ui.nodes["tool.indexer.idx"])

        self.window.ui.tabs['tool.indexer'] = QTabWidget(self.window)
        self.window.ui.tabs['tool.indexer'].addTab(files, trans("tool.indexer.tab.files"))
        self.window.ui.tabs['tool.indexer'].addTab(web, trans("tool.indexer.tab.web"))
        self.window.ui.tabs['tool.indexer'].addTab(ctx, trans("tool.indexer.tab.ctx"))
        self.window.ui.tabs['tool.indexer'].addTab(browse, trans("tool.indexer.tab.browser"))
        self.window.ui.tabs['tool.indexer'].currentChanged.connect(
            lambda: self.window.tools.get("indexer").on_tab_changed(self.window.ui.tabs['tool.indexer'].currentIndex())
        )

        self.window.ui.nodes["tool.indexer.status"] = CodeEditor(self.window)
        self.window.ui.nodes["tool.indexer.status"].setReadOnly(True)
        self.window.ui.nodes["tool.indexer.status"].setProperty('class', 'text-editor')
        self.window.ui.nodes["tool.indexer.btn.idx"] = QPushButton(trans("tool.indexer.idx.btn.add"))
        self.window.ui.nodes["tool.indexer.btn.idx"].clicked.connect(
            lambda: self.window.tools.get("indexer").index_data()
        )
        self.window.ui.nodes["tool.indexer.status.label"] = QLabel(trans("tool.indexer.status"))

        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes["tool.indexer.status.label"])
        bottom_layout.addWidget(self.window.ui.nodes["tool.indexer.status"])

        tabs_layout = QVBoxLayout()
        tabs_layout.setMenuBar(self.setup_menu())  # add menu bar
        tabs_layout.addLayout(idx_layout)
        tabs_layout.addWidget(self.window.ui.tabs['tool.indexer'])
        tabs_layout.addWidget(self.window.ui.nodes["tool.indexer.btn.idx"])

        tabs_widget = QWidget()
        tabs_widget.setLayout(tabs_layout)

        bottom_widget = QWidget()
        bottom_widget.setLayout(bottom_layout)

        self.window.ui.splitters['tool.indexer'] = QSplitter(Qt.Vertical)
        self.window.ui.splitters['tool.indexer'].addWidget(tabs_widget)
        self.window.ui.splitters['tool.indexer'].addWidget(bottom_widget)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.splitters['tool.indexer'])
        layout.setContentsMargins(0, 0, 0, 0)

        # add dialog to the window - static dialog
        self.window.ui.dialog['tool.indexer'] = IndexerDialog(self.window)
        self.window.ui.dialog['tool.indexer'].setLayout(layout)
        self.window.ui.dialog['tool.indexer'].setWindowTitle(trans("tool.indexer.title"))

    def hook_idx_change(self, key, value, caller, *args, **kwargs):
        """
        Hook: on loader change

        :param key: Option key
        :param value: Option value
        :param caller: Caller
        :param args: Args
        :param kwargs: Kwargs
        """
        self.window.tools.get("indexer").set_current_idx(value, check=False)

class IndexerDialog(BaseDialog):
    def __init__(self, window=None):
        """
        Example dialog

        :param window: main window
        """
        super(IndexerDialog, self).__init__(window)
        self.window = window

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.cleanup()
        super(IndexerDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()  # close dialog when the Esc key is pressed.
        else:
            super(IndexerDialog, self).keyPressEvent(event)

    def cleanup(self):
        """Cleanup on dialog close"""
        self.window.tools.get("indexer").on_close()