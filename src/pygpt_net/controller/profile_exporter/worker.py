#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.18 13:00:00                  #
# ================================================== #

import threading

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from pygpt_net.core.profile_exporter import ProfileExportCancelled
from pygpt_net.core.qt import safe_emit
from pygpt_net.utils import trans


class ProfileExporterWorkerSignals(QObject):
    sizes = Signal(object)
    finished = Signal(object)
    cancelled = Signal()
    error = Signal(object)
    status = Signal(str)
    commit_started = Signal()


class ProfileExporterWorker(QRunnable):
    def __init__(self, window, action: str, **kwargs):
        super().__init__()
        self.window = window
        self.action = action
        self.kwargs = kwargs
        self.signals = ProfileExporterWorkerSignals()
        self._cancel = threading.Event()
        self._committing = False

    def cancel(self):
        if not self._committing:
            self._cancel.set()

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def _status(self, key: str):
        parts = key.rsplit(".", 1)
        if len(parts) == 2 and parts[1] in ("db", "config", "files", "data"):
            section = trans(f"profile.export.section.{parts[1]}")
            if key.startswith("profile.export.status."):
                message = trans("profile.export.status.section").format(section=section)
            else:
                message = trans("profile.import.status.section").format(section=section)
        else:
            message = trans(key)
        safe_emit(self.signals, "status", message)

    def _commit_started(self):
        self._committing = True
        safe_emit(self.signals, "commit_started")

    @Slot()
    def run(self):
        try:
            core = self.window.core.profile_exporter
            if self.action == "sizes":
                result = core.get_section_sizes(cancelled=self.is_cancelled)
                safe_emit(self.signals, "sizes", result)
                return

            if self.action == "export":
                result = core.export_profile(
                    destination=self.kwargs["destination"],
                    selected=self.kwargs["selected"],
                    app_version=self.window.core.config.get_version(),
                    cancelled=self.is_cancelled,
                    status=self._status,
                )
                safe_emit(self.signals, "finished", result)
                return

            if self.action == "import":
                result = core.import_profile(
                    zip_path=self.kwargs["zip_path"],
                    target_dir=self.kwargs["target_dir"],
                    selected=self.kwargs["selected"],
                    cancelled=self.is_cancelled,
                    status=self._status,
                    commit_started=self._commit_started,
                )
                safe_emit(self.signals, "finished", result)
                return

            raise RuntimeError(f"Unknown profile exporter worker action: {self.action}")

        except ProfileExportCancelled:
            safe_emit(self.signals, "cancelled")
        except Exception as exc:
            safe_emit(self.signals, "error", exc)
        finally:
            self.cleanup()

    def cleanup(self):
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass
