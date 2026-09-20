#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.04 14:55:00                  #
# ================================================== #

from PySide6.QtCore import Slot, Signal, QObject

from pygpt_net.core.qt import safe_emit
from pygpt_net.core.events import RenderEvent
from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals
from pygpt_net.utils import trans

class Builder(QObject):
    def __init__(self, plugin=None):
        super(Builder, self).__init__()
        self.plugin = plugin
        self.worker = None
        self._loader_active = False

    def _start_loader(self):
        """Show the shared heavy-operation loader for an IPython image build."""
        dialog = self.plugin.window.ui.dialogs.show_loader(
            message=trans('ipython.docker.build.start'),
            show_cancel=False,
            modal=True,
        )
        self._loader_active = dialog is not None

    def _finish_loader(self):
        """Close the shared Docker-build loader if this builder opened it."""
        if not self._loader_active:
            return
        self._loader_active = False
        self.plugin.window.ui.dialogs.finish_loader()

    def build_and_restart(self):
        """Run IPython image build and restart container"""
        self.build_image(restart=True)

    def build_image(self, restart: bool = False):
        """
        Run IPython image build

        :param restart: Restart container
        """
        try:
            self.plugin.migrate_docker_defaults()
            self.plugin.window.update_status(trans('ipython.docker.build.start'))
            self._start_loader()
            self.worker = Worker()
            self.worker.plugin = self.plugin
            self.worker.restart = restart
            self.worker.signals.build_finished.connect(self.handle_build_finished)
            self.worker.signals.error.connect(self.handle_build_failed)
            self.plugin.window.threadpool.start(self.worker)
        except Exception as e:
            self._finish_loader()
            self.plugin.window.ui.dialogs.alert(e)

    @Slot()
    def handle_build_finished(self):
        """Handle build finished"""
        self._finish_loader()
        self.plugin.window.ui.dialogs.alert(trans('ipython.docker.build.finish'))
        self.plugin.window.update_status(trans('ipython.docker.build.finish'))
        self.plugin.window.controller.kernel.stop()
        event = RenderEvent(RenderEvent.END)
        self.plugin.window.dispatch(event)

    @Slot(object)
    def handle_build_failed(self, error):
        """Handle build failed"""
        self._finish_loader()
        self.plugin.window.ui.dialogs.alert(str(error))
        self.plugin.window.update_status(str(error))
        self.plugin.window.controller.kernel.stop()
        event = RenderEvent(RenderEvent.END)
        self.plugin.window.dispatch(event)

class WorkerSignals(BaseSignals):
    build_finished = Signal()

class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.restart = False

    @Slot()
    def run(self):
        try:
            interpreter = self.plugin.ipython_docker
            interpreter.build_image()
            if self.restart and self.plugin.get_option_value("sandbox_ipython"):
                interpreter.restart()
            safe_emit(self.signals, "build_finished")
        except Exception as e:
            safe_emit(self.signals, "error", e)
