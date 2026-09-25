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

import os

from PySide6.QtCore import Qt, QThreadPool, QUrl, Slot
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMenu, QMessageBox, QTreeWidgetItem

from pygpt_net.utils import trans
from .worker import ExtensionsWorker


class Extensions:
    def __init__(self, window=None):
        self.window = window
        self._workers = set()
        self._catalog = []
        self._explore_auto_loaded = False

    def setup(self):
        self.window.ui.dialogs.extensions.setup()
        tree = self.window.ui.nodes["extensions.explore.list"]
        tree.itemChanged.connect(self._update_install_button)
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.show_explore_context_menu)
        self.window.ui.nodes["extensions.tabs"].currentChanged.connect(self._on_tab_changed)
        self.window.ui.nodes["extensions.registry.url"].setText(
            self.window.core.extensions.get_registry_url()
        )
        self.refresh_installed()
        self._update_install_button()

    def reload(self):
        self._explore_auto_loaded = False
        # Static theme/locale packages can follow a profile switch immediately.
        # Python runtime add-ons remain process-scoped and require restart.
        self.window.core.extensions.sync_static_extensions()
        if "extensions.registry.url" in self.window.ui.nodes:
            self.window.ui.nodes["extensions.registry.url"].setText(
                self.window.core.extensions.get_registry_url()
            )
        self.refresh_installed()

    def open(self, explore: bool = False):
        dialog = self.window.ui.dialog.get("extensions")
        if dialog is None:
            return
        tabs = self.window.ui.nodes.get("extensions.tabs")
        if tabs is not None:
            tabs.setCurrentIndex(1 if explore else 0)
            self._on_tab_changed(tabs.currentIndex())
        self.refresh_installed()
        dialog.resize(1120, 700)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def refresh_installed(self):
        tree = self.window.ui.nodes.get("extensions.installed.list")
        if tree is None:
            return
        tree.clear()
        items = self.window.core.extensions.list_installed()
        for ext in items:
            item = QTreeWidgetItem(tree)
            item.setData(0, Qt.ItemDataRole.UserRole, ext.get("id"))
            item.setText(0, str(ext.get("name") or ext.get("id") or ""))
            item.setText(1, str(ext.get("description") or ""))
            item.setText(2, str(ext.get("author") or ""))
            item.setText(3, str(ext.get("version") or ""))
            item.setText(4, str(ext.get("type") or ""))
            item.setText(5, trans("extensions.yes") if ext.get("trusted") else trans("extensions.no"))
            item.setText(6, trans("extensions.yes") if ext.get("official") else trans("extensions.no"))
            if not ext.get("_compatible", True):
                item.setToolTip(0, trans("extensions.incompatible").format(version=ext.get("min_app_version")))
        status = self.window.ui.nodes.get("extensions.installed.status")
        if status is not None:
            status.setText(trans("extensions.status.installed").format(total=len(items)))

    def import_zip(self):
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            trans("extensions.import.zip"),
            self.window.core.config.get_last_used_dir(),
            trans("extensions.import.zip.filter"),
        )
        if not path:
            return
        self.window.core.config.set_last_used_dir(os.path.dirname(path))
        self._start_worker("import_zip", path=path)

    def import_directory(self):
        path = QFileDialog.getExistingDirectory(
            self.window,
            trans("extensions.import.directory"),
            self.window.core.config.get_last_used_dir(),
        )
        if not path:
            return
        self.window.core.config.set_last_used_dir(path)
        self._start_worker("import_directory", path=path)

    def import_github(self):
        value, ok = QInputDialog.getText(
            self.window,
            trans("extensions.import.github"),
            trans("extensions.import.github.prompt"),
        )
        if not ok or not str(value).strip():
            return
        self._start_worker("import_github", url=str(value).strip())

    def open_directory(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.window.core.extensions.get_root_dir()))

    def show_installed_context_menu(self, pos):
        tree = self.window.ui.nodes.get("extensions.installed.list")
        if tree is None:
            return
        item = tree.itemAt(pos)
        if item is None:
            return
        ext_id = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        if not ext_id:
            return
        menu = QMenu(tree)
        remove = menu.addAction(QIcon(":/icons/delete.svg"), trans("extensions.uninstall"))
        chosen = menu.exec(tree.viewport().mapToGlobal(pos))
        if chosen == remove:
            self.uninstall(ext_id, item.text(0) or ext_id)

    def uninstall(self, ext_id: str, name: str):
        answer = QMessageBox.question(
            self.window,
            trans("extensions.uninstall"),
            trans("extensions.uninstall.confirm").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.window.core.extensions.uninstall(ext_id)
            self.refresh_installed()
            self._render_registry(self._catalog)
            self._set_status(trans("extensions.status.uninstalled").format(name=name))
            QMessageBox.information(
                self.window,
                trans("extensions.title"),
                trans("extensions.restart_required"),
            )
        except Exception as exc:
            self.window.ui.dialogs.alert(str(exc))

    def _on_tab_changed(self, index: int):
        if int(index) != 1 or self._explore_auto_loaded:
            return
        if self._load_registry(show_error_dialog=False):
            self._explore_auto_loaded = True

    def refresh_registry(self):
        return self._load_registry(show_error_dialog=True)

    def _load_registry(self, show_error_dialog: bool):
        node = self.window.ui.nodes.get("extensions.registry.url")
        url = str(node.text() if node else "").strip()
        if url:
            self.window.core.extensions.set_registry_url(url)
        return self._start_worker(
            "registry",
            url=url or None,
            show_error_dialog=show_error_dialog,
        )

    def show_explore_context_menu(self, pos):
        tree = self.window.ui.nodes.get("extensions.explore.list")
        if tree is None or self._workers:
            return
        item = tree.itemAt(pos)
        if item is None:
            return
        idx = item.data(0, Qt.ItemDataRole.UserRole)
        try:
            entry = self._catalog[int(idx)]
        except (TypeError, ValueError, IndexError):
            return
        ext_id = str(entry.get("id") or "").strip()
        if not ext_id:
            return

        menu = QMenu(tree)
        installed = ext_id in self.window.core.extensions.get_installed_versions()
        if installed:
            action = menu.addAction(QIcon(":/icons/delete.svg"), trans("extensions.uninstall"))
        else:
            action = menu.addAction(QIcon(":/icons/download.svg"), trans("action.install"))

        selected = menu.exec(tree.viewport().mapToGlobal(pos))
        if selected != action:
            return
        if installed:
            self.uninstall(ext_id, str(entry.get("name") or ext_id))
        else:
            self._install_registry_entry(entry)

    def _install_registry_entry(self, entry):
        if not isinstance(entry, dict) or self._workers:
            return
        button = self.window.ui.nodes.get("extensions.explore.btn.install")
        if button is not None:
            button.setEnabled(False)
        self._start_worker("install_registry_many", entries=[entry])

    def install_selected(self):
        tree = self.window.ui.nodes.get("extensions.explore.list")
        if tree is None:
            return
        entries = []
        for row in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(row)
            if item.checkState(0) != Qt.CheckState.Checked:
                continue
            idx = item.data(0, Qt.ItemDataRole.UserRole)
            try:
                entries.append(self._catalog[int(idx)])
            except (TypeError, ValueError, IndexError):
                pass
        if entries:
            button = self.window.ui.nodes.get("extensions.explore.btn.install")
            if button is not None:
                button.setEnabled(False)
            self._start_worker("install_registry_many", entries=entries)
        else:
            self._update_install_button()

    @Slot(QTreeWidgetItem, int)
    def _update_install_button(self, *_args):
        tree = self.window.ui.nodes.get("extensions.explore.list")
        button = self.window.ui.nodes.get("extensions.explore.btn.install")
        if tree is None or button is None:
            return
        if self._workers:
            button.setEnabled(False)
            return
        button.setEnabled(any(
            tree.topLevelItem(row).checkState(0) == Qt.CheckState.Checked
            for row in range(tree.topLevelItemCount())
        ))

    def _render_registry(self, entries):
        self._catalog = list(entries or [])
        tree = self.window.ui.nodes.get("extensions.explore.list")
        if tree is None:
            return
        tree.blockSignals(True)
        try:
            tree.clear()
            installed_versions = self.window.core.extensions.get_installed_versions()
            for idx, ext in enumerate(self._catalog):
                item = QTreeWidgetItem(tree)
                ext_id = str(ext.get("id") or "")
                installed_version = installed_versions.get(ext_id)
                is_installed = installed_version is not None
                update_available = (
                    is_installed
                    and self.window.core.extensions.is_newer_version(
                        str(ext.get("version") or ""),
                        installed_version,
                    )
                )
                if not is_installed or update_available:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.CheckState.Unchecked)
                item.setData(0, Qt.ItemDataRole.UserRole, idx)
                name = str(ext.get("name") or ext_id)
                if update_available:
                    name += " ↑"
                elif is_installed:
                    name += " ✓"
                item.setText(1, name)
                item.setText(2, str(ext.get("description") or ""))
                item.setText(3, str(ext.get("author") or ""))
                item.setText(4, str(ext.get("version") or ""))
                item.setText(5, str(ext.get("type") or ""))
                item.setText(6, trans("extensions.yes") if ext.get("trusted") else trans("extensions.no"))
                item.setText(7, trans("extensions.yes") if ext.get("official") else trans("extensions.no"))
                path = str(ext.get("github_path") or ext.get("path") or "")
                source = str(ext.get("github_url") or ext.get("url") or "")
                if not source and path:
                    source = self.window.core.extensions.DEFAULT_REGISTRY_REPOSITORY
                item.setText(8, source + ((" :: " + path) if path else ""))
        finally:
            tree.blockSignals(False)
        self._update_install_button()
        node = self.window.ui.nodes.get("extensions.explore.status")
        if node is not None:
            node.setText(trans("extensions.status.registry").format(total=len(self._catalog)))

    def _start_worker(self, action: str, show_error_dialog: bool = True, **kwargs):
        # Installation mutates one profile-scoped add-ons tree and registry.
        # Serialize all extension workers so two imports/refreshes cannot race on
        # the same files or .registry.json.
        if self._workers:
            return False
        worker = ExtensionsWorker(self.window, action, **kwargs)
        self._workers.add(worker)
        self._set_busy(True)
        worker.signals.status.connect(self._set_status)
        worker.signals.finished.connect(lambda a, r, w=worker: self._on_finished(w, a, r))
        worker.signals.error.connect(
            lambda a, e, w=worker, show=show_error_dialog: self._on_error(w, a, e, show)
        )
        QThreadPool.globalInstance().start(worker)
        return True

    def _set_busy(self, busy: bool):
        for key in (
            "extensions.installed.btn.zip",
            "extensions.installed.btn.directory",
            "extensions.installed.btn.github",
            "extensions.registry.btn.refresh",
        ):
            node = self.window.ui.nodes.get(key)
            if node is not None:
                node.setEnabled(not busy)
        url = self.window.ui.nodes.get("extensions.registry.url")
        if url is not None:
            url.setEnabled(not busy)
        if busy:
            button = self.window.ui.nodes.get("extensions.explore.btn.install")
            if button is not None:
                button.setEnabled(False)
        else:
            self._update_install_button()

    @Slot(str)
    def _set_status(self, text: str):
        for key in ("extensions.installed.status", "extensions.explore.status"):
            node = self.window.ui.nodes.get(key)
            if node is not None:
                node.setText(str(text or ""))

    def _on_finished(self, worker, action, result):
        self._workers.discard(worker)
        self._set_busy(bool(self._workers))
        if action == "registry":
            self._render_registry(result)
            return
        self.refresh_installed()
        self._render_registry(self._catalog)
        if isinstance(result, dict):
            names = [str(result.get("name") or result.get("id") or "")]
        elif isinstance(result, list):
            names = [
                str(item.get("name") or item.get("id") or "")
                for item in result if isinstance(item, dict)
            ]
        else:
            names = []
        names = [name for name in names if name]
        self._set_status(trans("extensions.status.imported").format(name=", ".join(names)))
        QMessageBox.information(
            self.window,
            trans("extensions.title"),
            f'{trans("extensions.status.imported").format(name=", ".join(names))}\n\n'
            f'{trans("extensions.restart_required")}',
        )

    def _on_error(self, worker, action, error, show_error_dialog: bool = True):
        self._workers.discard(worker)
        self._set_busy(bool(self._workers))
        if action != "registry":
            # A multi-install can fail after earlier entries were already committed.
            # Re-read disk state so Installed/Explore never show stale data.
            self.refresh_installed()
            self._render_registry(self._catalog)
        self._update_install_button()
        self._set_status(trans("extensions.status.error").format(error=error))
        if action != "registry" or show_error_dialog:
            self.window.ui.dialogs.alert(str(error))
