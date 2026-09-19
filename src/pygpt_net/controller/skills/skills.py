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

import os

from PySide6.QtCore import Qt, QThreadPool, QUrl, Slot
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QTreeWidgetItem

from pygpt_net.utils import trans

from .worker import SkillsWorker


class Skills:
    def __init__(self, window=None):
        self.window = window
        self._workers = set()
        self._refreshing = False
        self._catalog = []

    def setup(self):
        self.window.ui.dialogs.skills.setup()
        tree = self.window.ui.nodes["skills.installed.list"]
        tree.itemChanged.connect(self._on_enabled_changed)
        self.refresh_installed()
        self.window.ui.nodes["skills.catalog.url"].setText(self.window.core.skills.get_catalog_url())

    def reload(self):
        self.window.core.skills.invalidate()
        if "skills.catalog.url" in self.window.ui.nodes:
            self.window.ui.nodes["skills.catalog.url"].setText(self.window.core.skills.get_catalog_url())
        self.refresh_installed()

    def open(self, explore: bool = False):
        dialog = self.window.ui.dialog.get("skills")
        if dialog is None:
            return
        tabs = self.window.ui.nodes.get("skills.tabs")
        if tabs is not None:
            tabs.setCurrentIndex(1 if explore else 0)
        self.refresh_installed()
        dialog.resize(980, 650)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        if explore:
            self.refresh_catalog()

    def refresh_installed(self):
        tree = self.window.ui.nodes.get("skills.installed.list")
        if tree is None:
            return
        self._refreshing = True
        try:
            tree.clear()
            for skill in self.window.core.skills.list_installed(force=True):
                item = QTreeWidgetItem(tree)
                item.setText(0, skill.get("display_name") or skill["name"])
                item.setText(1, skill.get("description", ""))
                item.setText(2, skill.get("standard", "agent-skills"))
                source = skill.get("source", "local")
                if skill.get("issues"):
                    source += " ⚠"
                    item.setToolTip(0, "\n".join(skill["issues"]))
                item.setText(3, source)
                item.setData(0, Qt.ItemDataRole.UserRole, skill["name"])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    0,
                    Qt.CheckState.Checked if skill.get("enabled") else Qt.CheckState.Unchecked,
                )
                icon_path = skill.get("icon_path")
                if icon_path and os.path.isfile(icon_path):
                    item.setIcon(0, QIcon(icon_path))
            tree.resizeColumnToContents(0)
            tree.resizeColumnToContents(2)
            tree.resizeColumnToContents(3)
            self._update_installed_status()
        finally:
            self._refreshing = False

    def _update_installed_status(self):
        node = self.window.ui.nodes.get("skills.installed.status")
        if node is None:
            return
        skills = self.window.core.skills.list_installed()
        enabled = sum(1 for item in skills if item.get("enabled"))
        node.setText(trans("skills.status.installed").format(total=len(skills), enabled=enabled))

    @Slot(QTreeWidgetItem, int)
    def _on_enabled_changed(self, item, column):
        if self._refreshing or column != 0:
            return
        name = item.data(0, Qt.ItemDataRole.UserRole)
        if not name:
            return
        enabled = item.checkState(0) == Qt.CheckState.Checked
        self.window.core.skills.set_enabled(str(name), enabled)
        self._update_installed_status()

    def import_github(self):
        value, ok = QInputDialog.getText(
            self.window,
            trans("skills.import.github"),
            trans("skills.import.github.prompt"),
        )
        if not ok or not str(value).strip():
            return
        self._start_worker("import_github", url=str(value).strip(), enable=True)

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            trans("skills.import.local"),
            self.window.core.config.get_last_used_dir(),
            trans("skills.import.filter"),
        )
        if not path:
            return
        self.window.core.config.set_last_used_dir(os.path.dirname(path))
        self._start_worker("import_local", path=path, enable=True)

    def import_folder(self):
        path = QFileDialog.getExistingDirectory(
            self.window,
            trans("skills.import.folder"),
            self.window.core.config.get_last_used_dir(),
        )
        if not path:
            return
        self.window.core.config.set_last_used_dir(path)
        self._start_worker("import_local", path=path, enable=True)

    def remove_selected(self):
        tree = self.window.ui.nodes.get("skills.installed.list")
        if tree is None or tree.currentItem() is None:
            return
        item = tree.currentItem()
        name = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        if not name:
            return
        answer = QMessageBox.question(
            self.window,
            trans("skills.remove"),
            trans("skills.remove.confirm").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.window.core.skills.remove(name)
            self.refresh_installed()
            self._set_status(trans("skills.status.removed").format(name=name))
        except Exception as exc:
            self.window.ui.dialogs.alert(str(exc))

    def open_directory(self):
        path = self.window.core.skills.get_root_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def refresh_catalog(self):
        url_node = self.window.ui.nodes.get("skills.catalog.url")
        url = str(url_node.text() if url_node is not None else "").strip()
        if url:
            self.window.core.skills.set_catalog_url(url)
        self._start_worker("catalog", url=url or self.window.core.skills.get_catalog_url())

    def install_selected(self):
        tree = self.window.ui.nodes.get("skills.explore.list")
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
                continue
        if not entries:
            return
        # Install checked entries serially inside one worker. Registry updates
        # must not race when several skills are selected at once.
        self._start_worker("install_catalog_many", entries=entries, enable=True)

    def _render_catalog(self, entries):
        self._catalog = list(entries or [])
        tree = self.window.ui.nodes.get("skills.explore.list")
        if tree is None:
            return
        tree.clear()
        installed = {x["name"] for x in self.window.core.skills.list_installed()}
        for idx, entry in enumerate(self._catalog):
            item = QTreeWidgetItem(tree)
            is_installed = entry.get("name") in installed
            if not is_installed:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Unchecked)
            item.setData(0, Qt.ItemDataRole.UserRole, idx)

            name = str(entry.get("display_name") or entry.get("name") or "")
            if is_installed:
                name += " ✓"
            item.setText(1, name)
            item.setText(2, str(entry.get("description") or ""))
            item.setText(3, str(entry.get("author") or entry.get("publisher") or ""))
            item.setText(4, str(entry.get("standard") or "Agent Skills"))
            raw_icon = entry.get("_icon_bytes")
            if raw_icon:
                pixmap = QPixmap()
                if pixmap.loadFromData(raw_icon):
                    item.setIcon(1, QIcon(pixmap))
            homepage = str(entry.get("homepage") or entry.get("url") or "")
            if homepage:
                item.setToolTip(1, homepage)
        tree.resizeColumnToContents(0)
        tree.resizeColumnToContents(1)
        tree.resizeColumnToContents(3)
        tree.resizeColumnToContents(4)
        node = self.window.ui.nodes.get("skills.explore.status")
        if node is not None:
            node.setText(trans("skills.status.catalog").format(total=len(self._catalog)))

    def _start_worker(self, action: str, **kwargs):
        worker = SkillsWorker(self.window, action, **kwargs)
        self._workers.add(worker)
        worker.signals.status.connect(self._set_status)
        worker.signals.finished.connect(lambda a, r, w=worker: self._on_worker_finished(w, a, r))
        worker.signals.error.connect(lambda a, e, w=worker: self._on_worker_error(w, a, e))
        QThreadPool.globalInstance().start(worker)

    @Slot(str)
    def _set_status(self, text: str):
        for key in ("skills.installed.status", "skills.explore.status"):
            node = self.window.ui.nodes.get(key)
            if node is not None:
                node.setText(str(text or ""))

    def _on_worker_finished(self, worker, action: str, result):
        self._workers.discard(worker)
        if action == "catalog":
            self._render_catalog(result)
            return
        self.refresh_installed()
        if action == "install_catalog_many":
            # Rebuild Explore from the cached catalog so newly installed rows get
            # their checkboxes cleared and are marked as already installed.
            self._render_catalog(self._catalog)
        names = [str(item.get("name")) for item in (result or []) if isinstance(item, dict)]
        if names:
            self._set_status(trans("skills.status.imported").format(names=", ".join(names)))
        else:
            self._set_status(trans("skills.status.ready"))

    def _on_worker_error(self, worker, action: str, error):
        self._workers.discard(worker)
        self._set_status(trans("skills.status.error").format(error=error))
        self.window.ui.dialogs.alert(str(error))
