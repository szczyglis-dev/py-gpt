#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

import json
import time

from PySide6.QtCore import QObject, Signal, Slot, QRunnable

from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans, get_image_extensions


class Threads:
    def __init__(self, window=None):
        """
        Assistant threads controller

        :param window: Window instance
        """
        self.window = window
        self.started = False
        self.stop = False  # force stop run
        self.run_id = None  # current run ID
        self.tool_calls = []  # list of previous tool calls
        self.img_ext = get_image_extensions()  # list, .png, .jpg, etc.

    def create_thread(self) -> str:
        """
        Create assistant thread and store in context (stream and not stream)

        :return: thread id
        """
        thread_id = self.window.core.gpt.assistants.thread_create()
        self.window.core.config.set('assistant_thread', thread_id)
        self.window.core.ctx.append_thread(thread_id)
        return thread_id

    def handle_output_message(self, ctx: CtxItem, stream: bool = False):
        """
        Handle output message (not stream ONLY)

        :param ctx: CtxItem
        :param stream: True if stream
        """
        # update ctx
        ctx.from_previous()  # append previous result if exists
        self.window.core.ctx.update_item(ctx)
        self.window.controller.chat.output.handle(ctx, 'assistant', stream)

        if stream:  # append all output to chat
            self.window.controller.chat.render.end(ctx.meta, ctx, stream=stream)  # extra reload for stream markdown needed here

        ctx.clear_reply()  # reset results

        self.log("Handling output message...")

        has_cmd = self.window.core.command.has_cmds(ctx.output)
        if has_cmd:
            self.log("Handling message command...")
            self.window.controller.chat.command.handle(ctx)

        # update ctx
        ctx.from_previous()  # append previous result again before save
        self.window.core.ctx.update_item(ctx)

        # index ctx (llama-index)
        self.window.controller.idx.on_ctx_end(ctx, mode="assistant")

        # update ctx list
        self.window.controller.ctx.update()

        # if is command execute and not locked yet (not executing)
        if has_cmd and self.window.controller.chat.reply.waiting():
            self.log("Replying for message command...")
            self.window.controller.chat.reply.handle()

        self.log("Handled output message.")

    def handle_message_data(self, ctx: CtxItem, msg, stream: bool = False):
        """
        Handle message data (files, images, text) - stream and not-stream

        :param ctx: CtxItem
        :param msg: Message
        :param stream: True if stream
        """
        paths = []
        file_ids = []
        images_ids = []
        mappings = {}  # file_id: path to sandbox
        citations = []

        for content in msg.content:
            if content.type == "text":
                # text, append only if no stream or if is stream and already streamed output is empty
                if not stream or (ctx.output is None or ctx.output == ""):
                    ctx.set_output(content.text.value)

                # annotations
                if content.text.annotations:
                    self.log("Run: received annotations: {}".format(len(content.text.annotations)))
                    for item in content.text.annotations:
                        # file
                        if item.type == "file_path":
                            file_id = item.file_path.file_id
                            file_ids.append(file_id)
                            mappings[file_id] = item.text
                        # citation
                        elif item.type == "file_citation":
                            data = {
                                "type": "assistant",  # store is remote
                                "text": item.text,
                                "start_idx": item.start_index,
                                "end_idx": item.end_index,
                            }
                            if item.file_citation:
                                data["file_id"] = item.file_citation.file_id
                                data["quote"] = item.file_citation.quote
                            citations.append(data)

            # image file
            elif content.type == "image_file":
                self.log("Run: received image file")
                images_ids.append(content.image_file.file_id)

        """
        # handle message files  -- legacy, deprecated
        for file_id in msg.file_ids:
            if file_id not in images_ids and file_id not in file_ids:
                self.log("Run: appending file id: {}".format(file_id))
                file_ids.append(file_id)
        """

        # handle content images
        if images_ids:
            image_paths = self.window.controller.assistant.files.handle_received_ids(images_ids, ".png")
            ctx.images = self.window.core.filesystem.make_local_list(list(image_paths))

        # citations
        if citations:
            ctx.doc_ids = citations

        # -- files --

        # download message files
        paths += self.window.controller.assistant.files.handle_received_ids(file_ids)
        if paths:
            # convert to local paths
            local_paths = self.window.core.filesystem.make_local_list(list(paths))
            text_msg = ctx.output  # use current output
            if text_msg:
                # map file ids to local paths
                for file_id in mappings:
                    path_sandbox = mappings[file_id]
                    k = file_ids.index(file_id)
                    if len(local_paths) > k:
                        text_msg = text_msg.replace(
                            path_sandbox,
                            local_paths[k]
                        )  # replace sandbox file path with a local path
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

        ctx.from_previous()  # append previous result again before save
        self.window.core.ctx.update_item(ctx)

    def handle_messages(self, ctx: CtxItem):
        """
        Handle run messages (not stream ONLY)

        :param ctx: CtxItem
        """
        data = self.window.core.gpt.assistants.msg_list(ctx.thread)
        for msg in data:
            if msg.role == "assistant":
                try:
                    self.log("Run: handling non-stream message...")
                    self.handle_message_data(ctx, msg)
                except Exception as e:
                    self.window.core.debug.log(e)
                    print("Run: handle message error:", e)
                break
        self.handle_output_message(ctx)

    def handle_tool_calls_stream(self, run, ctx: CtxItem):
        """
        Handle tool calls (stream ONLY)

        :param run: Run
        :param ctx: CtxItem
        """
        self.stop = False
        ctx.tool_calls = self.window.core.command.unpack_tool_calls(
            run.required_action.submit_tool_outputs.tool_calls
        )
        self.window.statusChanged.emit(trans('assistant.run.func.call'))
        self.window.stateChanged.emit(self.window.STATE_IDLE)
        self.handle_tool_calls(ctx)

    def handle_tool_calls(self, ctx: CtxItem):
        """
        Handle tool calls (stream and non-stream)

        :param ctx: CtxItem
        """
        self.log("Run: handling tool calls...")

        # store for submit
        self.run_id = ctx.run_id
        self.tool_calls = ctx.tool_calls

        has_calls = len(ctx.tool_calls) > 0

        # update ctx
        self.window.core.ctx.update_item(ctx)

        ctx.internal = True  # hide in chat input + handle synchronously

        self.window.controller.chat.output.handle(ctx, 'assistant', False)

        if has_calls:
            self.log("Handling tool call: {}.".format(ctx.tool_calls))
            self.window.controller.chat.command.handle(ctx)            

        ctx.tool_calls = []  # clear tool calls

        # update ctx
        self.window.core.ctx.update_item(ctx)

        # index ctx (llama-index)
        self.window.controller.idx.on_ctx_end(ctx, mode="assistant")

        if has_calls and self.window.controller.chat.reply.waiting():
            self.log("Replying for tool call...")
            self.window.controller.chat.reply.handle()
            return

        # check if there are any response, if not send empty response
        # TODO: if native then there is no cmd response here and response will be sent as tool call result
        # string response is only for message command response
        
        self.log("Sending response reply...")

        if not ctx.reply:
            results = {
                "response": "",
            }
            self.window.controller.chat.input.send(
                text=json.dumps(results),
                force=True,
                reply=True,
                internal=True,
                prev_ctx=ctx,
            )

    def handle_tool_outputs(self, ctx: CtxItem) -> list:
        """
        Handle tool outputs

        :param ctx: CtxItem
        :return: list of tool calls outputs
        """
        tools_outputs = []
        if self.window.controller.assistant.threads.is_running():
            tools_outputs = self.window.controller.assistant.threads.apply_outputs(ctx)
            self.window.controller.assistant.threads.reset()  # reset outputs
            self.log("Appended tool outputs: {}".format(len(tools_outputs)))

            # clear tool calls to prevent appending cmds to output (otherwise it will call commands again)
            ctx.tool_calls = []
        return tools_outputs


    def apply_outputs(self, ctx: CtxItem) -> list:
        """
        Apply tool call outputs

        :param ctx: CtxItem
        :return: list of tool calls outputs
        """
        self.log("Run: preparing tool calls outputs...")
        ctx.run_id = self.run_id
        ctx.tool_calls = self.tool_calls  # set previous tool calls
        return self.window.core.command.get_tool_calls_outputs(ctx)

    def handle_run_created(self, ctx: CtxItem, run, stream: bool = False):
        """
        Handle run created (stream and not stream)

        :param ctx: context item
        :param run
        :param stream: True if stream
        """
        ctx.run_id = run.id
        ctx.current = False
        self.window.core.ctx.update_item(ctx)
        self.window.core.ctx.append_run(ctx.run_id)  # get run ID and store in ctx
        self.handle_run(ctx, run, stream)  # handle assistant run

    def handle_run_error(self, ctx: CtxItem, err):
        """
        Handle run created (stream and not stream)

        :param ctx: context item
        :param err: error message
        """
        stream = self.window.core.config.get('stream')
        ctx.current = False  # reset current state
        ctx.from_previous()
        self.window.controller.chat.render.end(ctx.meta, ctx, stream=stream)  # extra reload for stream markdown needed here
        self.window.core.ctx.update_item(ctx)
        self.window.controller.ctx.update()
        self.window.core.debug.log(err)
        self.window.ui.dialogs.alert(err)
        self.window.ui.status("An error occurred. Please try again.")
        self.window.controller.chat.common.unlock_input()  # unlock input
        # self.handle_stream_end(ctx)

    def handle_run(self, ctx: CtxItem, run, stream: bool = False):
        """
        Handle assistant's run (not stream ONLY)

        :param ctx: CtxItem
        :param run: Run
        :param stream: True if stream
        """
        self.reset()  # clear previous run

        if stream:
            self.log("Run: finishing stream...")
            if run and run.usage is not None:
                    ctx.input_tokens = run.usage.prompt_tokens
                    ctx.output_tokens = run.usage.completion_tokens
                    ctx.total_tokens = run.usage.total_tokens
            self.handle_stream_end(ctx)  # unlock
            if run:
                if run.status == "requires_action":  # handle tool calls in stream mode
                    self.handle_tool_calls_stream(run, ctx)
            return # stop here, run is finished here in stream mode

        # ---- not stream only ----

        # run status listener
        self.window.stateChanged.emit(self.window.STATE_BUSY)
        self.log("Run: starting run worker...")

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

    def handle_stream_begin(self, ctx: CtxItem):
        """
        Handle stream end (stream ONLY)

        :param ctx: CtxItem
        """
        self.window.stateChanged.emit(self.window.STATE_BUSY)

    def handle_stream_end(self, ctx: CtxItem):
        """
        Handle stream end (stream ONLY)

        :param ctx: CtxItem
        """
        self.window.stateChanged.emit(self.window.STATE_IDLE)
        self.window.controller.chat.common.unlock_input()  # unlock input
        self.stop = False
        self.window.statusChanged.emit(trans('assistant.run.completed'))
        self.window.controller.chat.common.show_response_tokens(ctx)  # update tokens

    def handle_status_error(self, ctx: CtxItem):
        """
        Handle status error (stream and not stream)

        :param ctx: CtxItem
        """
        self.stop = False
        self.window.controller.chat.common.unlock_input()
        self.window.statusChanged.emit(trans('assistant.run.failed'))
        self.window.stateChanged.emit(self.window.STATE_ERROR)

    def handle_run_step_created(self, ctx: CtxItem, stream: bool = False):
        """
        Handle run step created (stream and not stream)

        :param ctx: CtxItem
        :param stream: True if stream
        """
        self.window.stateChanged.emit(self.window.STATE_BUSY)
        self.window.controller.chat.common.lock_input()  # lock input, show stop button

    @Slot(object, object)
    def handle_status(self, run, ctx: CtxItem):
        """
        Handle status (not stream ONLY)

        :param run: Run
        :param ctx: CtxItem
        """
        status = None
        if run:
            status = run.status

        self.log("Run status: {}".format(status))

        if status != "queued" and status != "in_progress":
            self.window.controller.chat.common.unlock_input()  # unlock input

        # completed
        if status == "completed":
            self.stop = False
            self.handle_messages(ctx)
            self.window.statusChanged.emit(trans('assistant.run.completed'))
            self.window.stateChanged.emit(self.window.STATE_IDLE)
            self.window.controller.chat.common.show_response_tokens(ctx)  # update tokens

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
            self.handle_status_error(ctx)

    @Slot()
    def handle_destroy(self):
        """Handle thread destroy"""
        self.started = False
        self.stop = False

    @Slot()
    def handle_started(self):
        """Handle listening started"""
        self.log("Run: assistant is listening status...")
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

    def log(self, msg: str):
        """
        Log message

        :param msg: message
        """
        if self.is_log():
            self.window.core.debug.info(msg, True)

    def reset(self):
        """
        Reset tool calls
        """
        self.run_id = None
        self.tool_calls = []

    def is_running(self) -> bool:
        """
        Check if tool calls need submit (tools are running)

        :return: True if running
        """
        return self.run_id is not None and len(self.tool_calls) > 0


class RunSignals(QObject):
    """Status check signals"""
    updated = Signal(object, object)
    destroyed = Signal()
    started = Signal()


class RunWorker(QRunnable):
    """Status check async worker"""
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
