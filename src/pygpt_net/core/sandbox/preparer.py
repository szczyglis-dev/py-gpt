#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub: https://github.com/szczyglis-dev/py-gpt    #
# MIT License                                        #
# ================================================== #

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from pygpt_net.core.qt import safe_emit
from pygpt_net.utils import trans


class BuiltinSandboxPrepareSignals(QObject):
    finished = Signal(object)
    error = Signal(object, object)


class BuiltinSandboxPrepareWorker(QRunnable):
    """Provision one Built-in sandbox environment outside the GUI thread."""

    def __init__(self, runtime, force: bool = False):
        super().__init__()
        self.runtime = runtime
        self.force = bool(force)
        self.signals = BuiltinSandboxPrepareSignals()

    @Slot()
    def run(self):
        try:
            self.runtime.ensure_ready(force=self.force)
            safe_emit(self.signals, "finished", self.runtime)
        except Exception as exc:
            safe_emit(self.signals, "error", self.runtime, exc)


class BuiltinSandboxPreparer(QObject):
    """Show the heavy-operation loader and provision a sandbox asynchronously."""

    start_requested = Signal(object)

    def __init__(self, plugin, label: str):
        super().__init__(plugin)
        self.plugin = plugin
        self.label = label
        self.worker = None
        self._loader_active = False
        self._pending = False
        self._request = None
        self._lock = threading.RLock()
        self.start_requested.connect(self._start)

    def prepare(self, runtime) -> bool:
        """Schedule preparation once. Return True while preparation is needed."""
        if runtime.is_ready():
            return False
        return self._schedule(runtime, force=False, manual=False)

    def rebuild(self, runtime) -> bool:
        """Force recreation of the selected Built-in venv in the background."""
        return self._schedule(runtime, force=True, manual=True)

    def _schedule(self, runtime, force: bool, manual: bool) -> bool:
        with self._lock:
            if self._pending:
                return False if manual else True
            self._pending = True
        request = {
            "runtime": runtime,
            "force": bool(force),
            "manual": bool(manual),
        }
        self.start_requested.emit(request)
        return True

    def is_preparing(self) -> bool:
        with self._lock:
            return self._pending

    @Slot(object)
    def _start(self, request):
        runtime = request["runtime"]
        force = bool(request.get("force"))
        manual = bool(request.get("manual"))
        self._request = request

        if not force and runtime.is_ready():
            self._finish_state()
            return

        if manual:
            message = trans("sandbox.builtin.rebuild.start")
        else:
            message = f"Preparing Built-in sandbox environment: {self.label}..."
        print(f"[BUILT-IN SANDBOX] {message}")
        try:
            dialog = self.plugin.window.ui.dialogs.show_loader(
                message=message,
                show_cancel=False,
                modal=True,
            )
            self._loader_active = dialog is not None
        except Exception as exc:
            self._loader_active = False
            self.plugin.window.core.debug.log(exc)

        worker = BuiltinSandboxPrepareWorker(runtime, force=force)
        worker.signals.finished.connect(self._finished)
        worker.signals.error.connect(self._failed)
        self.worker = worker
        self.plugin.window.threadpool.start(worker)

    def _close_loader(self):
        if not self._loader_active:
            return
        self._loader_active = False
        try:
            self.plugin.window.ui.dialogs.finish_loader()
        except Exception as exc:
            self.plugin.window.core.debug.log(exc)

    def _finish_state(self):
        with self._lock:
            self._pending = False
        self.worker = None
        self._request = None

    @Slot(object)
    def _finished(self, runtime):
        request = self._request or {}
        manual = bool(request.get("manual"))
        self._close_loader()
        self._finish_state()
        if manual:
            message = trans("sandbox.builtin.rebuild.finish")
            print(f"[BUILT-IN SANDBOX] {message} ({runtime.venv_root})")
            try:
                self.plugin.window.ui.dialogs.alert(message)
            except Exception:
                pass
        else:
            message = f"Built-in sandbox environment ready: {self.label}"
            print(f"[BUILT-IN SANDBOX] {message} ({runtime.venv_root})")
        try:
            self.plugin.window.update_status(message)
        except Exception:
            pass

    @Slot(object, object)
    def _failed(self, runtime, error):
        request = self._request or {}
        manual = bool(request.get("manual"))
        self._close_loader()
        self._finish_state()
        message = f"Unable to prepare Built-in sandbox environment ({self.label}): {error}"
        print(f"[BUILT-IN SANDBOX] ERROR: {message}")
        try:
            self.plugin.window.core.debug.log(error)
        except Exception:
            pass
        try:
            self.plugin.window.update_status(message)
        except Exception:
            pass
        if manual:
            try:
                self.plugin.window.ui.dialogs.alert(str(error))
            except Exception:
                pass
