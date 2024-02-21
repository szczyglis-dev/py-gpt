#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.21 14:00:00                  #
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
        self.img_ext = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp']

    def create_thread(self) -> str:
        """
        Create assistant thread

        :return: thread id
        """
        thread_id = self.window.core.gpt.assistants.thread_create()
        self.window.core.config.set('assistant_thread', thread_id)
        self.window.core.ctx.append_thread(thread_id)
        return thread_id

    def handle_output_message(self, ctx: CtxItem):
        """
        Handle output message

        :param ctx: CtxItem
        """
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

    def handle_message_data(self, ctx: CtxItem, msg):
        """
        Handle message data

        :param ctx: CtxItem
        :param msg: Message
        """
        paths = []
        file_ids = []
        images_ids = []
        mappings = {}  # file_id: path to sandbox

        for content in msg.content:
            if content.type == "text":
                ctx.set_output(content.text.value)

                # annotations
                if content.text.annotations:
                    if self.is_log():
                        print("Run: received annotations: {}".format(len(content.text.annotations)))
                    for item in content.text.annotations:
                        if item.type == "file_path":
                            file_id = item.file_path.file_id
                            file_ids.append(file_id)
                            mappings[file_id] = item.text

            # image file
            elif content.type == "image_file":
                if self.is_log():
                    print("Run: received image file")
                images_ids.append(content.image_file.file_id)

        # handle msg files
        for file_id in msg.file_ids:
            if file_id not in images_ids and file_id not in file_ids:
                file_ids.append(file_id)

        # handle content images
        if images_ids:
            image_paths = self.window.controller.assistant.files.handle_received_ids(images_ids, ".png")
            ctx.images = self.window.core.filesystem.make_local_list(list(image_paths))

        # download msg files
        paths += self.window.controller.assistant.files.handle_received_ids(file_ids)
        if paths:
            # convert to local paths
            local_paths = self.window.core.filesystem.make_local_list(list(paths))
            text_msg = ctx.output
            if text_msg:
                # map file ids to local paths
                for file_id in mappings:
                    path_sandbox = mappings[file_id]
                    k = file_ids.index(file_id)
                    if len(local_paths) > k:
                        text_msg = text_msg.replace(path_sandbox, local_paths[k])  # replace sandbox path
                ctx.set_output(text_msg)
            ctx.files = local_paths

            # append images from msg files
            if len(images_ids) == 0:
                img_files = []
                for path in paths:
                    if path.split('.')[-1].lower() in self.img_ext:
                        img_files.append(path)
                if img_files:
                    ctx.images = self.window.core.filesystem.make_local_list(list(img_files))

    def handle_messages(self, ctx: CtxItem):
        """
        Handle run messages

        :param ctx: CtxItem
        """
        data = self.window.core.gpt.assistants.msg_list(ctx.thread)
        for msg in data:
            if msg.role == "assistant":
                try:
                    if self.is_log():
                        print("Run: handling message...")
                    self.handle_message_data(ctx, msg)
                except Exception as e:
                    self.window.core.debug.log(e)
                    print("Run: handle message error:", e)
                break
        self.handle_output_message(ctx)  # send to chat

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

        ctx.internal = True  # hide in chat input + handle synchronously

        self.window.controller.chat.output.handle(ctx, 'assistant', False)
        self.window.controller.chat.output.handle_cmd(ctx)

        ctx.tool_calls = []  # clear tool calls

        # update ctx
        self.window.core.ctx.update_item(ctx)

        # index ctx (llama-index)
        self.window.controller.idx.on_ctx_end(ctx)

        # check if there are any response, if not send empty response
        if not ctx.reply:
            results = {
                "response": "",
            }
            self.window.controller.chat.input.send(
                json.dumps(results),
                force=True,
                reply=True,
                internal=True,
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

    def handle_run_created(self, ctx: CtxItem, run):
        """
        Handle run created

        :param ctx: context item
        :param run
        """
        ctx.run_id = run.id
        ctx.current = False
        self.window.core.ctx.update_item(ctx)
        self.window.core.ctx.append_run(ctx.run_id)  # get run ID and store in ctx
        self.handle_run(ctx)  # handle assistant run

    def handle_run_error(self, ctx: CtxItem, err):
        """
        Handle run created

        :param ctx: context item
        :param err: error message
        """
        ctx.current = False  # reset current state
        self.window.core.ctx.update_item(ctx)
        self.window.core.debug.log(err)
        self.window.ui.dialogs.alert(str(err))

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

        # function call
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
                        self.ctx.input_tokens = run.usage.prompt_tokens
                        self.ctx.output_tokens = run.usage.completion_tokens
                        self.ctx.total_tokens = run.usage.total_tokens

                self.signals.updated.emit(run, self.ctx)  # handle status update

                # finished or failed
                if status in self.stop_reasons:
                    self.check = False
                    if self.signals.destroyed is not None:
                        self.signals.destroyed.emit()
                    return
                time.sleep(1)

            if self.signals.destroyed is not None:
                self.signals.destroyed.emit()
        except Exception as e:
            self.window.core.debug.log(e)
            if self.signals.destroyed is not None:
                self.signals.destroyed.emit()
