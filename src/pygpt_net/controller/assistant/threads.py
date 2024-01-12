#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

import json
import time

from PySide6.QtCore import QObject, Signal, Slot, QRunnable

from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Threads:
    def __init__(self, window=None):
        """
        Assistant threads controller

        :param window: Window instance
        """
        self.window = window
        self.started = False
        self.stop = False

    def create_thread(self):
        """
        Create assistant thread

        :return: thread id
        :rtype: str
        """
        thread_id = self.window.core.gpt.assistants.thread_create()
        self.window.core.config.set('assistant_thread', thread_id)
        self.window.core.ctx.append_thread(thread_id)
        return thread_id

    def handle_messages(self, ctx: CtxItem):
        """
        Handle run messages

        :param ctx: CtxItem
        """
        data = self.window.core.gpt.assistants.msg_list(ctx.thread)
        for msg in data:
            if msg.role == "assistant":
                ctx.set_output(msg.content[0].text.value)
                paths = self.window.controller.assistant.files.handle_received(ctx, msg)
                if paths:
                    ctx.files = list(paths)  # append files paths list to ctx

                # update ctx
                self.window.core.ctx.update_item(ctx)

                self.window.controller.chat.output.handle(ctx, 'assistant', False)
                self.window.controller.chat.output.handle_cmd(ctx)

                # update ctx
                self.window.core.ctx.update_item(ctx)

                # index ctx (llama-index)
                self.window.controller.idx.on_ctx_end(ctx)

                # update ctx list
                self.window.controller.ctx.update()
                break

    def handle_run(self, ctx: CtxItem):
        """
        Handle assistant's run

        :param ctx: CtxItem
        """
        # worker
        worker = RunWorker()
        worker.window = self.window
        worker.ctx = ctx

        # signals
        worker.signals.updated.connect(self.handle_status)
        worker.signals.destroyed.connect(self.handle_destroy)
        worker.signals.started.connect(self.handle_started)

        # start
        self.window.threadpool.start(worker)
        self.started = True

    @Slot(str, object)
    def handle_status(self, status: str, ctx: CtxItem):
        """
        Insert text to input and send

        :param status: status
        :param ctx: CtxItem
        """
        print("Run status: {}".format(status))
        if status != "queued" and status != "in_progress":
            self.window.controller.chat.common.unlock_input()  # unlock input
        if status == "completed":
            self.stop = False
            self.handle_messages(ctx)
            self.window.statusChanged.emit(trans('assistant.run.completed'))
        elif status == "failed":
            self.stop = False
            self.window.controller.chat.common.unlock_input()
            self.window.statusChanged.emit(trans('assistant.run.failed'))

    @Slot()
    def handle_destroy(self):
        """Handle thread destroy"""
        self.started = False
        self.stop = False

    @Slot()
    def handle_started(self):
        """Handle listening started"""
        print("Run: assistant is listening status...")
        self.window.statusChanged.emit(trans('assistant.run.listening'))


class RunSignals(QObject):
    updated = Signal(object, object)
    destroyed = Signal()
    started = Signal()


class RunWorker(QRunnable):
    def __init__(self, *args, **kwargs):
        super(RunWorker, self).__init__()
        self.signals = RunSignals()
        self.args = args
        self.kwargs = kwargs
        self.window = None
        self.ctx = None
        self.check = True
        self.stop_reasons = [
            "cancelling",
            "cancelled",
            "failed",
            "completed",
            "expired",
            "requires_action",
        ]

    @Slot()
    def run(self):
        """Run thread"""
        try:
            self.signals.started.emit()
            while self.check \
                    and not self.window.is_closing \
                    and not self.window.controller.assistant.threads.stop:
                status = self.window.core.gpt.assistants.run_status(self.ctx.thread, self.ctx.run_id)
                self.signals.updated.emit(status, self.ctx)
                # finished or failed
                if status in self.stop_reasons:
                    self.check = False
                    self.signals.destroyed.emit()
                    break
                time.sleep(1)
            self.signals.destroyed.emit()
        except Exception as e:
            self.window.core.debug.log(e)
            self.signals.destroyed.emit()
