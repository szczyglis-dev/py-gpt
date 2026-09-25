#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 17:20:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.utils import trans


class ConnectorsDialog(BaseDialog):
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


class ConnectorEditDialog(QDialog):
    def __init__(self, parent, server: dict):
        super().__init__(parent)
        self.server = dict(server or {})
        self.setWindowTitle(trans("connectors.editor.title"))
        self.setMinimumSize(720, 620)

        self.label = QLineEdit(str(self.server.get("label") or ""))
        self.address = QLineEdit(str(self.server.get("server_address") or ""))
        self.transport = QComboBox()
        self.transport.addItems(["auto", "stdio", "http", "sse"])
        current_transport = str(self.server.get("transport") or "auto")
        idx = self.transport.findText(current_transport)
        self.transport.setCurrentIndex(max(0, idx))
        self.authorization = QLineEdit(str(self.server.get("authorization") or ""))
        self.authorization.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        self.allowed = QLineEdit(str(self.server.get("allowed_commands") or ""))
        self.disabled = QLineEdit(str(self.server.get("disabled_commands") or ""))
        self.cwd = QLineEdit(str(self.server.get("cwd") or ""))
        self.bearer = QLineEdit(str(self.server.get("bearer_token_env_var") or ""))
        self.startup_timeout = QLineEdit(str(self.server.get("startup_timeout_sec") or ""))
        self.tool_timeout = QLineEdit(str(self.server.get("tool_timeout_sec") or ""))
        self.source = QLineEdit(str(self.server.get("source") or "manual"))

        self.env = QTextEdit(str(self.server.get("env") or ""))
        self.headers = QTextEdit(str(self.server.get("headers") or ""))
        self.env_headers = QTextEdit(str(self.server.get("env_http_headers") or ""))
        self.extra = QTextEdit(str(self.server.get("extra") or ""))
        for widget in (self.env, self.headers, self.env_headers, self.extra):
            widget.setAcceptRichText(False)
            widget.setMaximumHeight(90)

        form = QFormLayout()
        form.addRow(trans("connectors.field.name"), self.label)
        form.addRow(trans("connectors.field.address"), self.address)
        form.addRow(trans("connectors.field.transport"), self.transport)
        form.addRow(trans("connectors.field.authorization"), self.authorization)
        form.addRow(trans("connectors.field.env"), self.env)
        form.addRow(trans("connectors.field.headers"), self.headers)
        form.addRow(trans("connectors.field.env_headers"), self.env_headers)
        form.addRow(trans("connectors.field.bearer_env"), self.bearer)
        form.addRow(trans("connectors.field.cwd"), self.cwd)
        form.addRow(trans("connectors.field.allowed"), self.allowed)
        form.addRow(trans("connectors.field.disabled"), self.disabled)
        form.addRow(trans("connectors.field.startup_timeout"), self.startup_timeout)
        form.addRow(trans("connectors.field.tool_timeout"), self.tool_timeout)
        form.addRow(trans("connectors.field.source"), self.source)
        form.addRow(trans("connectors.field.extra"), self.extra)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form, 1)
        layout.addWidget(buttons)

    def value(self) -> dict:
        value = dict(self.server)
        value.update({
            "label": self.label.text().strip() or "connector",
            "server_address": self.address.text().strip(),
            "transport": self.transport.currentText(),
            "authorization": self.authorization.text().strip(),
            "env": self.env.toPlainText().strip(),
            "headers": self.headers.toPlainText().strip(),
            "env_http_headers": self.env_headers.toPlainText().strip(),
            "bearer_token_env_var": self.bearer.text().strip(),
            "cwd": self.cwd.text().strip(),
            "allowed_commands": self.allowed.text().strip(),
            "disabled_commands": self.disabled.text().strip(),
            "startup_timeout_sec": self.startup_timeout.text().strip(),
            "tool_timeout_sec": self.tool_timeout.text().strip(),
            "source": self.source.text().strip() or "manual",
            "extra": self.extra.toPlainText().strip(),
        })
        return value


