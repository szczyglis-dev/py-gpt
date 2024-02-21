#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.21 01:00:00                  #
# ================================================== #

from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.item.ctx import CtxItem


class AssistantsWorker:
    def __init__(self, window=None):
        """
        Assistants Worker (async)

        :param window: Window instance
        """
        self.window = window

    @Slot(object, object)
    def handle_error(self, ctx: CtxItem, err: any):
        """
        Handle thread error signal

        :param ctx: context item
        :param err: error message
        """
        self.window.controller.assistant.threads.handle_run_error(ctx, err)

    @Slot(object, object)
    def handle_run_created(self, ctx: CtxItem, run):
        """
        Handle thread finished signal

        :param ctx: context item
        :param run
        """
        self.window.controller.assistant.threads.handle_run_created(ctx, run)

    def create_run(
            self,
            ctx: CtxItem,
            thread_id: str,
            assistant_id: str,
            system_prompt: str
    ):
        """
        Create assistant run

        :param ctx: context item
        :param thread_id: thread id
        :param assistant_id: assistant id
        :param system_prompt: system prompt
        """
        worker = Worker()
        worker.window = self.window
        worker.mode = "run_create"
        worker.ctx = ctx
        worker.thread_id = thread_id
        worker.assistant_id = assistant_id
        worker.system_prompt = system_prompt
        worker.signals.finished.connect(self.handle_run_created)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)

    def msg_send(
            self,
            ctx: CtxItem,
            thread_id: str,
            assistant_id: str,
            prompt: str,
            system_prompt: str
    ):
        """
        Send message to assistant thread

        :param ctx: context item
        :param thread_id: thread id
        :param assistant_id: assistant id
        :param prompt: prompt
        :param system_prompt: system prompt
        """
        worker = Worker()
        worker.window = self.window
        worker.mode = "msg_send"
        worker.ctx = ctx
        worker.thread_id = thread_id
        worker.assistant_id = assistant_id
        worker.prompt = prompt
        worker.system_prompt = system_prompt
        worker.signals.finished.connect(self.handle_run_created)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)

    def tools_submit(
            self,
            ctx: CtxItem,
            tools_outputs: list,
    ):
        """
        Send tools outputs to assistant thread

        :param ctx: context item
        :param tools_outputs: list of tools outputs
        """
        worker = Worker()
        worker.window = self.window
        worker.mode = "tools_submit"
        worker.ctx = ctx
        worker.tools_outputs = tools_outputs
        worker.signals.finished.connect(self.handle_run_created)
        worker.signals.error.connect(self.handle_error)
        self.window.threadpool.start(worker)


class WorkerSignals(QObject):
    finished = Signal(object, object)
    error = Signal(object, object)


class Worker(QRunnable):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.window = None
        self.mode = None
        self.thread_id = None
        self.assistant_id = None
        self.prompt = None
        self.system_prompt = None
        self.tools_outputs = None
        self.ctx = None

    @Slot()
    def run(self):
        """Assistants worker thread"""
        if self.mode == "run_create":
            self.run_create()
        elif self.mode == "msg_send":
            self.msg_send()
        elif self.mode == "tools_submit":
            self.tools_submit()

    def run_create(self) -> bool:
        """
        Create assistant run

        :return: result
        """
        try:
            run = self.window.core.gpt.assistants.run_create(
                self.thread_id,
                self.assistant_id,
                self.system_prompt,
            )
            if run is not None:
                self.signals.finished.emit(self.ctx, run)
                return True
        except Exception as e:
            self.signals.error.emit(self.ctx, e)
        return False

    def msg_send(self) -> bool:
        """
        Send message to assistant

        :return: result
        """
        try:
            response = self.window.core.gpt.assistants.msg_send(
                self.thread_id,
                self.prompt,
            )
            if response is not None:
                self.ctx.msg_id = response.id
                return self.run_create()
        except Exception as e:
            self.signals.error.emit(self.ctx, e)
        return False

    def tools_submit(self) -> bool:
        """
        Submit tools outputs to assistant

        :return: result
        """
        try:
            run = self.window.core.gpt.assistants.run_submit_tool(self.ctx, self.tools_outputs)
            if run is not None:
                self.ctx.run_id = run.id  # update run id
                self.signals.finished.emit(self.ctx, run)  # continue status check
        except Exception as e:
            self.signals.error.emit(self.ctx, e)
        return False
