#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.17 14:45:00                  #
# ================================================== #

import threading

from PySide6.QtCore import QObject, Signal, Slot, QTimer

from pygpt_net.core.qt import safe_emit


class AgentWorkflowSignals(QObject):
    changed = Signal(object)
    reload = Signal()
    run_started = Signal()
    invalidated = Signal()


class AgentWorkflow(QObject):
    """Qt bridge for the runtime Agent Workflow monitor."""

    def __init__(self, window=None):
        super().__init__()
        self.window = window
        self.signals = AgentWorkflowSignals(self)
        self._publish_lock = threading.Lock()
        self._publish_pending = False
        self._publish_timer = QTimer(self)
        self._publish_timer.setSingleShot(True)
        self._publish_timer.setInterval(250)
        self._publish_timer.timeout.connect(self._flush_publish)
        self.signals.invalidated.connect(self._schedule_publish)

    def setup(self):
        self.signals.run_started.connect(self._on_run_started)

    def _on_run_started(self):
        """Show the Agent Workflow onboarding only after a real Agents v2 run begins."""
        try:
            tool = self.window.tools.get("agent_workflow")
            if tool is not None:
                tool.show_on_first_agent_run()
        except Exception:
            pass

    def publish(self):
        """Queue one lightweight notification, even when producers outrun Qt."""
        with self._publish_lock:
            if self._publish_pending:
                return
            self._publish_pending = True
        safe_emit(self.signals, "invalidated")

    @Slot()
    def _schedule_publish(self):
        self._publish_timer.start()

    @Slot()
    def _flush_publish(self):
        with self._publish_lock:
            self._publish_pending = False
        # Visible views pull the latest state; hidden views allocate no snapshots.
        safe_emit(self.signals, "changed", None)

    def reload(self):
        safe_emit(self.signals, "reload")

    def on_run_started(self):
        safe_emit(self.signals, "run_started")

    def clear(self):
        self.window.core.agent_workflow.clear()
