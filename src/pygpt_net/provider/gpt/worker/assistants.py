#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.28 07:00:00                  #
# ================================================== #

from openai import AssistantEventHandler

from PySide6.QtCore import QObject, Signal, QRunnable, Slot
from typing_extensions import override

from pygpt_net.item.ctx import CtxItem


class AssistantsWorker:
    def __init__(self, window=None):
        """
        Assistants Worker (async)

        :param window: Window instance
        """
        self.window = window
        self.tool_output = ""

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
        worker.stream = self.window.core.config.get("stream")
        self.connect_signals(worker)
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
        worker.stream = self.window.core.config.get("stream")
        self.connect_signals(worker)
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
        worker.stream = self.window.core.config.get("stream")
        self.connect_signals(worker)
        self.window.threadpool.start(worker)

    def connect_signals(self, worker):
        """
        Connect worker signals

        :param worker: worker instance
        """
        worker.signals.finished.connect(self.handle_run_created)
        worker.signals.error.connect(self.handle_error)
        worker.signals.stream_text_created.connect(self.handle_text_created)
        worker.signals.stream_text_delta.connect(self.handle_text_delta)
        worker.signals.stream_end.connect(self.handle_end)
        worker.signals.stream_tool_call_created.connect(self.handle_tool_call_created)
        worker.signals.stream_tool_call_delta.connect(self.handle_tool_call_delta)
        worker.signals.stream_tool_call_done.connect(self.handle_tool_call_done)
        worker.signals.stream_message_done.connect(self.handle_message_done)
        worker.signals.stream_run_step_created.connect(self.handle_run_step_created)

    def is_show_tool_output(self) -> bool:
        """
        Return True if show tool output

        :return: bool
        """
        return self.window.core.config.get('ctx.code_interpreter', False)

    def append_chunk(self, ctx: CtxItem, chunk: str, begin: bool = False):
        """
        Append chunk to context output

        :param ctx: context item
        :param chunk: chunk
        :param begin: stream text begin
        """
        if ctx.output is None:
            ctx.output = ""
        if chunk is not None:
            ctx.output += chunk
        self.window.controller.chat.render.append_chunk(
            ctx,
            chunk,
            begin,
        )

    @Slot(object)
    def handle_text_created(self, ctx: CtxItem):
        """
        Handle thread text created signal

        :param ctx: context item
        """
        if (ctx.output != "" and ctx.output is not None) or self.tool_output != "":
            return  # append to existing output
        self.window.controller.chat.render.stream_begin()
        self.window.controller.assistant.threads.handle_stream_begin(ctx)

    @Slot(object, object)
    def handle_text_delta(self, ctx: CtxItem, delta, begin):
        """
        Handle thread text delta signal

        :param ctx: context item
        :param delta: delta
        :param begin: stream text begin
        """
        if ctx.output_tokens is None:
            ctx.output_tokens = 0
        ctx.output_tokens += 1  # tokens++
        self.append_chunk(ctx, delta.value, begin)

    @Slot(object)
    def handle_end(self, ctx: CtxItem):
        """
        Handle thread end signal

        :param ctx: context item
        """
        self.tool_output = ""
        self.window.controller.chat.render.stream_end()
        self.window.controller.assistant.threads.handle_output_message(ctx, stream=True)

    @Slot(object, object)
    def handle_tool_call_created(self, ctx: CtxItem, tool_call):
        """
        Handle thread tool call created signal

        :param ctx: context item
        :param tool_call: tool call
        """
        if self.is_show_tool_output():
            self.tool_output = ""

    @Slot(object, object, bool)
    def handle_tool_call_delta(self, ctx: CtxItem, delta, begin):
        """
        Handle thread tool call delta signal

        :param ctx: context item
        :param delta: delta
        :param begin: stream text begin
        """
        if self.is_show_tool_output():
            if delta.type == 'code_interpreter':
                if delta.code_interpreter.input:
                    if delta.code_interpreter.input is not None:
                        if self.tool_output == "":
                            self.window.controller.chat.render.stream_begin()
                            self.window.controller.assistant.threads.handle_stream_begin(ctx)
                            self.append_chunk(ctx, "**Code interpreter**\n```python\n", begin=begin)
                        self.tool_output += delta.code_interpreter.input
                        self.append_chunk(ctx, delta.code_interpreter.input)

                if delta.code_interpreter.outputs:
                    header = False
                    for output in delta.code_interpreter.outputs:
                        if output.type == "logs":
                            if not header:
                                self.append_chunk(ctx, "\n\n-------\nOutput:\n")
                                header = True
                            chunk = output.logs
                            if output.logs is not None:
                                self.append_chunk(ctx, "\n" + chunk)

    @Slot(object, object, bool)
    def handle_tool_call_done(self, ctx: CtxItem, tool_call, begin):
        """
        Handle thread tool call done signal

        :param ctx: context item
        :param tool_call: tool call
        :param begin: stream text begin
        """
        if self.is_show_tool_output():
            if self.tool_output is not None and self.tool_output != "":
                self.append_chunk(ctx, "\n```\n")

    @Slot(object, object)
    def handle_message_done(self, ctx: CtxItem, message):
        """
        Handle thread message done signal

        :param ctx: context item
        :param message: message
        """
        self.window.controller.assistant.threads.handle_message_data(
            ctx,
            message,
            stream=True,
        )  # handle img, files, etc.

    @Slot(object, object)
    def handle_run_step_created(self, ctx: CtxItem, run_step):
        """
        Handle thread run step created signal

        :param ctx: context item
        :param run_step: run step
        """
        ctx.run_id = run_step.run_id

    @Slot(object, object)
    def handle_error(self, ctx: CtxItem, err: any):
        """
        Handle thread error signal

        :param ctx: context item
        :param err: error message
        """
        self.window.controller.assistant.threads.handle_run_error(ctx, err)

    @Slot(object, object, bool)
    def handle_run_created(self, ctx: CtxItem, run, stream=False):
        """
        Handle thread finished signal

        :param ctx: context item
        :param run
        :param stream: stream mode
        """
        self.window.controller.assistant.threads.handle_run_created(
            ctx,
            run,
            stream=stream
        )


