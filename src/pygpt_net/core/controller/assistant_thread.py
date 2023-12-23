#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.19 02:00:00                  #
# ================================================== #
import threading
import time

from PySide6.QtCore import QObject, Signal, Slot

from ..utils import trans


class AssistantThread:
    def __init__(self, window=None):
        """
        Assistant thread  controller

        :param window: Window instance
        """
        self.window = window
        self.thread_run = None
        self.thread_run_started = False
        self.force_stop = False

    def create_thread(self):
        """
        Create assistant thread

        :return: thread id
        :rtype: str
        """
        thread_id = self.window.app.gpt_assistants.thread_create()
        self.window.config.set('assistant_thread', thread_id)
        self.window.app.context.append_thread(thread_id)
        return thread_id

    def handle_run_messages(self, ctx):
        """
        Handle run messages

        :param ctx: ContextItem
        """
        data = self.window.app.gpt_assistants.msg_list(ctx.thread)
        for msg in data:
            if msg.role == "assistant":
                ctx.set_output(msg.content[0].text.value)
                self.window.controller.assistant_files.handle_message_files(msg)
                self.window.controller.output.handle_response(ctx, 'assistant', False)
                self.window.controller.output.handle_commands(ctx)
                break

    def handle_run(self, ctx):
        """
        Handle assistant's run

        :param ctx: ContextItem
        """
        listener = AssistantRunThread(window=self.window, ctx=ctx)
        listener.updated.connect(self.handle_status)
        listener.destroyed.connect(self.handle_destroy)
        listener.started.connect(self.handle_started)

        self.thread_run = threading.Thread(target=listener.run)
        self.thread_run.start()
        self.thread_run_started = True

    @Slot(str, object)
    def handle_status(self, status, ctx):
        """
        Insert text to input and send

        :param status: status
        :param ctx: ContextItem
        """
        print("Run status: {}".format(status))
        if status != "queued" and status != "in_progress":
            self.window.controller.input.unlock_input()  # unlock input
        if status == "completed":
            self.force_stop = False
            self.handle_run_messages(ctx)
            self.window.statusChanged.emit(trans('assistant.run.completed'))
        elif status == "failed":
            self.force_stop = False
            self.window.controller.input.unlock_input()
            self.window.statusChanged.emit(trans('assistant.run.failed'))

    @Slot()
    def handle_destroy(self):
        """
        Handle thread destroy
        """
        self.thread_run_started = False
        self.force_stop = False

    @Slot()
    def handle_started(self):
        """
        Handle listening started
        """
        print("Run: assistant is listening status...")
        self.window.statusChanged.emit(trans('assistant.run.listening'))


class AssistantRunThread(QObject):
    updated = Signal(object, object)
    destroyed = Signal()
    started = Signal()

    def __init__(self, window=None, ctx=None):
        """
        Run assistant run status check thread

        :param window: Window instance
        :param ctx: ContextItem
        """
        super().__init__()
        self.window = window
        self.ctx = ctx
        self.check = True
        self.stop_reasons = [
            "cancelling",
            "cancelled",
            "failed",
            "completed",
            "expired",
            "requires_action",
        ]

    def run(self):
        """Run thread"""
        try:
            self.started.emit()
            while self.check \
                    and not self.window.is_closing \
                    and not self.window.controller.assistant_thread.force_stop:
                status = self.window.app.gpt_assistants.run_status(self.ctx.thread, self.ctx.run_id)
                self.updated.emit(status, self.ctx)
                # finished or failed
                if status in self.stop_reasons:
                    self.check = False
                    self.destroyed.emit()
                    break
                time.sleep(1)
            self.destroyed.emit()
        except Exception as e:
            self.window.app.error.log(e)
            self.destroyed.emit()
