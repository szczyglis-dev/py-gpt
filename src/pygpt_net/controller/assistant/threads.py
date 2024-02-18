#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.18 05:00:00                  #
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
        self.run_id = None
        self.tool_calls = []  # list of previous tool calls

    def create_thread(self) -> str:
        """
        Create assistant thread

        :return: thread id
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
        paths = []
        for msg in data:
            if msg.role == "assistant":
                for content in msg.content:
                    if content.type == "text":
                        ctx.set_output(content.text.value)

                # handle files
                paths += self.window.controller.assistant.files.handle_received_ids(msg.file_ids)
                if paths:
                    ctx.files = self.window.core.filesystem.make_local_list(list(paths))
                    ctx.images = self.window.core.filesystem.make_local_list_img(list(paths))

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

    def handle_tool_calls(self, ctx: CtxItem):
        """
        Handle tool calls

        :param ctx: CtxItem
        """
        if self.is_log():
            print("Run: handling tool calls...")

        # store for submit
        self.run_id = ctx.run_id
        self.tool_calls = ctx.tool_calls

        # update ctx
        self.window.core.ctx.update_item(ctx)

        self.window.controller.chat.output.handle(ctx, 'assistant', False)
        self.window.controller.chat.output.handle_cmd(ctx)

        ctx.tool_calls = []  # clear tool calls

        # update ctx
        self.window.core.ctx.update_item(ctx)

        # index ctx (llama-index)
        self.window.controller.idx.on_ctx_end(ctx)

        # check if there are any response
        if not ctx.reply:
            results = {
                "response": "",
            }
            self.window.controller.chat.input.send(
                json.dumps(results),
                force=True,
                reply=True,
                internal=False,
            )

    def apply_outputs(self, ctx: CtxItem) -> list:
        """
        Apply tool call outputs

        :param ctx: CtxItem
        :return: list of tool calls outputs
        """
        if self.is_log():
            print("Run: preparing tool calls outputs...")

        ctx.run_id = self.run_id
        ctx.tool_calls = self.tool_calls  # set previous tool calls
        return self.window.core.command.get_tool_calls_outputs(ctx)

    def handle_run(self, ctx: CtxItem):
        """
        Handle assistant's run

        :param ctx: CtxItem
        """
        # worker
        worker = RunWorker()
        worker.window = self.window
        worker.ctx = ctx

        self.reset()  # clear previous run

        # signals
        worker.signals.updated.connect(self.handle_status)
        worker.signals.destroyed.connect(self.handle_destroy)
        worker.signals.started.connect(self.handle_started)

        self.window.stateChanged.emit(self.window.STATE_BUSY)

        if self.is_log():
            print("Run: starting run worker...")

        # start
        self.window.threadpool.start(worker)
        self.started = True

    @Slot(object, object)
    def handle_status(self, run, ctx: CtxItem):
        """
        Handle status

        :param run: Run
        :param ctx: CtxItem
        """
        status = None
        if run:
            status = run.status

        if self.is_log():
            print("Run status: {}".format(status))

        if status != "queued" and status != "in_progress":
            self.window.controller.chat.common.unlock_input()  # unlock input

        # completed
        if status == "completed":
            self.stop = False
            self.handle_messages(ctx)
            self.window.statusChanged.emit(trans('assistant.run.completed'))
            self.window.stateChanged.emit(self.window.STATE_IDLE)
            self.window.controller.chat.output.show_response_tokens(ctx)  # update tokens

        # func call
        elif status == "requires_action":
            self.stop = False
            ctx.tool_calls = self.window.core.command.unpack_tool_calls(
                run.required_action.submit_tool_outputs.tool_calls
            )
            self.window.statusChanged.emit(trans('assistant.run.func.call'))
            self.window.stateChanged.emit(self.window.STATE_IDLE)
            self.handle_tool_calls(ctx)

        # error
        elif status in ["failed", "cancelled", "expired", "cancelling"]:
            self.stop = False
            self.window.controller.chat.common.unlock_input()
            self.window.statusChanged.emit(trans('assistant.run.failed'))
            self.window.stateChanged.emit(self.window.STATE_ERROR)

    @Slot()
    def handle_destroy(self):
        """Handle thread destroy"""
        self.started = False
        self.stop = False

    @Slot()
    def handle_started(self):
        """Handle listening started"""
        if self.is_log():
            print("Run: assistant is listening status...")
        self.window.statusChanged.emit(trans('assistant.run.listening'))

    def is_log(self) -> bool:
        """
        Check if logging is enabled

        :return: True if enabled
        """
        if self.window.core.config.has('log.assistants') \
                and self.window.core.config.get('log.assistants'):
            return True
        return False

    def reset(self):
        """
        Reset tool calls
        """
        self.run_id = None
        self.tool_calls = []

    def is_running(self) -> bool:
        """
        Check if tool calls need submit

        :return: True if running
        """
        return self.run_id is not None and len(self.tool_calls) > 0


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
                run = self.window.core.gpt.assistants.run_get(self.ctx)
                status = None
                if run is not None:
                    status = run.status
                    if run.usage is not None:
                        self.ctx.input_tokens = run.usage["prompt_tokens"]
                        self.ctx.output_tokens = run.usage["completion_tokens"]
                        self.ctx.total_tokens = run.usage["total_tokens"]

                self.signals.updated.emit(run, self.ctx)  # handle status update

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
