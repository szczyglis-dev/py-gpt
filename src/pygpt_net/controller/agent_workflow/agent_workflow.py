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

from PySide6.QtCore import QObject, Signal

from pygpt_net.core.qt import safe_emit


class AgentWorkflowSignals(QObject):
    changed = Signal(object)
    reload = Signal()
    run_started = Signal()


class AgentWorkflow:
    """Qt bridge for the runtime Agent Workflow monitor."""

    def __init__(self, window=None):
        self.window = window
        self.signals = AgentWorkflowSignals()

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

    def publish(self, snapshot: dict):
        safe_emit(self.signals, "changed", snapshot)

    def reload(self):
        safe_emit(self.signals, "reload")

    def on_run_started(self):
        safe_emit(self.signals, "run_started")

    def clear(self):
        self.window.core.agent_workflow.clear()
