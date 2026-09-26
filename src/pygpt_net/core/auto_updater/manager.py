#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.25 20:00:00                  #
# ================================================== #

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, Signal, Slot, QTimer
from PySide6.QtWidgets import QMessageBox

from pygpt_net.core.auto_updater import AUTO_UPDATER_ENABLED, is_auto_update_method_enabled
from pygpt_net.core.auto_updater.appimage import AppImageUpdateFlow
from pygpt_net.core.auto_updater.base import (
    UpdateCancelled,
    UpdateContext,
    UpdateError,
    UpdatePayload,
    UpdateResult,
)
from pygpt_net.core.auto_updater.detector import DistributionDetector, DistributionInfo
from pygpt_net.core.auto_updater.linux import LinuxArchiveUpdateFlow
from pygpt_net.core.auto_updater.pip import PipUpdateFlow
from pygpt_net.core.auto_updater.snap import SnapUpdateFlow
from pygpt_net.core.auto_updater.source import SourceUpdateFlow
from pygpt_net.core.auto_updater.source_archive import SourceArchiveUpdateFlow
from pygpt_net.core.auto_updater.trace import AutoUpdateTrace
from pygpt_net.core.auto_updater.windows import WindowsMsiUpdateFlow
from pygpt_net.utils import trans


@dataclass
class ConfirmationRequest:
    title: str
    message: str
    event: threading.Event
    result: Optional[bool] = None


class AutoUpdater(QObject):
    """Coordinates distribution-specific automatic update flows."""

    progressChanged = Signal(object)
    confirmationRequested = Signal(object)
    flowFinished = Signal(object)

    SUPPORTED = {
        "windows_msi",
        "linux_archive",
        "appimage",
        "pip",
        "source",
        "source_manual",
        "snap",
    }

    def __init__(self, window=None):
        super().__init__()
        self.window = window
        self.trace = AutoUpdateTrace(window)
        self.detector = DistributionDetector(window, log_cb=self.trace.log)
        self.cancel_event = threading.Event()
        self.worker = None
        self.running = False
        self._distribution = None

        self.progressChanged.connect(self._on_progress)
        self.confirmationRequested.connect(self._on_confirmation_requested)
        self.flowFinished.connect(self._on_finished)

    def log(self, message: str):
        self.trace.log(message)

    def detect(self) -> DistributionInfo:
        self.log("Distribution detection requested.")
        self._distribution = self.detector.detect()
        self.log(
            "Distribution detected: "
            f"kind={self._distribution.kind!r}, label={self._distribution.label!r}, "
            f"source_root={self._distribution.source_root!r}"
        )
        return self._distribution

    def can_update(self) -> bool:
        if not AUTO_UPDATER_ENABLED:
            self.log("Automatic updater is disabled by AUTO_UPDATER_ENABLED=False.")
            return False
        distribution = self.detect()
        supported = distribution.kind in self.SUPPORTED
        method_enabled = is_auto_update_method_enabled(distribution.kind)
        result = supported and method_enabled
        self.log(
            "Automatic update support check: "
            f"kind={distribution.kind!r}, supported={supported}, "
            f"method_enabled={method_enabled}, result={result}."
        )
        return result

    def get_type(self) -> str:
        return self.detect().kind

    def start(self, payload: UpdatePayload) -> bool:
        self.log(
            "Start requested: "
            f"version={payload.version!r}, build={payload.build!r}, "
            f"download_windows={payload.download_windows!r}, "
            f"download_linux={payload.download_linux!r}, "
            f"download_appimage={payload.download_appimage!r}"
        )
        if not AUTO_UPDATER_ENABLED:
            self.log("Start rejected: AUTO_UPDATER_ENABLED=False.")
            return False
        if self.running:
            self.log("Start rejected: another automatic update is already running.")
            return False

        distribution = self.detect()
        if distribution.kind == "ms_store":
            self.log("Microsoft Store installation detected; in-app updater is intentionally skipped.")
            QMessageBox.information(
                self.window,
                trans("update.auto.title"),
                trans("update.auto.ms_store"),
            )
            return False
        if distribution.kind == "flatpak":
            self.log("Flatpak installation detected; in-app updater is not supported.")
            QMessageBox.information(
                self.window,
                trans("update.auto.title"),
                trans("update.auto.flatpak"),
            )
            return False
        if distribution.kind not in self.SUPPORTED:
            self.log(f"Unsupported installation type: {distribution.kind!r}.")
            QMessageBox.warning(
                self.window,
                trans("update.auto.title"),
                trans("update.auto.unsupported"),
            )
            return False
        if not is_auto_update_method_enabled(distribution.kind):
            self.log(
                f"Start rejected: automatic update method for {distribution.kind!r} "
                "is disabled by its per-method constant."
            )
            return False

        self.log("Showing initial automatic-update confirmation dialog.")
        answer = QMessageBox.question(
            self.window,
            trans("update.auto.confirm.start.title"),
            trans("update.auto.confirm.start").format(
                version=payload.version,
                type=distribution.label,
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            self.log("Initial automatic-update confirmation declined by user.")
            return False
        self.log("Initial automatic-update confirmation accepted by user.")

        self.cancel_event.clear()
        self.running = True
        progress = self.window.ui.dialog.get("update.progress")
        if progress is not None:
            self.log("Opening update progress dialog.")
            progress.start_update(self.cancel, trans("update.auto.status.preparing"))
        else:
            self.log("Update progress dialog is unavailable; continuing without it.")

        self.worker = AutoUpdateWorker(self, payload, distribution)
        self.log(f"Starting worker for flow kind={distribution.kind!r}.")
        self.window.threadpool.start(self.worker)
        return True

    def cancel(self):
        if self.running:
            self.log("Cancel requested by user.")
            self.cancel_event.set()
        else:
            self.log("Cancel requested while no update flow is running; ignored.")

    def _confirm_from_worker(self, title: str, message: str) -> bool:
        self.log(f"Worker requested UI confirmation: title={title!r}.")
        request = ConfirmationRequest(title, message, threading.Event())
        self.confirmationRequested.emit(request)
        while not request.event.wait(0.1):
            if self.cancel_event.is_set():
                self.log("Confirmation wait interrupted by cancellation.")
                return False
        self.log(f"Worker confirmation completed: result={bool(request.result)}.")
        return bool(request.result)

    def _emit_progress(self, data: dict):
        self.progressChanged.emit(data)

    def _make_flow(self, payload: UpdatePayload, distribution: DistributionInfo, context: UpdateContext):
        kind = distribution.kind
        if not is_auto_update_method_enabled(kind):
            self.log(f"Flow creation blocked: automatic update method for {kind!r} is disabled.")
            raise UpdateError("Automatic update method is disabled")
        self.log(f"Creating update flow implementation for kind={kind!r}.")
        if kind == "windows_msi":
            return WindowsMsiUpdateFlow(self.window, payload, context)
        if kind == "linux_archive":
            return LinuxArchiveUpdateFlow(self.window, payload, context)
        if kind == "appimage":
            return AppImageUpdateFlow(self.window, payload, context)
        if kind == "pip":
            return PipUpdateFlow(self.window, payload, context)
        if kind == "source":
            return SourceUpdateFlow(self.window, payload, context, distribution.source_root)
        if kind == "source_manual":
            return SourceArchiveUpdateFlow(self.window, payload, context, distribution.source_root)
        if kind == "snap":
            return SnapUpdateFlow(self.window, payload, context)
        raise UpdateError(trans("update.auto.unsupported"))

    @Slot(object)
    def _on_confirmation_requested(self, request: ConfirmationRequest):
        try:
            parent = self.window.ui.dialog.get("update.progress") or self.window
            self.log(f"Displaying worker confirmation dialog: title={request.title!r}.")
            answer = QMessageBox.question(
                parent,
                request.title,
                request.message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            request.result = answer == QMessageBox.Yes
            self.log(f"Worker confirmation dialog answered: {'YES' if request.result else 'NO'}.")
        finally:
            request.event.set()

    @Slot(object)
    def _on_progress(self, data: dict):
        dialog = self.window.ui.dialog.get("update.progress")
        if dialog is None:
            return
        status = data.get("status", "") or ""
        if status.startswith("update."):
            status = trans(status)
        dialog.set_progress(
            status=status,
            percent=data.get("percent"),
            received=data.get("received", 0),
            total=data.get("total", 0),
            speed=data.get("speed", 0.0),
            eta=data.get("eta"),
        )

    @Slot(object)
    def _on_finished(self, result):
        self.log(f"Flow finished signal received: result_type={type(result).__name__}.")
        self.running = False
        self.worker = None

        dialog = self.window.ui.dialog.get("update.progress")
        if dialog is not None:
            self.log("Closing update progress dialog.")
            dialog.finish_update()

        if isinstance(result, UpdateCancelled):
            self.log(f"Update cancelled: {result}")
            QMessageBox.information(self.window, trans("update.auto.title"), trans("update.auto.cancelled"))
            return
        if isinstance(result, Exception):
            self.log(f"Update failed with exception: {type(result).__name__}: {result}")
            try:
                self.window.core.debug.log(result)
            except Exception:
                pass
            QMessageBox.critical(
                self.window,
                trans("update.auto.error.title"),
                f"{trans('update.auto.error')}\n\n{result}",
            )
            return
        if not isinstance(result, UpdateResult):
            self.log(f"Update returned unexpected result object: {result!r}")
            QMessageBox.critical(self.window, trans("update.auto.error.title"), trans("update.auto.error"))
            return

        self.log(
            "Update result: "
            f"success={result.success}, quit_app={result.quit_app}, "
            f"message={result.message!r}, data={result.data!r}"
        )
        if result.quit_app:
            self.log("Update flow requested application shutdown; scheduling quit in 50 ms.")
            # Flows that need post-exit work prepare a detached helper before
            # returning. Quit through QApplication so aboutToQuit performs
            # PyGPT's normal shutdown path before that helper continues.
            QTimer.singleShot(50, self.window.app.quit)
            return

        if result.message:
            self.log("Displaying final update result message.")
            QMessageBox.information(self.window, trans("update.auto.title"), result.message)


class AutoUpdateWorker(QRunnable):
    def __init__(self, manager: AutoUpdater, payload: UpdatePayload, distribution: DistributionInfo):
        super().__init__()
        self.manager = manager
        self.payload = payload
        self.distribution = distribution

    @Slot()
    def run(self):
        self.manager.log(
            "Worker entered: "
            f"distribution={self.distribution.kind!r}, version={self.payload.version!r}."
        )
        try:
            context = UpdateContext(
                self.manager.window,
                self.manager.cancel_event,
                self.manager._emit_progress,
                self.manager._confirm_from_worker,
                log_cb=self.manager.trace.log,
                debug_enabled_cb=self.manager.trace.enabled,
            )
            flow = self.manager._make_flow(self.payload, self.distribution, context)
            context.log(f"Flow object created: class={flow.__class__.__name__}, id={flow.id!r}.")
            result = flow.run()
            context.log(f"Flow run() returned: {result!r}")
            self.manager.flowFinished.emit(result)
        except UpdateCancelled as exc:
            self.manager.log(f"Worker caught UpdateCancelled: {exc}")
            self.manager.flowFinished.emit(exc)
        except Exception as exc:
            self.manager.log(f"Worker caught exception: {type(exc).__name__}: {exc}")
            self.manager.flowFinished.emit(exc)
