#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.03 14:00:00                  #
# ================================================== #

from PySide6.QtCore import QRunnable, Slot, QObject, Signal


class Worker(QObject, QRunnable):
    def __init__(self, fn, *args, **kwargs):
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self):
        self.fn(*self.args, **self.kwargs)


class WorkerSignals(QObject):
    updated = Signal(object)
    finished = Signal(object)
