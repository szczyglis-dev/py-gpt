#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.02 04:00:00                  #
# ================================================== #

from PySide6.QtCore import QObject, Signal, Slot
from pygpt_net.core.worker import Worker
from pygpt_net.item.ctx import CtxItem


class WorkerSignals(QObject):
    updated = Signal(int, str)


class Summarizer:
    def __init__(self, window=None):
        """
        Summarize  controller

        :param window: Window instance
        """
        self.window = window

    def summarize(self, id: int, ctx: CtxItem):
        """
        Summarize context

        :param id: CtxMeta ID
        :param ctx: CtxItem
        """
        self.start_worker(id, ctx)

    def summarizer(self, id: int, ctx: CtxItem, window, updated_signal: Signal):
        """
        Summarize worker callback

        :param id: CtxMeta ID
        :param ctx: CtxItem
        :param window: Window instance
        :param updated_signal: WorkerSignals: updated signal
        """
        title = window.core.gpt.summarizer.summary_ctx(ctx)
        if title:
            updated_signal.emit(id, title)

    def start_worker(self, id: int, ctx: CtxItem):
        """
        Handle worker thread

        :param id: CtxMeta ID
        :param ctx: CtxItem
        """
        worker = Worker(self.summarizer)
        worker.signals = WorkerSignals()
        worker.signals.updated.connect(self.handle_update)
        worker.kwargs['id'] = id
        worker.kwargs['ctx'] = ctx
        worker.kwargs['window'] = self.window
        worker.kwargs['updated_signal'] = worker.signals.updated
        self.window.threadpool.start(worker)

    @Slot(int, str)
    def handle_update(self, id: int, title: str):
        """
        Handle update signal (make update)

        :param id: CtxMeta ID
        :param title: CtxMeta title
        """
        self.window.controller.ctx.update_name(id, title)

