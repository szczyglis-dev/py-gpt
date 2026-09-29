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

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from pygpt_net.core.qt import safe_emit
from pygpt_net.utils import trans


class ExtensionsWorkerSignals(QObject):
    finished = Signal(str, object)
    error = Signal(str, object)
    status = Signal(str)


class ExtensionsWorker(QRunnable):
    def __init__(self, window, action: str, **kwargs):
        super().__init__()
        self.window = window
        self.action = action
        self.kwargs = kwargs
        self.signals = ExtensionsWorkerSignals()

    @Slot()
    def run(self):
        try:
            core = self.window.core.extensions
            if self.action == "registry":
                safe_emit(self.signals, "status", trans("extensions.status.loading_registry"))
                result = core.fetch_registry(self.kwargs.get("url"))
            elif self.action == "import_zip":
                safe_emit(self.signals, "status", trans("extensions.status.importing"))
                result = core.import_zip(self.kwargs["path"])
            elif self.action == "import_directory":
                safe_emit(self.signals, "status", trans("extensions.status.importing"))
                result = core.import_directory(self.kwargs["path"])
            elif self.action == "import_github":
                safe_emit(self.signals, "status", trans("extensions.status.importing"))
                result = core.import_github(self.kwargs["url"])
            elif self.action == "install_registry_many":
                entries = list(self.kwargs.get("entries") or [])
                imported = []
                total = len(entries)
                for idx, entry in enumerate(entries, start=1):
                    safe_emit(
                        self.signals,
                        "status",
                        trans("extensions.status.installing_n").format(current=idx, total=total),
                    )
                    imported.append(core.install_registry_entry(entry))
                result = imported
            else:
                raise RuntimeError(f"Unknown add-ons worker action: {self.action}")
            safe_emit(self.signals, "finished", self.action, result)
        except Exception as exc:
            safe_emit(self.signals, "error", self.action, exc)
        finally:
            signals = self.signals
            self.signals = None
            if signals is not None:
                try:
                    signals.deleteLater()
                except RuntimeError:
                    pass
