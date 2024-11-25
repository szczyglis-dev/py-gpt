#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.25 02:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, Signal, QObject

from pygpt_net.core.events import RenderEvent
from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals
from pygpt_net.utils import trans

class Builder(QObject):
    def __init__(self, plugin=None):
        super(Builder, self).__init__()
        self.plugin = plugin
        self.worker = None

    def build_and_restart(self):
        """Run IPython image build and restart container"""
        self.build_image(restart=True)

    def build_image(self, restart: bool = False):
        """
        Run IPython image build

        :param restart: Restart container
        """
        try:
            self.worker = Worker()
            self.worker.plugin = self.plugin
            self.worker.restart = restart
            self.worker.signals.build_finished.connect(self.handle_build_finished)
            self.worker.signals.error.connect(self.handle_build_failed)
            self.plugin.window.threadpool.start(self.worker)
        except Exception as e:
            self.plugin.window.ui.dialogs.alert(e)

    @Slot()
    def handle_build_finished(self):
        """Handle build finished"""
        self.plugin.window.ui.dialogs.alert(trans('ipython.docker.build.finish'))
        self.plugin.window.update_status(trans('ipython.docker.build.finish'))
        self.plugin.window.controller.kernel.stop()
        event = RenderEvent(RenderEvent.END)
        self.plugin.window.dispatch(event)

    @Slot(object)
    def handle_build_failed(self, error):
        """Handle build failed"""
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
            self.plugin.get_interpreter().build_image()
            if self.restart:
                self.plugin.get_interpreter().restart()
            self.signals.build_finished.emit()
        except Exception as e:
            self.signals.error.emit(e)
