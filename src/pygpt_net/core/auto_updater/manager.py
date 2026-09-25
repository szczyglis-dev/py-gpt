#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, Signal, Slot, QTimer
from PySide6.QtWidgets import QMessageBox

from pygpt_net.core.auto_updater import AUTO_UPDATER_ENABLED
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
        "snap",
    }

    def __init__(self, window=None):
        super().__init__()
        self.window = window
        self.detector = DistributionDetector(window)
        self.cancel_event = threading.Event()
        self.worker = None
        self.running = False
        self._distribution = None

        self.progressChanged.connect(self._on_progress)
        self.confirmationRequested.connect(self._on_confirmation_requested)
        self.flowFinished.connect(self._on_finished)

    def detect(self) -> DistributionInfo:
        self._distribution = self.detector.detect()
        return self._distribution

    def can_update(self) -> bool:
        if not AUTO_UPDATER_ENABLED:
            return False
        return self.detect().kind in self.SUPPORTED

    def get_type(self) -> str:
        return self.detect().kind

    def start(self, payload: UpdatePayload) -> bool:
        if not AUTO_UPDATER_ENABLED or self.running:
            return False

        distribution = self.detect()
        if distribution.kind == "ms_store":
            QMessageBox.information(
                self.window,
                trans("update.auto.title"),
                trans("update.auto.ms_store"),
            )
            return False
        if distribution.kind == "flatpak":
            QMessageBox.information(
                self.window,
                trans("update.auto.title"),
                trans("update.auto.flatpak"),
            )
            return False
        if distribution.kind not in self.SUPPORTED:
            QMessageBox.warning(
                self.window,
                trans("update.auto.title"),
                trans("update.auto.unsupported"),
            )
            return False

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
            return False

        self.cancel_event.clear()
        self.running = True
        progress = self.window.ui.dialog.get("update.progress")
        if progress is not None:
            progress.start_update(self.cancel, trans("update.auto.status.preparing"))

        self.worker = AutoUpdateWorker(self, payload, distribution)
        self.window.threadpool.start(self.worker)
        return True

    def cancel(self):
        if self.running:
            self.cancel_event.set()

    def _confirm_from_worker(self, title: str, message: str) -> bool:
        request = ConfirmationRequest(title, message, threading.Event())
        self.confirmationRequested.emit(request)
        while not request.event.wait(0.1):
            if self.cancel_event.is_set():
                return False
        return bool(request.result)

    def _emit_progress(self, data: dict):
        self.progressChanged.emit(data)

    def _make_flow(self, payload: UpdatePayload, distribution: DistributionInfo, context: UpdateContext):
        kind = distribution.kind
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
        if kind == "snap":
            return SnapUpdateFlow(self.window, payload, context)
        raise UpdateError(trans("update.auto.unsupported"))

    @Slot(object)
    def _on_confirmation_requested(self, request: ConfirmationRequest):
        try:
            parent = self.window.ui.dialog.get("update.progress") or self.window
            answer = QMessageBox.question(
                parent,
                request.title,
                request.message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            request.result = answer == QMessageBox.Yes
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
        self.running = False
        self.worker = None

        dialog = self.window.ui.dialog.get("update.progress")
        if dialog is not None:
            dialog.finish_update()

        if isinstance(result, UpdateCancelled):
            QMessageBox.information(self.window, trans("update.auto.title"), trans("update.auto.cancelled"))
            return
        if isinstance(result, Exception):
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
            QMessageBox.critical(self.window, trans("update.auto.error.title"), trans("update.auto.error"))
            return

        if result.quit_app:
            # The flow has already created a detached post-exit helper. Quit via
            # QApplication so aboutToQuit performs PyGPT's normal shutdown path.
            QTimer.singleShot(50, self.window.app.quit)
            return

        if result.message:
            QMessageBox.information(self.window, trans("update.auto.title"), result.message)


class AutoUpdateWorker(QRunnable):
    def __init__(self, manager: AutoUpdater, payload: UpdatePayload, distribution: DistributionInfo):
        super().__init__()
        self.manager = manager
        self.payload = payload
        self.distribution = distribution

    @Slot()
    def run(self):
        try:
            context = UpdateContext(
                self.manager.window,
                self.manager.cancel_event,
                self.manager._emit_progress,
                self.manager._confirm_from_worker,
            )
            flow = self.manager._make_flow(self.payload, self.distribution, context)
            result = flow.run()
            self.manager.flowFinished.emit(result)
        except UpdateCancelled as exc:
            self.manager.flowFinished.emit(exc)
        except Exception as exc:
            self.manager.flowFinished.emit(exc)
