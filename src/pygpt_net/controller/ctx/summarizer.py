#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.05 00:00:00                  #
# ================================================== #

from PySide6.QtCore import QObject, Signal, Slot
from pygpt_net.core.worker import Worker
from pygpt_net.item.ctx import CtxItem


class WorkerSignals(QObject):
    updated = Signal(int, object, str)
    finished = Signal(int, bool)


class Summarizer:
    def __init__(self, window=None):
        """
        Summarize  controller

        :param window: Window instance
        """
        self.window = window
        self.worker = None
        self.pending = set()

    def summarize(
            self,
            id: int,
            ctx: CtxItem
    ) -> bool:
        """
        Summarize context

        :param id: CtxMeta ID
        :param ctx: CtxItem
        :return: True if a new summarizer worker was started
        """
        if id is None or id in self.pending:
            return False

        # Mark the context synchronously before starting the worker. Streaming
        # workflow partials can call prepare_summary() repeatedly while the
        # first partial is being persisted; only the first call may start a
        # summarizer.
        self.pending.add(id)

        # make copy of ctx
        ctx_copy = CtxItem()
        ctx_copy.from_dict(ctx.to_dict())
        try:
            self.start_worker(id, ctx_copy)
        except Exception:
            self.pending.discard(id)
            raise
        return True

    def summarizer(
            self,
            id: int,
            ctx: CtxItem,
            window,
            updated_signal: Signal,
            finished_signal: Signal
    ):
        """
        Summarize worker callback

        :param id: CtxMeta ID
        :param ctx: CtxItem
        :param window: Window instance
        :param updated_signal: WorkerSignals: updated signal
        :param finished_signal: WorkerSignals: finished signal
        """
        has_title = False
        try:
            title = window.core.api.openai.summarizer.summary_ctx(ctx)
            if title:
                has_title = True
                updated_signal.emit(id, ctx, title)
        finally:
            # On success handle_update() releases the guard only after the meta
            # has been marked initialized. On failure/empty output release it
            # here, which also lets the normal end-of-turn fallback retry.
            finished_signal.emit(id, has_title)

    def start_worker(
            self,
            id: int,
            ctx: CtxItem
    ):
        """
        Handle worker thread

        :param id: CtxMeta ID
        :param ctx: CtxItem
        """
        worker = Worker(self.summarizer)
        worker.signals = WorkerSignals()
        worker.signals.updated.connect(self.handle_update)
        worker.signals.finished.connect(self.handle_finished)
        worker.kwargs['id'] = id
        worker.kwargs['ctx'] = ctx
        worker.kwargs['window'] = self.window
        worker.kwargs['updated_signal'] = worker.signals.updated
        worker.kwargs['finished_signal'] = worker.signals.finished
        self.worker = worker
        self.window.threadpool.start(worker)

    @Slot(int, bool)
    def handle_finished(self, id: int, has_title: bool):
        """Release failed/empty summary attempts so the end fallback can retry."""
        if not has_title:
            self.pending.discard(id)
            self.worker = None

    @Slot(int, object, str)
    def handle_update(
            self,
            id: int,
            ctx: CtxItem,
            title: str
    ):
        """
        Handle update signal (make update)

        :param id: CtxMeta ID
        :param ctx: CtxItem
        :param title: CtxMeta title
        """
        refresh = True
        # prevent UI list selection loose after later update
        if ctx.internal or len(ctx.cmds) > 0:
            refresh = False
        self.window.controller.ctx.update_name(
            id,
            title,
            refresh=refresh,
        )
        self.pending.discard(id)
        self.window.controller.chat.common.focus_input()  # restore focus
        self.worker = None

