#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.11 14:00:00                  #
# ================================================== #

from typing import Any

from PySide6.QtCore import Signal, Slot, QObject

from pygpt_net.core.events import RenderEvent
from pygpt_net.plugin.base.signals import BaseSignals
from pygpt_net.plugin.base.worker import BaseWorker
from pygpt_net.utils import trans


class Builder(QObject):
    def __init__(self, plugin=None):
        super(Builder, self).__init__()
        self.plugin = plugin
        self.docker = None
        self.worker = None

    def build_image(self, restart: bool = False):
        """Run image build"""
        try:            
            self.plugin.window.update_status("Please wait... building...")
            self.worker = Worker()
            self.worker.plugin = self.plugin
            self.worker.docker = self.docker
            self.worker.restart = restart
            self.worker.signals.build_finished.connect(self.handle_build_finished)
            self.worker.signals.error.connect(self.handle_build_failed)
            self.plugin.window.threadpool.start(self.worker)
        except Exception as e:
            self.plugin.window.ui.dialogs.alert(e)

    @Slot()
    def handle_build_finished(self):
        """Handle build finished"""
        self.plugin.window.ui.dialogs.alert(trans('docker.build.finish'))
        self.plugin.window.update_status(trans('docker.build.finish'))
        self.plugin.window.controller.kernel.stop()
        event = RenderEvent(RenderEvent.END)
        self.plugin.window.dispatch(event)


    @Slot(object)
    def handle_build_failed(self, error: Any):
        """
        Handle build failed

        :param error: error
        """
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
        self.docker = None
        self.plugin = None
        self.restart = False

    @Slot()
    def run(self):
        try:
            self.docker.build_image()
            self.signals.build_finished.emit()
            if self.restart:
                self.docker.restart()
        except Exception as e:
            self.signals.error.emit(e)
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources after worker execution."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass