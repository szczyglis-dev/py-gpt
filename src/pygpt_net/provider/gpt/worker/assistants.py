#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 21:00:00                  #
# ================================================== #

from openai import AssistantEventHandler

from PySide6.QtCore import QObject, Signal, QRunnable, Slot
from typing_extensions import override

from pygpt_net.core.events import RenderEvent
from pygpt_net.item.ctx import CtxItem, CtxMeta


class AssistantsWorker:
    CHUNK_TYPE_MSG = 1  # last chunk = message
    CHUNK_TYPE_TOOL = 0  # last chunk = tool

    def __init__(self, window=None):
        """
        Assistants Worker (async)

        :param window: Window instance
        """
        self.window = window
        self.tool_output = ""
        self.last_chunk_type = self.CHUNK_TYPE_MSG  # msg or tool

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
            model: str,
            file_ids: list,
            prompt: str,
            system_prompt: str
    ):
        """
        Send message to assistant thread

        :param ctx: context item
        :param thread_id: thread id
        :param assistant_id: assistant id
        :param model: model ID
        :param file_ids: uploaded file IDs
        :param prompt: prompt
        :param system_prompt: system prompt
        """
        worker = Worker()
        worker.window = self.window
        worker.mode = "msg_send"
        worker.model = model
        worker.ctx = ctx
        worker.thread_id = thread_id
        worker.assistant_id = assistant_id
        worker.prompt = prompt
        worker.file_ids = file_ids
        worker.system_prompt = system_prompt
        worker.stream = self.window.core.config.get("stream")
        self.connect_signals(worker)
        self.window.threadpool.start(worker)

    def tools_submit(
            self,
            ctx: CtxItem,
            model: str,
            tools_outputs: list,
    ):
        """
        Send tools outputs to assistant thread

        :param ctx: context item
        :param model: model ID
        :param tools_outputs: list of tools outputs
        """
        worker = Worker()
        worker.window = self.window
        worker.mode = "tools_submit"
        worker.model = model
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
        worker.signals.stream_run_step_done.connect(self.handle_run_step_done)
        worker.signals.stream_run_created.connect(self.handle_run_created)

    def is_show_tool_output(self) -> bool:
        """
        Return True if show tool output

        :return: bool
        """
        return self.window.core.config.get('ctx.code_interpreter', False)

    def begin_chunks(self, ctx: CtxItem):
        """
        Begin chunks stream output

        :param ctx: context item
        """
        self.render_output(RenderEvent.STREAM_BEGIN, ctx.meta, ctx)
        self.window.controller.assistant.threads.handle_stream_begin(ctx)
        self.render_output(RenderEvent.STREAM_APPEND, ctx.meta, ctx, chunk="", begin=True)

    def reset_tool_output(self):
        """Reset tool output"""
        self.tool_output = ""

    def has_tool_output(self) -> bool:
        """
        Return True if has tool output

        :return: bool
        """
        return self.tool_output is not None and self.tool_output != ""

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
        self.render_output(RenderEvent.STREAM_APPEND, ctx.meta, ctx, chunk=chunk, begin=False)

    def render_output(self, event_name: str, meta: CtxMeta, ctx: CtxItem, **kwargs):
        """
        Send render output event to window

        :param event_name: event name
        :param meta: context meta
        :param ctx: context item
        :param kwargs: additional data
        """
        data = {
            "meta": meta,
            "ctx": ctx,
        }
        data.update(kwargs)
        event = RenderEvent(event_name, data)
        self.window.dispatch(event)

    def log(self, message: str):
        """
        Log assistant message

        :param message: message
        """
        self.window.controller.assistant.threads.log(message)

    @Slot(object)
    def handle_text_created(self, ctx: CtxItem):
        """
        Handle thread text created signal

        :param ctx: context item
        """
        self.log("STREAM: text created")
        if ctx.stopped:
            self.log("STREAM: ignoring: stopped")
            return
        if (ctx.output != "" and ctx.output is not None) or self.has_tool_output():
            return  # append to existing output

    @Slot(object, object)
    def handle_text_delta(self, ctx: CtxItem, delta, begin):
        """
        Handle thread text delta signal

        :param ctx: context item
        :param delta: delta
        :param begin: stream text begin
        """
        if ctx.stopped:
            return
        # self.window.controller.assistant.threads.log("STREAM: text delta")
        if ctx.output_tokens is None:
            ctx.output_tokens = 0
        ctx.output_tokens += 1  # tokens++
        self.append_chunk(ctx, delta.value, begin)
        self.last_chunk_type = self.CHUNK_TYPE_MSG
        # self.log("STREAM: chunk: msg text")

    @Slot(object)
    def handle_end(self, ctx: CtxItem):
        """
        Handle thread end signal

        :param ctx: context item
        """
        self.log("STREAM: end")
        if ctx.stopped:
            return
        self.reset_tool_output()
        self.render_output(RenderEvent.STREAM_END, ctx.meta, ctx)
        self.window.controller.assistant.threads.handle_output_message(ctx, stream=True)

    @Slot(object, object, bool)
    def handle_tool_call_created(self, ctx: CtxItem, tool_call, begin):
        """
        Handle thread tool call created signal

        :param ctx: context item
        :param tool_call: tool call
        :param begin: stream text begin
        """
        self.log("STREAM: tool call created: {}".format(tool_call.type))
        if ctx.stopped:
            self.log("STREAM: ignoring: stopped")
            return
        if self.is_show_tool_output():
            self.reset_tool_output()

    @Slot(object, object, bool)
    def handle_tool_call_delta(self, ctx: CtxItem, delta, begin):
        """
        Handle thread tool call delta signal

        :param ctx: context item
        :param delta: delta
        :param begin: stream text begin
        """
        if ctx.stopped:
            return
        # self.log("STREAM: tool call delta")
        if self.is_show_tool_output():
            if delta.type == 'code_interpreter':
                # begin code block
                if begin:
                    self.log("STREAM: tool output: code_interpreter: begin")
                    self.append_chunk(ctx, "\n\n**Code interpreter**\n```python\n", begin=False)

                # input
                if delta.code_interpreter.input:
                    if delta.code_interpreter.input is not None:
                        self.tool_output += delta.code_interpreter.input
                        self.append_chunk(ctx, delta.code_interpreter.input)
                        self.last_chunk_type = self.CHUNK_TYPE_TOOL
                        # self.log("STREAM: chunk: code_interpreter: input")

                # output
                if delta.code_interpreter.outputs:
                    header = False
                    for output in delta.code_interpreter.outputs:
                        if output.type == "logs":
                            if not header:
                                self.log("STREAM: tool output: code_interpreter: log begin")
                                self.append_chunk(ctx, "\n\n-------\nOutput:\n")
                                self.last_chunk_type = self.CHUNK_TYPE_TOOL
                                header = True
                            chunk = output.logs
                            if output.logs is not None:
                                self.append_chunk(ctx, "\n" + chunk)
                                self.last_chunk_type = self.CHUNK_TYPE_TOOL
                                # self.log("STREAM: chunk: code_interpreter: logs")

    @Slot(object, object, bool)
    def handle_tool_call_done(self, ctx: CtxItem, tool_call, begin):
        """
        Handle thread tool call done signal

        :param ctx: context item
        :param tool_call: tool call
        :param begin: stream text begin
        """
        if type(tool_call) == "dict":  # not-native call
            self.log("STREAM: tool call done: {}".format(tool_call))
        else:  # native call
            self.log("STREAM: tool call done: {}".format(tool_call.type))
            
        if ctx.stopped:
            self.log("STREAM: ignoring: stopped")
            return
        if self.is_show_tool_output():
            if self.has_tool_output() and self.last_chunk_type == self.CHUNK_TYPE_TOOL:
                self.append_chunk(ctx, "\n```\n")

    @Slot(object, object)
    def handle_message_done(self, ctx: CtxItem, message):
        """
        Handle thread message done signal

        :param ctx: context item
        :param message: message
        """
        self.log("STREAM: message done")
        if ctx.stopped:
            self.log("STREAM: ignoring: stopped")
            return
        self.window.controller.assistant.threads.handle_message_data(
            ctx,
            message,
            stream=True,
        )  # handle img, files, etc.

    @Slot(object, object, int)
    def handle_run_step_created(self, ctx: CtxItem, run_step, step_idx: int):
        """
        Handle thread run step created signal

        :param ctx: context item
        :param run_step: run step
        :param step_idx: step index
        """
        self.log("STREAM: run step created: {}, idx: {}".format(run_step.id, step_idx))
        if ctx.stopped:
            self.log("STREAM: ignoring: stopped")
            return
        ctx.run_id = run_step.run_id
        self.window.controller.assistant.threads.handle_run_step_created(ctx, stream=True)
        if step_idx == 0:
            self.log("STREAM: run created: {}".format(ctx.run_id))
            self.log("STREAM: begin chunks...")
            self.begin_chunks(ctx)

    @Slot(object, object, int)
    def handle_run_step_done(self, ctx: CtxItem, run_step, step_idx: int):
        """
        Handle thread run step created signal

        :param ctx: context item
        :param run_step: run step
        :param step_idx: step index
        """
        self.log("STREAM: run step done: {}, idx: {}".format(run_step.id, step_idx))
        if ctx.stopped:
            self.log("STREAM: ignoring: stopped")
            return

    @Slot(object, object)
    def handle_error(self, ctx: CtxItem, err: any):
        """
        Handle thread error signal

        :param ctx: context item
        :param err: error message
        """
        self.log("STREAM: error: {}".format(err))
        self.window.controller.assistant.threads.handle_run_error(ctx, err)  # bad filetype error, etc.

    @Slot(object, object, bool)
    def handle_run_created(self, ctx: CtxItem, run, stream=False):
        """
        Handle thread finished signal

        :param ctx: context item
        :param run
        :param stream: stream mode
        """
        if not stream:
            self.log("STREAM: run created: {}".format(run.id))
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
        self.text_begin = False
        self.tool_begin = False
        self.stream_started = False
        self.step_idx = 0
        
    @override
    def on_text_created(self, text) -> None:
        """Callback that is fired when a text content block is created"""
        # print(f"\nassistant > ", end="", flush=True)
        if not self.stream_started:
            self.text_begin = True
        self.stream_started = True
        self.signals.stream_text_created.emit(self.ctx)

    @override
    def on_text_delta(self, delta, snapshot):
        """Callback that is fired whenever a message delta is returned from the API"""
        # print(delta.value, end="", flush=True)
        self.signals.stream_text_delta.emit(self.ctx, delta, self.text_begin)
        self.text_begin = False

    @override
    def on_run_step_created(self, run_step) -> None:
        """Callback that is fired when a run step is created"""
        self.tool_begin = False  # reset
        self.signals.stream_run_step_created.emit(self.ctx, run_step, self.step_idx)
        self.step_idx += 1

    @override
    def on_run_step_done(self, run_step):
        """Fires when run completed."""
        self.signals.stream_run_step_done.emit(self.ctx, run_step, self.step_idx)

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
        self.tool_begin = False  # reset
        self.signals.stream_tool_call_created.emit(self.ctx, tool_call, self.tool_begin)

    @override
    def on_tool_call_delta(self, delta, snapshot):
        """Callback that is fired when a tool call delta is encountered"""
        begin = True
        if self.tool_begin:
            begin = False
        self.signals.stream_tool_call_delta.emit(self.ctx, delta, begin)
        self.tool_begin = True

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
    stream_tool_call_created = Signal(object, object, bool)  # ctx, tool_call, begin
    stream_tool_call_delta = Signal(object, object, bool)  # ctx, delta, begin
    stream_tool_call_done = Signal(object, object, bool)  # ctx, tool_call
    stream_message_done = Signal(object, object)  # ctx, message
    stream_run_step_created = Signal(object, object, int)  # ctx, run_step, step idx
    stream_run_created = Signal(object, object)  # ctx, run_step
    stream_run_step_done = Signal(object, object, int)  # ctx, run_step, step idx


class Worker(QRunnable):
    """Assistants worker"""
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.window = None
        self.mode = None
        self.model = None
        self.thread_id = None
        self.assistant_id = None
        self.file_ids = []
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
                    self.model,
                    self.system_prompt,
                )
            else:
                # not stream mode
                run = self.window.core.gpt.assistants.run_create(
                    self.thread_id,
                    self.assistant_id,
                    self.model,
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
                self.file_ids,
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
