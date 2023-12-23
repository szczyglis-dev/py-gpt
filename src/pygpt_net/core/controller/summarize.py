#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.19 21:00:00                  #
# ================================================== #
import threading

from PySide6.QtCore import QObject, Signal, Slot


class Summarize:
    def __init__(self, window=None):
        """
        Summarize  controller

        :param window: Window instance
        """
        self.window = window
        self.thread = None
        self.thread_started = False

    def summarize_ctx(self, id, ctx):
        """
        Summarize context

        :param ctx: CtxItem
        """
        self.start_thread(id, ctx)

    def start_thread(self, id, ctx):
        """
        Handle thread start

        :param ctx: CtxItem
        """
        summarizer = SummarizeThread(window=self.window, id=id, ctx=ctx)
        summarizer.updated.connect(self.handle_update)
        summarizer.destroyed.connect(self.handle_destroy)

        self.thread = threading.Thread(target=summarizer.run)
        self.thread.start()
        self.thread_started = True

    @Slot(str, str)
    def handle_update(self, id, title):
        """
        Handle thread name update
        :param id: ctx id
        :param title: generated title
        """
        self.window.controller.context.update_name(id, title)
        self.thread_started = False

    @Slot()
    def handle_destroy(self):
        """Handle thread destroy"""
        self.thread_started = False


class SummarizeThread(QObject):
    updated = Signal(object, object)
    destroyed = Signal()

    def __init__(self, window=None, id=None, ctx=None):
        """
        Run summarize thread

        :param window: Window instance
        :param ctx: CtxItem
        """
        super().__init__()
        self.window = window
        self.id = id
        self.ctx = ctx

    def run(self):
        """Run thread"""
        try:
            title = self.window.app.gpt.prepare_ctx_name(self.ctx)
            if title is not None and title != "":
                self.updated.emit(self.id, title)
        except Exception as e:
            self.window.app.error.log(e)
        self.destroyed.emit()