class Connectors:
    def __init__(self, window=None):
        self.window = window
        self.dialog_id = "connectors"

    def setup(self):
        nodes = self.window.ui.nodes
        tabs = QTabWidget()
        nodes["connectors.tabs"] = tabs
        tabs.addTab(self._installed_tab(), trans("connectors.tab.installed"))
        tabs.addTab(self._explore_tab(), trans("connectors.tab.explore"))

        info = QLabel(trans("connectors.info"))
        info.setWordWrap(True)
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        nodes["connectors.info"] = info
        close_btn = QPushButton(trans("action.close"))
        close_btn.clicked.connect(lambda: self.window.ui.dialog[self.dialog_id].close())
        close_btn.setAutoDefault(False)
        nodes["connectors.btn.close"] = close_btn

        footer = QHBoxLayout()
        footer.addWidget(info, 1)
        footer.addWidget(close_btn)

        layout = QVBoxLayout()
        layout.addWidget(tabs, 1)
        layout.addLayout(footer)

        dialog = ConnectorsDialog(self.window, self.dialog_id)
        dialog.setLayout(layout)
        dialog.setWindowTitle(trans("connectors.title"))
        dialog.setMinimumSize(820, 520)
        self.window.ui.dialog[self.dialog_id] = dialog

    def edit_connector(self, server: dict):
        dialog = ConnectorEditDialog(self.window, server)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        value = dialog.value()
        if not value.get("server_address"):
            self.window.ui.dialogs.alert(trans("connectors.error.address_required"))
            return None
        return value

    def _installed_tab(self):
        nodes = self.window.ui.nodes
        tab = QWidget()
        tree = QTreeWidget()
        tree.setColumnCount(5)
        tree.setHeaderLabels([
            trans("connectors.column.active"),
            trans("connectors.column.name"),
            trans("connectors.column.transport"),
            trans("connectors.column.address"),
            trans("connectors.column.source"),
        ])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tree.setUniformRowHeights(True)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(
            self.window.controller.connectors.show_installed_context_menu
        )
        _configure_tree_columns(tree, {1: 170, 2: 100, 3: 440, 4: 260})
        nodes["connectors.installed.list"] = tree

        btn_github = QPushButton(QIcon(":/icons/download.svg"), trans("connectors.import.github"))
        btn_github.clicked.connect(self.window.controller.connectors.import_github)
        nodes["connectors.installed.btn.github"] = btn_github
        btn_file = QPushButton(QIcon(":/icons/upload.svg"), trans("connectors.import.file"))
        btn_file.clicked.connect(self.window.controller.connectors.import_file)
        nodes["connectors.installed.btn.file"] = btn_file
        btn_folder = QPushButton(QIcon(":/icons/add_folder.svg"), trans("connectors.import.folder"))
        btn_folder.clicked.connect(self.window.controller.connectors.import_folder)
        nodes["connectors.installed.btn.folder"] = btn_folder
        btn_add = QPushButton(QIcon(":/icons/add.svg"), trans("action.add"))
        btn_add.clicked.connect(self.window.controller.connectors.add_manual)
        nodes["connectors.installed.btn.add"] = btn_add
        btn_edit = QPushButton(QIcon(":/icons/edit.svg"), trans("action.edit"))
        btn_edit.clicked.connect(self.window.controller.connectors.edit_selected)
        nodes["connectors.installed.btn.edit"] = btn_edit
        btn_mcp = QPushButton(QIcon(":/icons/settings_filled.svg"), trans("connectors.mcp_settings"))
        btn_mcp.clicked.connect(self.window.controller.connectors.open_mcp_settings)
        nodes["connectors.installed.btn.mcp"] = btn_mcp
        for btn in (btn_github, btn_file, btn_folder, btn_add, btn_edit, btn_mcp):
            btn.setAutoDefault(False)

        buttons = QHBoxLayout()
        buttons.addWidget(btn_github)
        buttons.addWidget(btn_file)
        buttons.addWidget(btn_folder)
        buttons.addStretch(1)
        buttons.addWidget(btn_add)
        buttons.addWidget(btn_edit)
        buttons.addWidget(btn_mcp)

        status = QLabel("")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nodes["connectors.installed.status"] = status

        layout = QVBoxLayout(tab)
        layout.addWidget(tree, 1)
        layout.addLayout(buttons)
        layout.addWidget(status)
        return tab

    def _explore_tab(self):
        nodes = self.window.ui.nodes
        tab = QWidget()
        url = QLineEdit()
        url.setPlaceholderText(trans("connectors.catalog.url.placeholder"))
        url.returnPressed.connect(self.window.controller.connectors.refresh_catalog_silent)
        nodes["connectors.catalog.url"] = url
        refresh = QPushButton(QIcon(":/icons/reload.svg"), trans("action.refresh"))
        refresh.clicked.connect(self.window.controller.connectors.refresh_catalog)
        refresh.setAutoDefault(False)

        catalog_label = QLabel(trans("connectors.catalog.url"))
        nodes["connectors.catalog.label"] = catalog_label
        nodes["connectors.catalog.btn.refresh"] = refresh
        top = QHBoxLayout()
        top.addWidget(catalog_label)
        top.addWidget(url, 1)
        top.addWidget(refresh)

        tree = QTreeWidget()
        tree.setColumnCount(5)
        tree.setHeaderLabels([
            "",
            trans("connectors.column.name"),
            trans("connectors.column.description"),
            trans("connectors.column.publisher"),
            trans("connectors.column.source"),
        ])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        # Selection is visual only; installation is driven exclusively by the
        # checkbox in column 0. Start with no highlighted catalog row.
        tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tree.setUniformRowHeights(True)
        _configure_tree_columns(tree, {1: 170, 2: 430, 3: 180, 4: 340})
        nodes["connectors.explore.list"] = tree

        install = QPushButton(QIcon(":/icons/download.svg"), trans("connectors.install"))
        install.clicked.connect(self.window.controller.connectors.install_selected)
        install.setAutoDefault(False)
        install.setEnabled(False)
        nodes["connectors.explore.btn.install"] = install
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(install)

        status = QLabel("")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nodes["connectors.explore.status"] = status

        layout = QVBoxLayout(tab)
        layout.addLayout(top)
        layout.addWidget(tree, 1)
        layout.addWidget(status)
        layout.addLayout(bottom)
        return tab
