#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.16 05:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, Signal, QObject

from pygpt_net.plugin.base import BaseWorker, BaseSignals
from pygpt_net.utils import trans

class Builder(QObject):
    def __init__(self, plugin=None):
        super(Builder, self).__init__()
        self.plugin = plugin
        self.worker = None

    def build_image(self):
        """Run IPython image build"""
        try:
            self.worker = Worker()
            self.worker.plugin = self.plugin
            self.worker.signals.build_finished.connect(self.handle_build_finished)
            self.worker.signals.error.connect(self.handle_build_failed)
            self.plugin.window.threadpool.start(self.worker)
        except Exception as e:
            self.plugin.window.ui.dialogs.alert(e)

    @Slot()
    def handle_build_finished(self):
        """Handle build finished"""
        self.plugin.window.ui.dialogs.alert(trans('ipython.docker.build.finish'))
        self.plugin.window.ui.status(trans('ipython.docker.build.finish'))

    @Slot(object)
    def handle_build_failed(self, error):
        """Handle build failed"""
        self.plugin.window.ui.dialogs.alert(str(error))
        self.plugin.window.ui.status(str(error))

class WorkerSignals(BaseSignals):
    build_finished = Signal()

class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None

    @Slot()
    def run(self):
        try:
            self.plugin.ipython.build_image()
            self.signals.build_finished.emit()
        except Exception as e:
            self.signals.error.emit(e)
