#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 17:40:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.utils import trans


class SkillsDialog(BaseDialog):
    pass


def _configure_tree_columns(tree: QTreeWidget, widths: dict[int, int]):
    """Configure catalog/list columns for manual resizing and horizontal scrolling."""
    header = tree.header()
    # Keep regular sections manually resizable, but let the real last column
    # (Source) consume any otherwise-empty header viewport on the right.
    # This removes the visual "blank column" while preserving horizontal
    # scrolling when the user widens the interactive sections.
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    header.setStretchLastSection(True)
    tree.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    tree.setTextElideMode(Qt.TextElideMode.ElideRight)
    for column, width in widths.items():
        tree.setColumnWidth(column, width)


class Skills:
    def __init__(self, window=None):
        self.window = window
        self.dialog_id = "skills"

    def setup(self):
        nodes = self.window.ui.nodes

        tabs = QTabWidget()
        nodes["skills.tabs"] = tabs
        tabs.addTab(self._installed_tab(), trans("skills.tab.installed"))
        tabs.addTab(self._explore_tab(), trans("skills.tab.explore"))

        info = QLabel(trans("skills.info"))
        info.setWordWrap(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        nodes["skills.info"] = info

        close_btn = QPushButton(trans("action.close"))
        close_btn.clicked.connect(lambda: self.window.ui.dialog[self.dialog_id].close())
        close_btn.setAutoDefault(False)
        nodes["skills.btn.close"] = close_btn

        footer = QHBoxLayout()
        footer.addWidget(info, 1)
        footer.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.addWidget(tabs, 1)
        layout.addLayout(footer)

        dialog = SkillsDialog(self.window, self.dialog_id)
        dialog.setLayout(layout)
        dialog.setWindowTitle(trans("skills.title"))
        dialog.setMinimumSize(760, 500)
        self.window.ui.dialog[self.dialog_id] = dialog

    def _installed_tab(self):
        nodes = self.window.ui.nodes
        tab = QWidget()

        tree = QTreeWidget()
        tree.setColumnCount(5)
        tree.setHeaderLabels([
            trans("skills.column.enabled"),
            trans("skills.column.name"),
            trans("skills.column.description"),
            trans("skills.column.standard"),
            trans("skills.column.source"),
        ])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tree.setUniformRowHeights(True)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(
            self.window.controller.skills.show_installed_context_menu
        )
        _configure_tree_columns(tree, {1: 190, 2: 430, 3: 150, 4: 300})
        nodes["skills.installed.list"] = tree

        btn_github = QPushButton(QIcon(":/icons/download.svg"), trans("skills.import.github"))
        btn_github.clicked.connect(self.window.controller.skills.import_github)
        nodes["skills.installed.btn.github"] = btn_github
        btn_file = QPushButton(QIcon(":/icons/folder_open.svg"), trans("skills.import.file"))
        btn_file.clicked.connect(self.window.controller.skills.import_file)
        nodes["skills.installed.btn.file"] = btn_file
        btn_folder = QPushButton(QIcon(":/icons/folder.svg"), trans("skills.import.folder"))
        btn_folder.clicked.connect(self.window.controller.skills.import_folder)
        nodes["skills.installed.btn.folder"] = btn_folder
        btn_open = QPushButton(QIcon(":/icons/folder_open.svg"), trans("skills.open_dir"))
        btn_open.clicked.connect(self.window.controller.skills.open_directory)
        nodes["skills.installed.btn.open"] = btn_open
        btn_refresh = QPushButton(QIcon(":/icons/reload.svg"), trans("action.refresh"))
        btn_refresh.clicked.connect(self.window.controller.skills.refresh_installed)
        nodes["skills.installed.btn.refresh"] = btn_refresh
        for btn in (btn_github, btn_file, btn_folder, btn_open, btn_refresh):
            btn.setAutoDefault(False)

        buttons = QHBoxLayout()
        buttons.addWidget(btn_github)
        buttons.addWidget(btn_file)
        buttons.addWidget(btn_folder)
        buttons.addStretch(1)
        buttons.addWidget(btn_open)
        buttons.addWidget(btn_refresh)

        status = QLabel("")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nodes["skills.installed.status"] = status

        layout = QVBoxLayout(tab)
        layout.addWidget(tree, 1)
        layout.addLayout(buttons)
        layout.addWidget(status)
        return tab

    def _explore_tab(self):
        nodes = self.window.ui.nodes
        tab = QWidget()

        url = QLineEdit()
        url.setPlaceholderText(trans("skills.catalog.url.placeholder"))
        url.returnPressed.connect(self.window.controller.skills.refresh_catalog_silent)
        nodes["skills.catalog.url"] = url

        btn_refresh = QPushButton(QIcon(":/icons/reload.svg"), trans("skills.catalog.refresh"))
        btn_refresh.clicked.connect(self.window.controller.skills.refresh_catalog)
        btn_refresh.setAutoDefault(False)
        catalog_label = QLabel(trans("skills.catalog.url"))
        nodes["skills.catalog.label"] = catalog_label
        nodes["skills.catalog.btn.refresh"] = btn_refresh
        top = QHBoxLayout()
        top.addWidget(catalog_label)
        top.addWidget(url, 1)
        top.addWidget(btn_refresh)

        tree = QTreeWidget()
        tree.setColumnCount(6)
        tree.setHeaderLabels([
            "",
            trans("skills.column.name"),
            trans("skills.column.description"),
            trans("skills.column.author"),
            trans("skills.column.standard"),
            trans("skills.column.source"),
        ])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        # Installation is controlled only by the explicit checkbox column.
        # A normal row click may highlight a row for navigation, but it never
        # changes which skills are selected for installation.
        tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tree.setUniformRowHeights(True)
        _configure_tree_columns(tree, {1: 190, 2: 450, 3: 180, 4: 160, 5: 320})
        nodes["skills.explore.list"] = tree

        btn_install = QPushButton(QIcon(":/icons/download.svg"), trans("skills.install"))
        btn_install.clicked.connect(self.window.controller.skills.install_selected)
        btn_install.setAutoDefault(False)
        btn_install.setEnabled(False)
        nodes["skills.explore.btn.install"] = btn_install
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(btn_install)

        status = QLabel("")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nodes["skills.explore.status"] = status

        layout = QVBoxLayout(tab)
        layout.addLayout(top)
        layout.addWidget(tree, 1)
        layout.addWidget(status)
        layout.addLayout(bottom)
        return tab
