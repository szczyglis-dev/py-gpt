#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 03:00:00                  #
# ================================================== #

from PySide6.QtCore import QObject, Signal
from pygpt_net.core.worker import Worker


class WorkerSignals(QObject):
    updated = Signal(str, str)


class Summarize:
    def __init__(self, window=None):
        """
        Summarize  controller

        :param window: Window instance
        """
        self.window = window

    def summarize_ctx(self, id, ctx):
        """
        Summarize context

        :param id: CtxMeta ID
        :param ctx: CtxItem
        """
        self.start_worker(id, ctx)

    def summarizer(self, id, ctx, window, updated_signal):
        """
        Summarize worker callback

        :param id: CtxMeta ID
        :param ctx: CtxItem
        :param window: Window instance
        :param updated_signal: WorkerSignals: updated signal
        """
        title = window.app.gpt.prepare_ctx_name(ctx)
        if title:
            updated_signal.emit(id, title)

    def start_worker(self, id, ctx):
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

    def handle_update(self, id, title):
        """
        Handle update signal

        :param id: CtxMeta ID
        :param title: CtxMeta title
        """
        self.window.controller.ctx.update_name(id, title)

