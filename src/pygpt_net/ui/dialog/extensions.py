#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.25 16:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QHeaderView, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QTreeWidget, QVBoxLayout, QWidget,
)

from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.utils import trans


class ExtensionsDialog(BaseDialog):
    pass


def _configure_tree(tree, widths):
    header = tree.header()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setStretchLastSection(True)
    tree.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    tree.setTextElideMode(Qt.TextElideMode.ElideRight)
    for col, width in widths.items():
        tree.setColumnWidth(col, width)


class Extensions:
    def __init__(self, window=None):
        self.window = window
        self.dialog_id = "extensions"

    def setup(self):
        nodes = self.window.ui.nodes
        info = QLabel(f'{trans("extensions.help")} {trans("extensions.warning")}')
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setContentsMargins(15, 5, 15, 5)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        nodes["extensions.info"] = info

        tabs = QTabWidget()
        nodes["extensions.tabs"] = tabs
        tabs.addTab(self._installed_tab(), trans("extensions.tab.installed"))
        tabs.addTab(self._explore_tab(), trans("extensions.tab.explore"))

        close_btn = QPushButton(trans("action.close"))
        close_btn.setAutoDefault(False)
        close_btn.clicked.connect(lambda: self.window.ui.dialog[self.dialog_id].close())
        nodes["extensions.btn.close"] = close_btn
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.addWidget(tabs, 1)
        layout.addWidget(info)
        layout.addLayout(footer)

        dialog = ExtensionsDialog(self.window, self.dialog_id)
        dialog.setLayout(layout)
        dialog.setWindowTitle(f'{trans("extensions.title")} (beta)')
        dialog.setMinimumSize(900, 560)
        self.window.ui.dialog[self.dialog_id] = dialog

    def _installed_tab(self):
        nodes = self.window.ui.nodes
        tab = QWidget()
        tree = QTreeWidget()
        tree.setColumnCount(7)
        tree.setHeaderLabels([
            trans("extensions.column.name"), trans("extensions.column.description"),
            trans("extensions.column.author"), trans("extensions.column.version"),
            trans("extensions.column.type"), trans("extensions.column.trusted"),
            trans("extensions.column.official"),
        ])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.window.controller.extensions.show_installed_context_menu)
        _configure_tree(tree, {0: 190, 1: 430, 2: 180, 3: 90, 4: 130, 5: 80, 6: 80})
        nodes["extensions.installed.list"] = tree

        btn_zip = QPushButton(QIcon(":/icons/folder_open.svg"), trans("extensions.import.zip"))
        btn_dir = QPushButton(QIcon(":/icons/folder.svg"), trans("extensions.import.directory"))
        btn_git = QPushButton(QIcon(":/icons/download.svg"), trans("extensions.import.github"))
        btn_open = QPushButton(QIcon(":/icons/folder_open.svg"), trans("extensions.open_dir"))
        btn_refresh = QPushButton(QIcon(":/icons/reload.svg"), trans("action.refresh"))
        btn_zip.clicked.connect(self.window.controller.extensions.import_zip)
        btn_dir.clicked.connect(self.window.controller.extensions.import_directory)
        btn_git.clicked.connect(self.window.controller.extensions.import_github)
        btn_open.clicked.connect(self.window.controller.extensions.open_directory)
        btn_refresh.clicked.connect(self.window.controller.extensions.refresh_installed)
        for key, btn in {
            "extensions.installed.btn.zip": btn_zip,
            "extensions.installed.btn.directory": btn_dir,
            "extensions.installed.btn.github": btn_git,
            "extensions.installed.btn.open": btn_open,
            "extensions.installed.btn.refresh": btn_refresh,
        }.items():
            btn.setAutoDefault(False); nodes[key] = btn
        buttons = QHBoxLayout()
        buttons.addWidget(btn_zip); buttons.addWidget(btn_dir); buttons.addWidget(btn_git)
        buttons.addStretch(1); buttons.addWidget(btn_open); buttons.addWidget(btn_refresh)
        status = QLabel(""); status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nodes["extensions.installed.status"] = status
        layout = QVBoxLayout(tab); layout.addWidget(tree, 1); layout.addLayout(buttons); layout.addWidget(status)
        return tab

    def _explore_tab(self):
        nodes = self.window.ui.nodes
        tab = QWidget()
        label = QLabel(trans("extensions.registry.url"))
        url = QLineEdit(); url.setPlaceholderText(trans("extensions.registry.url.placeholder"))
        refresh = QPushButton(QIcon(":/icons/reload.svg"), trans("action.refresh"))
        refresh.setAutoDefault(False)
        refresh.clicked.connect(self.window.controller.extensions.refresh_registry)
        nodes["extensions.registry.label"] = label
        nodes["extensions.registry.url"] = url
        nodes["extensions.registry.btn.refresh"] = refresh
        top = QHBoxLayout(); top.addWidget(label); top.addWidget(url, 1); top.addWidget(refresh)

        tree = QTreeWidget(); tree.setColumnCount(9)
        tree.setHeaderLabels([
            "", trans("extensions.column.name"), trans("extensions.column.description"),
            trans("extensions.column.author"), trans("extensions.column.version"),
            trans("extensions.column.type"), trans("extensions.column.trusted"),
            trans("extensions.column.official"), trans("extensions.column.source"),
        ])
        tree.setRootIsDecorated(False); tree.setAlternatingRowColors(True)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        _configure_tree(tree, {0: 28, 1: 190, 2: 390, 3: 160, 4: 85, 5: 120, 6: 75, 7: 75, 8: 350})
        nodes["extensions.explore.list"] = tree
        install = QPushButton(QIcon(":/icons/download.svg"), trans("extensions.install_update"))
        install.setAutoDefault(False); install.setEnabled(False)
        install.clicked.connect(self.window.controller.extensions.install_selected)
        nodes["extensions.explore.btn.install"] = install
        bottom = QHBoxLayout(); bottom.addStretch(1); bottom.addWidget(install)
        status = QLabel(""); status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nodes["extensions.explore.status"] = status
        layout = QVBoxLayout(tab); layout.addLayout(top); layout.addWidget(tree, 1); layout.addWidget(status); layout.addLayout(bottom)
        return tab