class EventHandler(AssistantEventHandler):
    """Assistants event handler"""
    def __init__(
            self,
            signals: QObject = None,
            ctx: CtxItem = None

    ):
        super().__init__()
        self.signals = signals
        self.ctx = ctx
        self.begin = False
        self.tool_begin = False
        self.stream_started = False
        
    @override
    def on_text_created(self, text) -> None:
        """Callback that is fired when a text content block is created"""
        # print(f"\nassistant > ", end="", flush=True)
        if not self.stream_started:
            self.begin = True
        self.stream_started = True
        self.signals.stream_text_created.emit(self.ctx)

    @override
    def on_text_delta(self, delta, snapshot):
        """Callback that is fired whenever a message delta is returned from the API"""
        # print(delta.value, end="", flush=True)
        self.signals.stream_text_delta.emit(self.ctx, delta, self.begin)
        self.begin = False

    @override
    def on_run_step_created(self, run_step) -> None:
        """Callback that is fired when a run step is created"""
        self.signals.stream_run_step_created.emit(self.ctx, run_step)

    @override
    def on_text_done(self, text):
        """Callback that is fired when a text content block is finished"""
        pass

    @override
    def on_message_done(self, message) -> None:
        """Callback that is fired when a message is completed"""
        self.signals.stream_message_done.emit(self.ctx, message)

    @override
    def on_end(self):
        """Fires when the stream has finished."""
        # print("\n\nassistant > end\n", flush=True)
        self.signals.stream_end.emit(self.ctx)

    @override
    def on_exception(self, exception: Exception):
        """Fired whenever an exception happens during streaming"""
        self.signals.error.emit(self.ctx,  exception)

    @override
    def on_timeout(self) -> None:
        """Fires if the request times out"""
        self.signals.error.emit(self.ctx,  "Timeout")

    @override
    def on_tool_call_created(self, tool_call):
        """Callback that is fired when a tool call is created"""
        # print(f"\nassistant > {tool_call.type}\n", flush=True)
        if not self.stream_started:
            self.tool_begin = True
        self.stream_started = True
        self.signals.stream_tool_call_created.emit(self.ctx, tool_call)

    @override
    def on_tool_call_delta(self, delta, snapshot):
        """Callback that is fired when a tool call delta is encountered"""
        self.signals.stream_tool_call_delta.emit(self.ctx, delta, self.tool_begin)
        self.tool_begin = False

    @override
    def on_tool_call_done(self, tool_call) -> None:
        """Callback that is fired when a tool call delta is encountered"""
        self.signals.stream_tool_call_done.emit(self.ctx, tool_call, self.tool_begin)


class WorkerSignals(QObject):
    """Assistants worker signals"""
    # run create
    finished = Signal(object, object, bool)  # ctx, run, stream
    error = Signal(object, object)  # ctx, error

    # stream
    stream_text_created = Signal(object)  # ctx
    stream_text_delta = Signal(object, object, bool)  # ctx, delta, begin
    stream_end = Signal(object)  # ctx
    stream_tool_call_created = Signal(object, object)  # ctx, tool_call
    stream_tool_call_delta = Signal(object, object, bool)  # ctx, delta
    stream_tool_call_done = Signal(object, object, bool)  # ctx, tool_call
    stream_message_done = Signal(object, object)  # ctx, message
    stream_run_step_created = Signal(object, object)  # ctx, run_step


class Worker(QRunnable):
    """Assistants worker"""
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
        self.stream = False

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
            if self.stream:  # stream mode
                run = self.window.core.gpt.assistants.run_create_stream(
                    self.signals,
                    self.ctx,
                    self.thread_id,
                    self.assistant_id,
                    self.system_prompt,
                )
            else:
                # not stream mode
                run = self.window.core.gpt.assistants.run_create(
                    self.thread_id,
                    self.assistant_id,
                    self.system_prompt,
                )
            # handle run (stream or not)
            if run is not None:
                self.signals.finished.emit(self.ctx, run, self.stream)
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
                self.signals.finished.emit(self.ctx, run, False)  # continue status check
                # TODO: implement stream mode in tool submit
                return True
        except Exception as e:
            self.signals.error.emit(self.ctx, e)
        return False
