#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 14:00:00                  #
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
        tree.setColumnCount(4)
        tree.setHeaderLabels([
            trans("skills.column.name"),
            trans("skills.column.description"),
            trans("skills.column.standard"),
            trans("skills.column.source"),
        ])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tree.setUniformRowHeights(True)
        tree.header().setStretchLastSection(False)
        tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        nodes["skills.installed.list"] = tree

        btn_github = QPushButton(QIcon(":/icons/download.svg"), trans("skills.import.github"))
        btn_github.clicked.connect(self.window.controller.skills.import_github)
        btn_file = QPushButton(QIcon(":/icons/folder_open.svg"), trans("skills.import.file"))
        btn_file.clicked.connect(self.window.controller.skills.import_file)
        btn_folder = QPushButton(QIcon(":/icons/folder.svg"), trans("skills.import.folder"))
        btn_folder.clicked.connect(self.window.controller.skills.import_folder)
        btn_remove = QPushButton(QIcon(":/icons/delete.svg"), trans("skills.remove"))
        btn_remove.clicked.connect(self.window.controller.skills.remove_selected)
        btn_open = QPushButton(QIcon(":/icons/folder_open.svg"), trans("skills.open_dir"))
        btn_open.clicked.connect(self.window.controller.skills.open_directory)
        btn_refresh = QPushButton(QIcon(":/icons/reload.svg"), trans("action.refresh"))
        btn_refresh.clicked.connect(self.window.controller.skills.refresh_installed)
        for btn in (btn_github, btn_file, btn_folder, btn_remove, btn_open, btn_refresh):
            btn.setAutoDefault(False)

        buttons = QHBoxLayout()
        buttons.addWidget(btn_github)
        buttons.addWidget(btn_file)
        buttons.addWidget(btn_folder)
        buttons.addStretch(1)
        buttons.addWidget(btn_remove)
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
        url.returnPressed.connect(self.window.controller.skills.refresh_catalog)
        nodes["skills.catalog.url"] = url

        btn_refresh = QPushButton(QIcon(":/icons/reload.svg"), trans("skills.catalog.refresh"))
        btn_refresh.clicked.connect(self.window.controller.skills.refresh_catalog)
        btn_refresh.setAutoDefault(False)
        top = QHBoxLayout()
        top.addWidget(QLabel(trans("skills.catalog.url")))
        top.addWidget(url, 1)
        top.addWidget(btn_refresh)

        tree = QTreeWidget()
        tree.setColumnCount(5)
        tree.setHeaderLabels([
            "",
            trans("skills.column.name"),
            trans("skills.column.description"),
            trans("skills.column.author"),
            trans("skills.column.standard"),
        ])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        # Installation is controlled only by the explicit checkbox column.
        # Disable row selection so highlighted rows cannot be mistaken for the
        # set of skills that will be installed.
        tree.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        tree.setUniformRowHeights(True)
        tree.header().setStretchLastSection(False)
        tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        nodes["skills.explore.list"] = tree

        btn_install = QPushButton(QIcon(":/icons/download.svg"), trans("skills.install"))
        btn_install.clicked.connect(self.window.controller.skills.install_selected)
        btn_install.setAutoDefault(False)
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
