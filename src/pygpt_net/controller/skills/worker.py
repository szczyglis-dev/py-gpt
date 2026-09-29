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

from urllib.parse import urljoin

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from pygpt_net.core.qt import safe_emit
from pygpt_net.utils import trans


class SkillsWorkerSignals(QObject):
    finished = Signal(str, object)
    error = Signal(str, object)
    status = Signal(str)


class SkillsWorker(QRunnable):
    def __init__(self, window, action: str, **kwargs):
        super().__init__()
        self.window = window
        self.action = action
        self.kwargs = kwargs
        self.signals = SkillsWorkerSignals()

    @Slot()
    def run(self):
        try:
            core = self.window.core.skills
            if self.action == "catalog":
                url = self.kwargs.get("url") or core.get_catalog_url()
                safe_emit(self.signals, "status", trans("skills.status.loading_catalog"))
                entries = core.fetch_catalog(url)
                # Icons are optional. Download them in the worker and keep the UI
                # thread free from network I/O. A broken icon never rejects the row.
                for entry in entries[:200]:
                    icon = str(entry.get("icon") or "").strip()
                    if not icon:
                        continue
                    try:
                        icon_url = urljoin(url, icon)
                        entry["_icon_bytes"] = core.fetch_icon(icon_url)
                    except Exception:
                        entry["_icon_bytes"] = b""
                safe_emit(self.signals, "finished", self.action, entries)
                return

            if self.action == "import_github":
                safe_emit(self.signals, "status", trans("skills.status.importing_github"))
                result = core.import_github(
                    self.kwargs["url"],
                    enable=self.kwargs.get("enable", True),
                )
                safe_emit(self.signals, "finished", self.action, result)
                return

            if self.action == "import_local":
                safe_emit(self.signals, "status", trans("skills.status.importing_local"))
                result = core.import_local(
                    self.kwargs["path"],
                    enable=self.kwargs.get("enable", True),
                )
                safe_emit(self.signals, "finished", self.action, result)
                return

            if self.action == "install_catalog":
                safe_emit(self.signals, "status", trans("skills.status.installing"))
                result = core.install_catalog_entry(
                    self.kwargs["entry"],
                    enable=self.kwargs.get("enable", True),
                )
                safe_emit(self.signals, "finished", self.action, result)
                return

            if self.action == "install_catalog_many":
                entries = list(self.kwargs.get("entries") or [])
                imported = []
                total = len(entries)
                for idx, entry in enumerate(entries, start=1):
                    safe_emit(
                        self.signals,
                        "status",
                        trans("skills.status.installing_n").format(current=idx, total=total),
                    )
                    imported.extend(core.install_catalog_entry(
                        entry,
                        enable=self.kwargs.get("enable", True),
                    ))
                safe_emit(self.signals, "finished", self.action, imported)
                return

            raise RuntimeError(f"Unknown skills worker action: {self.action}")
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
