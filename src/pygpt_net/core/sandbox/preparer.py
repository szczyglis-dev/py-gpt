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


class BuiltinSandboxPrepareSignals(QObject):
    finished = Signal(object)
    error = Signal(object, object)


class BuiltinSandboxPrepareWorker(QRunnable):
    """Provision one Built-in sandbox environment outside the GUI thread."""

    def __init__(self, runtime):
        super().__init__()
        self.runtime = runtime
        self.signals = BuiltinSandboxPrepareSignals()

    @Slot()
    def run(self):
        try:
            self.runtime.ensure_ready()
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
        self._lock = threading.RLock()
        self.start_requested.connect(self._start)

    def prepare(self, runtime) -> bool:
        """Schedule preparation once. Return True while preparation is needed."""
        if runtime.is_ready():
            return False
        with self._lock:
            if self._pending:
                return True
            self._pending = True
        # May be emitted by a plugin worker. Because this QObject belongs to the
        # GUI thread, _start() is queued there and may safely open the dialog.
        self.start_requested.emit(runtime)
        return True

    def is_preparing(self) -> bool:
        with self._lock:
            return self._pending

    @Slot(object)
    def _start(self, runtime):
        if runtime.is_ready():
            self._finish_state()
            return

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

        worker = BuiltinSandboxPrepareWorker(runtime)
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

    @Slot(object)
    def _finished(self, runtime):
        self._close_loader()
        self._finish_state()
        message = f"Built-in sandbox environment ready: {self.label}"
        print(f"[BUILT-IN SANDBOX] {message} ({runtime.venv_root})")
        try:
            self.plugin.window.update_status(message)
        except Exception:
            pass

    @Slot(object, object)
    def _failed(self, runtime, error):
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
