#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from pygpt_net.core.qt import safe_emit
from pygpt_net.utils import trans


class ConnectorsWorkerSignals(QObject):
    finished = Signal(str, object)
    error = Signal(str, object)
    status = Signal(str)


class ConnectorsWorker(QRunnable):
    def __init__(self, window, action: str, **kwargs):
        super().__init__()
        self.window = window
        self.action = action
        self.kwargs = kwargs
        self.signals = ConnectorsWorkerSignals()

    @Slot()
    def run(self):
        try:
            core = self.window.core.connectors
            if self.action == "catalog":
                safe_emit(self.signals, "status", trans("connectors.status.loading_catalog"))
                result = core.fetch_catalog(self.kwargs.get("url"))
                safe_emit(self.signals, "finished", self.action, result)
                return
            if self.action == "import_github":
                safe_emit(self.signals, "status", trans("connectors.status.importing"))
                result = core.import_github(self.kwargs["url"])
                safe_emit(self.signals, "finished", self.action, result)
                return
            if self.action == "import_local":
                safe_emit(self.signals, "status", trans("connectors.status.importing"))
                result = core.import_local(self.kwargs["path"])
                safe_emit(self.signals, "finished", self.action, result)
                return
            if self.action == "install_catalog_many":
                imported = []
                entries = list(self.kwargs.get("entries") or [])
                total = len(entries)
                for idx, entry in enumerate(entries, start=1):
                    safe_emit(
                        self.signals,
                        "status",
                        trans("connectors.status.installing_n").format(current=idx, total=total),
                    )
                    imported.extend(core.install_catalog_entry(entry))
                safe_emit(self.signals, "finished", self.action, imported)
                return
            raise RuntimeError(f"Unknown connectors worker action: {self.action}")
        except Exception as exc:
            safe_emit(self.signals, "error", self.action, exc)
        finally:
            self.cleanup()

    def cleanup(self):
        signals = self.signals
        self.signals = None
        if signals is not None:
            try:
                signals.deleteLater()
            except RuntimeError:
                pass
