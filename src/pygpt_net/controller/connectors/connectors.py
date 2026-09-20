#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 17:36:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QThreadPool, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMenu, QMessageBox, QTreeWidgetItem

from pygpt_net.utils import trans
from .worker import ConnectorsWorker


class Connectors:
    def __init__(self, window=None):
        self.window = window
        self._workers = set()
        self._refreshing = False
        self._catalog = []
        self._status_state = {"installed": None, "explore": None}

    def setup(self):
        self.window.ui.dialogs.connectors.setup()
        tree = self.window.ui.nodes["connectors.installed.list"]
        tree.itemChanged.connect(self._on_active_changed)
        tree.itemDoubleClicked.connect(lambda item, _col: self.edit_selected())
        explore_tree = self.window.ui.nodes["connectors.explore.list"]
        explore_tree.itemChanged.connect(self._update_install_button)
        explore_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        explore_tree.customContextMenuRequested.connect(self.show_explore_context_menu)
        self.window.ui.nodes["connectors.catalog.url"].setText(
            self.window.core.connectors.get_catalog_url()
        )
        self.refresh_installed()
        self._update_install_button()

    def reload(self):
        if "connectors.catalog.url" in self.window.ui.nodes:
            self.window.ui.nodes["connectors.catalog.url"].setText(
                self.window.core.connectors.get_catalog_url()
            )
        self.refresh_installed()

    def open(self, explore: bool = False):
        dialog = self.window.ui.dialog.get("connectors")
        if dialog is None:
            return
        tabs = self.window.ui.nodes.get("connectors.tabs")
        if tabs is not None:
            tabs.setCurrentIndex(1 if explore else 0)
        self.refresh_installed()
        dialog.resize(1040, 680)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        if explore:
            self.refresh_catalog()

    def refresh_installed(self):
        tree = self.window.ui.nodes.get("connectors.installed.list")
        if tree is None:
            return
        self._refreshing = True
        try:
            tree.clear()
            for idx, server in enumerate(self.window.core.connectors.get_servers()):
                item = QTreeWidgetItem(tree)
                item.setData(0, Qt.ItemDataRole.UserRole, idx)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Checked if server.get("active") else Qt.CheckState.Unchecked)
                item.setText(1, str(server.get("label") or ""))
                item.setText(2, self._display_transport(server))
                item.setText(3, str(server.get("server_address") or ""))
                item.setText(4, str(server.get("source") or "manual"))
                extra = str(server.get("extra") or "")
                if extra:
                    item.setToolTip(4, extra)
            for column in (0, 1, 2, 4):
                tree.resizeColumnToContents(column)
            self._set_status_key(
                "connectors.status.installed",
                targets=("installed",),
                total=tree.topLevelItemCount(),
            )
        finally:
            self._refreshing = False

    @staticmethod
    def _display_transport(server: dict) -> str:
        transport = str(server.get("transport") or "auto")
        if transport != "auto":
            return transport
        address = str(server.get("server_address") or "")
        if address.startswith("stdio:"):
            return "stdio"
        if "/sse" in address.lower() or address.lower().startswith("sse"):
            return "sse"
        return "http" if address.startswith(("http://", "https://")) else "auto"

    @Slot(QTreeWidgetItem, int)
    def _on_active_changed(self, item, column):
        if self._refreshing or column != 0:
            return
        idx = item.data(0, Qt.ItemDataRole.UserRole)
        if idx is None:
            return
        self.window.core.connectors.set_active(
            int(idx), item.checkState(0) == Qt.CheckState.Checked
        )

    def add_manual(self):
        server = {
            "active": False,
            "label": "connector",
            "server_address": "",
            "transport": "auto",
            "source": "manual",
        }
        value = self.window.ui.dialogs.connectors.edit_connector(server)
        if value is None:
            return
        self.window.core.connectors.add_servers([value])
        self.refresh_installed()

    def edit_selected(self):
        idx = self._selected_index()
        if idx is None:
            return
        self.edit_connector(idx)

    def edit_connector(self, idx: int):
        servers = self.window.core.connectors.get_servers()
        if idx < 0 or idx >= len(servers):
            return
        value = self.window.ui.dialogs.connectors.edit_connector(servers[idx])
        if value is None:
            return
        self.window.core.connectors.update_server(idx, value)
        self.refresh_installed()

    def remove_selected(self):
        idx = self._selected_index()
        if idx is None:
            return
        self.remove_connector(idx)

    def show_installed_context_menu(self, pos):
        tree = self.window.ui.nodes.get("connectors.installed.list")
        if tree is None:
            return
        item = tree.itemAt(pos)
        if item is None:
            return
        value = item.data(0, Qt.ItemDataRole.UserRole)
        if value is None:
            return
        idx = int(value)
        menu = QMenu(tree)
        edit_action = menu.addAction(QIcon(":/icons/edit.svg"), trans("action.edit"))
        remove_action = menu.addAction(QIcon(":/icons/delete.svg"), trans("connectors.remove"))
        selected = menu.exec(tree.viewport().mapToGlobal(pos))
        if selected == edit_action:
            self.edit_connector(idx)
        elif selected == remove_action:
            self.remove_connector(idx)

    def remove_connector(self, idx: int):
        servers = self.window.core.connectors.get_servers()
        if idx < 0 or idx >= len(servers):
            return
        label = str(servers[idx].get("label") or "connector")
        answer = QMessageBox.question(
            self.window,
            trans("connectors.remove"),
            trans("connectors.remove.confirm").format(name=label),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.window.core.connectors.remove_server(idx)
        self.refresh_installed()
        if self._catalog:
            self._render_catalog(self._catalog)

    def _selected_index(self):
        tree = self.window.ui.nodes.get("connectors.installed.list")
        if tree is None:
            return None
        item = tree.currentItem()
        if item is None:
            return None
        value = item.data(0, Qt.ItemDataRole.UserRole)
        return int(value) if value is not None else None

    def open_mcp_settings(self):
        self.window.controller.plugins.settings.open_plugin("mcp")

    def import_github(self):
        value, ok = QInputDialog.getText(
            self.window,
            trans("connectors.import.github"),
            trans("connectors.import.github.prompt"),
        )
        if ok and str(value).strip():
            self._start_worker("import_github", url=str(value).strip())

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            trans("connectors.import.file"),
            "",
            "MCP configs (*.json *.jsonc *.json5 *.toml *.yaml *.yml);;All files (*)",
        )
        if path:
            self._start_worker("import_local", path=path)

    def import_folder(self):
        path = QFileDialog.getExistingDirectory(self.window, trans("connectors.import.folder"))
        if path:
            self._start_worker("import_local", path=path)

    def refresh_catalog(self):
        node = self.window.ui.nodes.get("connectors.catalog.url")
        value = str(node.text() if node is not None else "").strip()
        self.window.core.connectors.set_catalog_url(value)
        self._start_worker("catalog", url=value or None)

    def show_explore_context_menu(self, pos):
        tree = self.window.ui.nodes.get("connectors.explore.list")
        if tree is None:
            return
        item = tree.itemAt(pos)
        if item is None:
            return
        idx = item.data(0, Qt.ItemDataRole.UserRole)
        try:
            entry = self._catalog[int(idx)]
        except (TypeError, ValueError, IndexError):
            return
        if self._is_catalog_entry_installed(entry):
            return
        menu = QMenu(tree)
        install_action = menu.addAction(QIcon(":/icons/download.svg"), trans("action.install"))
        selected = menu.exec(tree.viewport().mapToGlobal(pos))
        if selected == install_action:
            button = self.window.ui.nodes.get("connectors.explore.btn.install")
            if button is not None:
                button.setEnabled(False)
            self._start_worker("install_catalog_many", entries=[entry])

    def _installed_catalog_names(self):
        names = set()
        for server in self.window.core.connectors.get_servers():
            source = str(server.get("source") or "").strip()
            if source.lower().startswith("catalog:"):
                names.add(source.split(":", 1)[1].strip().lower())
        return names

    def _is_catalog_entry_installed(self, entry: dict, installed_names=None) -> bool:
        name = str(entry.get("name") or "").strip().lower()
        if not name:
            return False
        if installed_names is None:
            installed_names = self._installed_catalog_names()
        return name in installed_names

    def install_selected(self):
        tree = self.window.ui.nodes.get("connectors.explore.list")
        if tree is None:
            return
        entries = []
        for row in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(row)
            if item.checkState(0) != Qt.CheckState.Checked:
                continue
            idx = item.data(0, Qt.ItemDataRole.UserRole)
            if idx is not None and int(idx) < len(self._catalog):
                entries.append(self._catalog[int(idx)])
        if not entries:
            self._update_install_button()
            return
        button = self.window.ui.nodes.get("connectors.explore.btn.install")
        if button is not None:
            button.setEnabled(False)
        self._start_worker("install_catalog_many", entries=entries)

    @Slot(QTreeWidgetItem, int)
    def _update_install_button(self, *_args):
        tree = self.window.ui.nodes.get("connectors.explore.list")
        button = self.window.ui.nodes.get("connectors.explore.btn.install")
        if tree is None or button is None:
            return
        checked = any(
            tree.topLevelItem(row).checkState(0) == Qt.CheckState.Checked
            for row in range(tree.topLevelItemCount())
        )
        button.setEnabled(checked)

    def _render_catalog(self, entries):
        self._catalog = list(entries or [])
        tree = self.window.ui.nodes.get("connectors.explore.list")
        if tree is None:
            return
        tree.clear()
        installed_names = self._installed_catalog_names()
        for idx, entry in enumerate(self._catalog):
            item = QTreeWidgetItem(tree)
            item.setData(0, Qt.ItemDataRole.UserRole, idx)
            is_installed = self._is_catalog_entry_installed(entry, installed_names)
            if not is_installed:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Unchecked)
            item.setText(1, str(entry.get("display_name") or entry.get("name") or ""))
            item.setText(2, str(entry.get("description") or ""))
            item.setText(3, str(entry.get("publisher") or entry.get("author") or ""))
            item.setText(4, str(entry.get("homepage") or entry.get("github") or entry.get("url") or ""))
            if is_installed:
                item.setText(1, item.text(1) + " ✓")
        tree.resizeColumnToContents(0)
        tree.resizeColumnToContents(1)
        tree.resizeColumnToContents(3)
        tree.clearSelection()
        tree.setCurrentItem(None)
        self._update_install_button()
        self._set_status_key(
            "connectors.status.catalog",
            targets=("explore",),
            total=len(self._catalog),
        )

    def _start_worker(self, action: str, **kwargs):
        targets = self._status_targets_for_action(action)
        if action == "catalog":
            self._set_status_key(
                "connectors.status.loading_catalog",
                targets=targets,
            )
        elif action in ("import_github", "import_local"):
            self._set_status_key(
                "connectors.status.importing",
                targets=targets,
            )
        elif action == "install_catalog_many":
            total = max(1, len(list(kwargs.get("entries") or [])))
            self._set_status_key(
                "connectors.status.installing_n",
                targets=targets,
                current=1,
                total=total,
            )

        worker = ConnectorsWorker(self.window, action, **kwargs)
        self._workers.add(worker)
        worker.signals.status.connect(
            lambda text, a=action: self._set_status(
                text,
                targets=self._status_targets_for_action(a),
            )
        )
        worker.signals.finished.connect(lambda a, r, w=worker: self._on_worker_finished(w, a, r))
        worker.signals.error.connect(lambda a, e, w=worker: self._on_worker_error(w, a, e))
        QThreadPool.globalInstance().start(worker)

    @staticmethod
    def _status_targets_for_action(action: str):
        if action == "catalog":
            return ("explore",)
        if action in ("import_github", "import_local"):
            return ("installed",)
        if action == "install_catalog_many":
            return ("explore",)
        return ("installed", "explore")

    def _set_status(self, text: str, targets=("installed", "explore")):
        text = str(text or "")
        for target in targets:
            node = self.window.ui.nodes.get(f"connectors.{target}.status")
            if node is not None:
                node.setText(text)

    def _set_status_key(self, key: str, targets=("installed", "explore"), **kwargs):
        state = (str(key), dict(kwargs))
        text = trans(key).format(**kwargs)
        for target in targets:
            self._status_state[target] = state
            node = self.window.ui.nodes.get(f"connectors.{target}.status")
            if node is not None:
                node.setText(text)

    def retranslate_status(self):
        """Refresh persisted dialog status texts after a runtime locale change."""
        for target, state in self._status_state.items():
            if not state:
                continue
            key, kwargs = state
            node = self.window.ui.nodes.get(f"connectors.{target}.status")
            if node is not None:
                node.setText(trans(key).format(**kwargs))

    def _on_worker_finished(self, worker, action: str, result):
        self._workers.discard(worker)
        if action == "catalog":
            self._render_catalog(result)
            return
        self.refresh_installed()
        if action == "install_catalog_many":
            self._render_catalog(self._catalog)
        names = [str(item.get("label")) for item in (result or []) if isinstance(item, dict)]
        targets = self._status_targets_for_action(action)
        if names:
            self._set_status_key(
                "connectors.status.imported",
                targets=targets,
                names=", ".join(names),
            )
        else:
            self._set_status_key(
                "connectors.status.ready",
                targets=targets,
            )

    def _on_worker_error(self, worker, action: str, error):
        self._workers.discard(worker)
        if action == "install_catalog_many":
            self._update_install_button()
        self._set_status_key(
            "connectors.status.error",
            targets=self._status_targets_for_action(action),
            error=error,
        )
        self.window.ui.dialogs.alert(str(error))
