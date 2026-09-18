#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.18 13:42:00                  #
# ================================================== #

import os
from datetime import datetime
from pathlib import Path

from packaging.version import InvalidVersion, Version
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QFileDialog, QMessageBox

from pygpt_net.core.profile_exporter import (
    InsufficientDiskSpace,
    InvalidProfileArchive,
)
from pygpt_net.ui.dialog.profile_exporter import ExportProfileDialog, ImportProfileDialog
from pygpt_net.utils import trans

from .worker import ProfileExporterWorker


class ProfileExporter:
    """UI/controller flow for profile import and export."""

    def __init__(self, window=None):
        self.window = window
        self.worker = None
        self.size_worker = None
        self.export_dialog = None
        self.import_dialog = None
        self.export_sizes = {}
        self.import_state = None
        self.busy = False

    def setup(self):
        """No eager UI setup is required; dialogs are created on demand."""
        pass

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def open_export(self):
        if self.busy:
            self.window.ui.dialogs.alert(trans("profile.operation.busy"))
            return

        try:
            # Persist the active in-memory profile state before measuring or
            # archiving it so the ZIP reflects what the user currently sees.
            self.window.controller.settings.save_all(force=True)
        except Exception as exc:
            self.window.core.debug.log(exc)

        self.export_sizes = {}
        self.export_dialog = ExportProfileDialog(self.window, self)
        self.export_dialog.rejected.connect(self._cancel_size_worker)
        self.export_dialog.setModal(True)
        self.export_dialog.show()
        self.export_dialog.raise_()
        self.export_dialog.activateWindow()

        self.window.update_status(trans("profile.export.status.sizing"))
        worker = ProfileExporterWorker(self.window, "sizes")
        worker.signals.sizes.connect(self._on_export_sizes)
        worker.signals.error.connect(self._on_size_error)
        self.size_worker = worker
        self.window.threadpool.start(worker)

    def _cancel_size_worker(self):
        worker = self.size_worker
        self.size_worker = None
        if worker is not None:
            worker.cancel()
        self.window.update_status("")

    @Slot(object)
    def _on_export_sizes(self, sizes):
        self.size_worker = None
        self.export_sizes = dict(sizes or {})
        if self.export_dialog is not None and self.export_dialog.isVisible():
            self.export_dialog.set_sizes(
                self.export_sizes,
                self.window.core.profile_exporter.format_size,
            )
        self.window.update_status("")

    @Slot(object)
    def _on_size_error(self, error):
        self.size_worker = None
        self.window.core.debug.log(error)
        self.window.update_status("")
        if self.export_dialog is not None and self.export_dialog.isVisible():
            self._alert(
                trans("profile.export.size.error").format(error=str(error)),
                parent=self.export_dialog,
            )

    def export_selected(self):
        if self.export_dialog is None or self.busy:
            return
        selected = self.export_dialog.selected_sections()
        if not selected:
            self._alert(
                trans("profile.export.section.empty"),
                parent=self.export_dialog,
            )
            return

        stamp = datetime.now().strftime("%Y_%m__%d_%H_%M_%S")
        default_name = f"PyGPT_export_{stamp}.zip"
        default_path = os.path.join(str(Path.home()), default_name)
        filename, _filter = QFileDialog.getSaveFileName(
            self.export_dialog,
            trans("profile.export.file.title"),
            default_path,
            "ZIP (*.zip)",
        )
        if not filename:
            return
        if not filename.lower().endswith(".zip"):
            filename += ".zip"

        try:
            required = self.window.core.profile_exporter.estimate_export_required(
                self.export_sizes,
                selected,
            )
            self.window.core.profile_exporter.ensure_space(
                os.path.dirname(os.path.abspath(filename)) or os.getcwd(),
                required,
            )
        except InsufficientDiskSpace as exc:
            self._show_disk_space_error(exc, parent=self.export_dialog)
            return

        self.export_dialog.accept()
        self.export_dialog = None
        self.busy = True
        self.window.update_status(trans("profile.export.status.preparing"))
        self.window.ui.dialogs.show_loader(
            message=trans("profile.export.loader"),
            show_cancel=True,
            on_cancel=self.cancel,
            modal=True,
        )

        worker = ProfileExporterWorker(
            self.window,
            "export",
            destination=filename,
            selected=selected,
        )
        self._connect_operation_worker(worker, self._export_finished)
        self.worker = worker
        self.window.threadpool.start(worker)

    @Slot(object)
    def _export_finished(self, path):
        self._finish_operation()
        self.window.update_status(trans("profile.export.status.done"))
        self.window.ui.dialogs.alert(
            trans("profile.export.success").format(path=str(path))
        )

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def open_import(self):
        if self.busy:
            self.window.ui.dialogs.alert(trans("profile.operation.busy"))
            return

        filename, _filter = QFileDialog.getOpenFileName(
            self.window,
            trans("profile.import.file.title"),
            str(Path.home()),
            "ZIP (*.zip)",
        )
        if not filename:
            return

        try:
            meta = self.window.core.profile_exporter.read_meta(filename)
            exported_version = Version(meta["app_version"])
            current_version = Version(self.window.core.config.get_version())
        except (InvalidProfileArchive, InvalidVersion, ValueError, TypeError) as exc:
            self.window.core.debug.log(exc)
            self.window.ui.dialogs.alert(trans("profile.import.invalid"))
            return

        if exported_version > current_version:
            self.window.ui.dialogs.alert(
                trans("profile.import.newer").format(version=meta["app_version"])
            )
            return

        # Preliminary warning before opening the options dialog, matching the
        # import flow. The authoritative check is repeated later on the actual
        # destination filesystem chosen by the user.
        try:
            required = self.window.core.profile_exporter.estimate_import_required(
                filename,
                meta["exported"],
            )
            free = self.window.core.profile_exporter.get_free_space(
                self.window.core.config.get_user_path()
            )
            if free < required:
                self._show_disk_space_warning(required, free)
        except Exception as exc:
            self.window.core.debug.log(exc)
            self.window.ui.dialogs.alert(trans("profile.import.invalid"))
            return

        default_name = trans("profile.import.default_name").format(
            date=datetime.now().strftime("%Y-%m-%d")
        )
        self.import_state = {
            "zip_path": filename,
            "meta": meta,
        }
        self.import_dialog = ImportProfileDialog(
            self.window,
            self,
            filename=os.path.basename(filename),
            exported=meta["exported"],
            default_name=default_name,
        )
        self.import_dialog.setModal(True)
        self.import_dialog.show()
        self.import_dialog.raise_()
        self.import_dialog.activateWindow()

    def import_selected(self):
        if self.import_dialog is None or self.import_state is None or self.busy:
            return

        name = self.import_dialog.name_input.text().strip()
        if not name:
            self._alert(
                trans("profile.import.name.empty"),
                parent=self.import_dialog,
            )
            return
        if self._profile_name_exists(name):
            self._alert(
                trans("profile.import.name.exists").format(name=name),
                parent=self.import_dialog,
            )
            return

        selected = self.import_dialog.selected_sections()
        zip_path = self.import_state["zip_path"]

        target_dir = self._choose_import_directory(zip_path, selected)
        if not target_dir:
            return

        self.import_state.update({
            "name": name,
            "selected": selected,
            "target_dir": target_dir,
        })
        self.import_dialog.accept()
        self.import_dialog = None

        self.busy = True
        self.window.update_status(trans("profile.import.status.preparing"))
        self.window.ui.dialogs.show_loader(
            message=trans("profile.import.loader"),
            show_cancel=True,
            on_cancel=self.cancel,
            modal=True,
        )

        worker = ProfileExporterWorker(
            self.window,
            "import",
            zip_path=zip_path,
            target_dir=target_dir,
            selected=selected,
        )
        worker.signals.commit_started.connect(self._on_import_commit_started)
        self._connect_operation_worker(worker, self._import_finished)
        self.worker = worker
        self.window.threadpool.start(worker)

    def _choose_import_directory(self, zip_path: str, selected):
        while True:
            target = QFileDialog.getExistingDirectory(
                self.import_dialog or self.window,
                trans("profile.import.workdir.title"),
                str(Path.home()),
                QFileDialog.Option.ShowDirsOnly,
            )
            if not target:
                return None

            target = os.path.abspath(os.path.expanduser(target))
            if os.path.islink(target):
                self._alert(
                    trans("profile.import.workdir.unsafe"),
                    parent=self.import_dialog,
                )
                continue

            valid, _reason = self.window.core.profile_exporter.validate_target_directory(target)
            if not valid:
                self._alert(
                    trans("profile.import.workdir.unsafe"),
                    parent=self.import_dialog,
                )
                continue

            try:
                is_empty = self.window.core.filesystem.is_directory_empty(target)
            except Exception:
                is_empty = False

            if not is_empty:
                answer = QMessageBox.warning(
                    self.import_dialog or self.window,
                    trans("profile.import.workdir.warning.title"),
                    trans("profile.import.workdir.warning").format(path=target),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    continue

            try:
                required = self.window.core.profile_exporter.estimate_import_required(
                    zip_path,
                    selected,
                )
                self.window.core.profile_exporter.ensure_space(target, required)
            except InsufficientDiskSpace as exc:
                self._show_disk_space_error(exc, parent=self.import_dialog)
                continue

            return target

    @Slot()
    def _on_import_commit_started(self):
        dialog = self.window.ui.dialog.get("loader")
        if dialog is not None:
            dialog.cancel_button.setEnabled(False)

    @Slot(object)
    def _import_finished(self, path):
        state = dict(self.import_state or {})
        self._finish_operation()
        self.import_state = None

        name = state.get("name", "")
        target = state.get("target_dir", str(path))
        if not name:
            self.window.ui.dialogs.alert(trans("profile.import.error").format(error="Missing profile name"))
            return

        try:
            uuid = self.window.core.config.profile.add(name, target)
            self.window.controller.settings.profile.update_list()
            self.window.controller.settings.profile.update_menu()
        except Exception as exc:
            self.window.core.debug.log(exc)
            self.window.ui.dialogs.alert(
                trans("profile.import.error").format(error=str(exc))
            )
            return

        self.window.update_status(
            trans("profile.import.status.done").format(name=name)
        )
        answer = QMessageBox.question(
            self.window,
            trans("profile.import.switch.title"),
            trans("profile.import.switch").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.window.controller.settings.profile.switch(uuid, force=True)

    # ------------------------------------------------------------------
    # Worker / error helpers
    # ------------------------------------------------------------------

    def _connect_operation_worker(self, worker, finished_slot):
        worker.signals.status.connect(self.window.update_status)
        worker.signals.finished.connect(finished_slot)
        worker.signals.cancelled.connect(self._operation_cancelled)
        worker.signals.error.connect(self._operation_error)

    def cancel(self):
        if self.worker is not None:
            self.worker.cancel()
            self.window.update_status(trans("profile.operation.cancelling"))

    @Slot()
    def _operation_cancelled(self):
        self._finish_operation()
        self.window.update_status(trans("profile.operation.cancelled"))
        self.import_state = None

    @Slot(object)
    def _operation_error(self, error):
        self.window.core.debug.log(error)
        self._finish_operation()
        if isinstance(error, InsufficientDiskSpace):
            self._show_disk_space_error(error)
        elif isinstance(error, InvalidProfileArchive):
            self.window.ui.dialogs.alert(trans("profile.import.invalid"))
        else:
            self.window.ui.dialogs.alert(
                trans("profile.operation.error").format(error=str(error))
            )
        self.window.update_status(trans("profile.operation.failed"))
        self.import_state = None

    def _finish_operation(self):
        self.window.ui.dialogs.finish_loader()
        self.worker = None
        self.busy = False

    def _profile_name_exists(self, name: str) -> bool:
        wanted = name.strip().casefold()
        for profile in self.window.core.config.profile.get_all().values():
            if str(profile.get("name") or "").strip().casefold() == wanted:
                return True
        return False

    def _alert(self, message: str, parent=None):
        """Show an alert owned by the current modal profile dialog when needed."""
        QMessageBox.information(
            parent or self.window,
            trans("alert.title"),
            self.window.core.debug.parse_alert(message),
            QMessageBox.StandardButton.Ok,
        )

    def _show_disk_space_error(self, exc: InsufficientDiskSpace, parent=None):
        self._alert(
            trans("profile.disk_space.error").format(
                required=self.window.core.profile_exporter.format_size(exc.required),
                free=self.window.core.profile_exporter.format_size(exc.free),
            ),
            parent=parent,
        )

    def _show_disk_space_warning(self, required: int, free: int):
        QMessageBox.warning(
            self.window,
            trans("profile.disk_space.warning.title"),
            trans("profile.disk_space.warning").format(
                required=self.window.core.profile_exporter.format_size(required),
                free=self.window.core.profile_exporter.format_size(free),
            ),
            QMessageBox.StandardButton.Ok,
        )
