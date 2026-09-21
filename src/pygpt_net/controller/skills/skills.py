#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.19 17:50:00                  #
# ================================================== #

import os

from PySide6.QtCore import Qt, QThreadPool, QUrl, Slot
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMenu, QMessageBox, QTreeWidgetItem

from pygpt_net.utils import trans

from .worker import SkillsWorker


class Skills:
    def __init__(self, window=None):
        self.window = window
        self._workers = set()
        self._refreshing = False
        self._catalog = []
        self._status_state = {"installed": None, "explore": None}

    def setup(self):
        self.window.ui.dialogs.skills.setup()
        tree = self.window.ui.nodes["skills.installed.list"]
        tree.itemChanged.connect(self._on_enabled_changed)
        explore_tree = self.window.ui.nodes["skills.explore.list"]
        explore_tree.itemChanged.connect(self._update_install_button)
        explore_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        explore_tree.customContextMenuRequested.connect(self.show_explore_context_menu)
        self.refresh_installed()
        self._update_install_button()
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
                item.setText(1, skill.get("display_name") or skill["name"])
                item.setText(2, skill.get("description", ""))
                item.setText(3, skill.get("standard", "agent-skills"))
                source = skill.get("source", "local")
                if skill.get("issues"):
                    source += " ⚠"
                    item.setToolTip(1, "\n".join(skill["issues"]))
                item.setText(4, source)
                if source:
                    item.setToolTip(4, source)
                description = str(skill.get("description") or "")
                if description:
                    item.setToolTip(2, description)
                item.setData(0, Qt.ItemDataRole.UserRole, skill["name"])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    0,
                    Qt.CheckState.Checked if skill.get("enabled") else Qt.CheckState.Unchecked,
                )
                icon_path = skill.get("icon_path")
                if icon_path and os.path.isfile(icon_path):
                    item.setIcon(1, QIcon(icon_path))
            tree.resizeColumnToContents(0)
            self._update_installed_status()
        finally:
            self._refreshing = False
        self.refresh_toolbox()

    def _update_installed_status(self):
        node = self.window.ui.nodes.get("skills.installed.status")
        if node is None:
            return
        skills = self.window.core.skills.list_installed()
        enabled = sum(1 for item in skills if item.get("enabled"))
        self._set_status_key(
            "skills.status.installed",
            targets=("installed",),
            total=len(skills),
            enabled=enabled,
        )

    @Slot(QTreeWidgetItem, int)
    def _on_enabled_changed(self, item, column):
        if self._refreshing or column != 0:
            return
        name = item.data(0, Qt.ItemDataRole.UserRole)
        if not name:
            return
        self.set_enabled(
            str(name),
            item.checkState(0) == Qt.CheckState.Checked,
            source="dialog",
        )

    def on_toolbox_enabled_changed(self, name: str, enabled: bool):
        """Apply a skill checkbox change coming from the toolbox."""
        self.set_enabled(name, enabled, source="toolbox")

    def set_enabled(self, name: str, enabled: bool, source: str = ""):
        """Set global skill state and synchronize all skill views/preset state."""
        if not self.window.core.skills.set_enabled(str(name), bool(enabled)):
            return
        if source != "dialog":
            self.refresh_installed()
        else:
            self._update_installed_status()
            self.refresh_toolbox()
        self.window.controller.presets.sync_agent_skills_from_global()
        self.window.controller.plugins.update_info()

    def refresh_toolbox(self):
        """Refresh the compact toolbox Skills list when it is available."""
        try:
            self.window.ui.toolbox.presets.refresh_skills()
        except (AttributeError, RuntimeError):
            pass

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

    def show_installed_context_menu(self, pos):
        tree = self.window.ui.nodes.get("skills.installed.list")
        if tree is None:
            return
        item = tree.itemAt(pos)
        if item is None:
            return
        name = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        if not name:
            return
        menu = QMenu(tree)
        remove_action = menu.addAction(QIcon(":/icons/delete.svg"), trans("skills.remove"))
        selected = menu.exec(tree.viewport().mapToGlobal(pos))
        if selected == remove_action:
            self.remove_skill(name, item.text(1) or name)

    def remove_skill(self, name: str, display_name: str = ""):
        name = str(name or "").strip()
        if not name:
            return
        display_name = str(display_name or name)
        answer = QMessageBox.question(
            self.window,
            trans("skills.remove"),
            trans("skills.remove.confirm").format(name=display_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.window.core.skills.remove(name)
            self.refresh_installed()
            self.window.controller.presets.sync_agent_skills_from_global()
            self.window.controller.plugins.update_info()
            self._set_status_key("skills.status.removed", name=display_name)
        except Exception as exc:
            self.window.ui.dialogs.alert(str(exc))

    def remove_selected(self):
        """Compatibility wrapper for callers outside the dialog UI."""
        tree = self.window.ui.nodes.get("skills.installed.list")
        if tree is None:
            return
        item = tree.currentItem()
        if item is None:
            return
        name = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        if name:
            self.remove_skill(name, item.text(1) or name)

    def open_directory(self):
        path = self.window.core.skills.get_root_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def refresh_catalog(self):
        url_node = self.window.ui.nodes.get("skills.catalog.url")
        url = str(url_node.text() if url_node is not None else "").strip()
        if url:
            self.window.core.skills.set_catalog_url(url)
        self._start_worker("catalog", url=url or self.window.core.skills.get_catalog_url())

    def show_explore_context_menu(self, pos):
        tree = self.window.ui.nodes.get("skills.explore.list")
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
        name = str(entry.get("name") or "")
        installed = {x["name"] for x in self.window.core.skills.list_installed()}
        if name in installed:
            return
        menu = QMenu(tree)
        install_action = menu.addAction(QIcon(":/icons/download.svg"), trans("action.install"))
        selected = menu.exec(tree.viewport().mapToGlobal(pos))
        if selected == install_action:
            button = self.window.ui.nodes.get("skills.explore.btn.install")
            if button is not None:
                button.setEnabled(False)
            self._start_worker("install_catalog_many", entries=[entry], enable=True)

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
            self._update_install_button()
            return
        button = self.window.ui.nodes.get("skills.explore.btn.install")
        if button is not None:
            button.setEnabled(False)
        # Install checked entries serially inside one worker. Registry updates
        # must not race when several skills are selected at once.
        self._start_worker("install_catalog_many", entries=entries, enable=True)

    @Slot(QTreeWidgetItem, int)
    def _update_install_button(self, *_args):
        tree = self.window.ui.nodes.get("skills.explore.list")
        button = self.window.ui.nodes.get("skills.explore.btn.install")
        if tree is None or button is None:
            return
        checked = any(
            tree.topLevelItem(row).checkState(0) == Qt.CheckState.Checked
            for row in range(tree.topLevelItemCount())
        )
        button.setEnabled(checked)

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
            source = str(entry.get("url") or entry.get("homepage") or "")
            item.setText(5, source)
            if source:
                item.setToolTip(5, source)
            raw_icon = entry.get("_icon_bytes")
            if raw_icon:
                pixmap = QPixmap()
                if pixmap.loadFromData(raw_icon):
                    item.setIcon(1, QIcon(pixmap))
            homepage = str(entry.get("homepage") or entry.get("url") or "")
            if homepage:
                item.setToolTip(1, homepage)
            description = item.text(2)
            if description:
                item.setToolTip(2, description)
        tree.resizeColumnToContents(0)
        # QTreeWidget may make the first inserted item current automatically.
        # Keep the catalog visually neutral until the user explicitly clicks a
        # row; install selection is represented only by column-0 checkboxes.
        tree.clearSelection()
        tree.setCurrentItem(None)
        self._update_install_button()
        self._set_status_key(
            "skills.status.catalog",
            targets=("explore",),
            total=len(self._catalog),
        )

    def _start_worker(self, action: str, **kwargs):
        status_key = {
            "catalog": "skills.status.loading_catalog",
            "import_github": "skills.status.importing_github",
            "import_local": "skills.status.importing_local",
            "install_catalog": "skills.status.installing",
            "install_catalog_many": "skills.status.installing",
        }.get(action)
        if status_key:
            targets = ("explore",) if action == "catalog" else ("installed", "explore")
            self._set_status_key(status_key, targets=targets)

        worker = SkillsWorker(self.window, action, **kwargs)
        self._workers.add(worker)
        worker.signals.status.connect(
            lambda text, a=action: self._set_worker_status(a, text)
        )
        worker.signals.finished.connect(lambda a, r, w=worker: self._on_worker_finished(w, a, r))
        worker.signals.error.connect(lambda a, e, w=worker: self._on_worker_error(w, a, e))
        QThreadPool.globalInstance().start(worker)

    @Slot(str)
    def _set_status(self, text: str):
        for key in ("skills.installed.status", "skills.explore.status"):
            node = self.window.ui.nodes.get(key)
            if node is not None:
                node.setText(str(text or ""))

    def _set_worker_status(self, action: str, text: str):
        """Route worker progress to the tab that owns the operation."""
        if action == "catalog":
            targets = ("explore",)
        else:
            targets = ("installed", "explore")
        value = str(text or "")
        for target in targets:
            node = self.window.ui.nodes.get(f"skills.{target}.status")
            if node is not None:
                node.setText(value)

    def _set_status_key(self, key: str, targets=("installed", "explore"), **kwargs):
        state = (str(key), dict(kwargs))
        text = trans(key).format(**kwargs)
        for target in targets:
            self._status_state[target] = state
            node = self.window.ui.nodes.get(f"skills.{target}.status")
            if node is not None:
                node.setText(text)

    def retranslate_status(self):
        """Refresh persisted dialog status texts after a runtime locale change."""
        for target, state in self._status_state.items():
            if not state:
                continue
            key, kwargs = state
            node = self.window.ui.nodes.get(f"skills.{target}.status")
            if node is not None:
                node.setText(trans(key).format(**kwargs))

    def _on_worker_finished(self, worker, action: str, result):
        self._workers.discard(worker)
        if action == "catalog":
            self._render_catalog(result)
            return
        self.refresh_installed()
        self.window.controller.presets.sync_agent_skills_from_global()
        self.window.controller.plugins.update_info()
        if action == "install_catalog_many":
            # Rebuild Explore from the cached catalog so newly installed rows get
            # their checkboxes cleared and are marked as already installed.
            self._render_catalog(self._catalog)
        names = [str(item.get("name")) for item in (result or []) if isinstance(item, dict)]
        if names:
            self._set_status_key("skills.status.imported", names=", ".join(names))
        else:
            self._set_status_key("skills.status.ready")

    def _on_worker_error(self, worker, action: str, error):
        self._workers.discard(worker)
        if action == "install_catalog_many":
            self._update_install_button()
        self._set_status_key("skills.status.error", error=error)
        self.window.ui.dialogs.alert(str(error))
