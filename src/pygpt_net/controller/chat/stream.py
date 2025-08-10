#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.11 00:00:00                  #
# ================================================== #

import base64
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QMetaObject, Qt

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.events import RenderEvent
from pygpt_net.core.types import MODE_ASSISTANT
from pygpt_net.core.text.utils import has_unclosed_code_tag
from pygpt_net.item.ctx import CtxItem

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    - `finished`: No data
    - `errorOccurred`: Exception
    - `eventReady`: RenderEvent
    """
    end = Signal(object)
    errorOccurred = Signal(Exception)
    eventReady = Signal(object)


class StreamWorker(QRunnable):
    def __init__(self, ctx: CtxItem, window, parent=None):
        QRunnable.__init__(self)
        self.signals = WorkerSignals()
        self.ctx = ctx
        self.window = window

    @Slot()
    def run(self):
        ctx = self.ctx
        win = self.window
        core = win.core
        ctrl = win.controller

        emit_event = self.signals.eventReady.emit
        emit_error = self.signals.errorOccurred.emit
        emit_end = self.signals.end.emit

        output_parts = []
        output_tokens = 0
        begin = True
        error = None
        fn_args_buffers = {}
        citations = []
        files = []
        img_path = core.image.gen_unique_path(ctx)
        is_image = False
        is_code = False
        force_func_call = False
        stopped = False
        chunk_type = "raw"
        generator = ctx.stream
        ctx.stream = None

        base_data = {
            "meta": ctx.meta,
            "ctx": ctx,
        }
        emit_event(RenderEvent(RenderEvent.STREAM_BEGIN, base_data))

        tool_calls = []
        try:
            if generator is not None:
                for chunk in generator:
                    if ctrl.kernel.stopped():
                        ctx.msg_id = None
                        stopped = True
                        break

                    if error is not None:
                        ctx.msg_id = None
                        stopped = True
                        break

                    etype = None
                    response = None

                    if ctx.use_responses_api:
                        if hasattr(chunk, 'type'):
                            etype = chunk.type
                            chunk_type = "api_chat_responses"
                        else:
                            continue
                    else:
                        if (hasattr(chunk, 'choices')
                                and chunk.choices
                                and hasattr(chunk.choices[0], 'delta')
                                and chunk.choices[0].delta is not None):
                            chunk_type = "api_chat"
                        elif (hasattr(chunk, 'choices')
                              and chunk.choices
                              and hasattr(chunk.choices[0], 'text')
                              and chunk.choices[0].text is not None):
                            chunk_type = "api_completion"
                        elif hasattr(chunk, 'content') and chunk.content is not None:
                            chunk_type = "langchain_chat"
                        elif hasattr(chunk, 'delta') and chunk.delta is not None:
                            chunk_type = "llama_chat"
                        else:
                            chunk_type = "raw"

                    # OpenAI chat completion
                    if chunk_type == "api_chat":
                        citations = None
                        delta = chunk.choices[0].delta
                        if delta and delta.content is not None:
                            if citations is None and hasattr(chunk, 'citations') and chunk.citations is not None:
                                citations = chunk.citations
                                ctx.urls = citations
                            response = delta.content

                        if delta and delta.tool_calls:
                            for tool_chunk in delta.tool_calls:
                                if tool_chunk.index is None:
                                    tool_chunk.index = 0
                                if len(tool_calls) <= tool_chunk.index:
                                    tool_calls.append(
                                        {
                                            "id": "",
                                            "type": "function",
                                            "function": {"name": "", "arguments": ""}
                                        }
                                    )
                                tool_call = tool_calls[tool_chunk.index]
                                if getattr(tool_chunk, "id", None):
                                    tool_call["id"] += tool_chunk.id
                                if getattr(tool_chunk.function, "name", None):
                                    tool_call["function"]["name"] += tool_chunk.function.name
                                if getattr(tool_chunk.function, "arguments", None):
                                    tool_call["function"]["arguments"] += tool_chunk.function.arguments

                    # OpenAI Responses API
                    elif chunk_type == "api_chat_responses":
                        if etype == "response.completed":
                            for item in chunk.response.output:
                                if item.type == "mcp_list_tools":
                                    core.gpt.responses.mcp_tools = item.tools
                                elif item.type == "mcp_call":
                                    call = {
                                        "id": item.id,
                                        "type": "mcp_call",
                                        "approval_request_id": item.approval_request_id,
                                        "arguments": item.arguments,
                                        "error": item.error,
                                        "name": item.name,
                                        "output": item.output,
                                        "server_label": item.server_label,
                                    }
                                    tool_calls.append({
                                        "id": item.id,
                                        "call_id": "",
                                        "type": "function",
                                        "function": {"name": item.name, "arguments": item.arguments}
                                    })
                                    ctx.extra["mcp_call"] = call
                                    core.ctx.update_item(ctx)
                                elif item.type == "mcp_approval_request":
                                    call = {
                                        "id": item.id,
                                        "type": "mcp_call",
                                        "arguments": item.arguments,
                                        "name": item.name,
                                        "server_label": item.server_label,
                                    }
                                    ctx.extra["mcp_approval_request"] = call
                                    core.ctx.update_item(ctx)

                        elif etype == "response.output_text.delta":
                            response = chunk.delta

                        # function_call
                        elif etype == "response.output_item.added" and chunk.item.type == "function_call":
                            tool_calls.append({
                                "id": chunk.item.id,
                                "call_id": chunk.item.call_id,
                                "type": "function",
                                "function": {"name": chunk.item.name, "arguments": ""}
                            })
                            fn_args_buffers[chunk.item.id] = ""
                        elif etype == "response.function_call_arguments.delta":
                            fn_args_buffers[chunk.item_id] += chunk.delta
                        elif etype == "response.function_call_arguments.done":
                            buf = fn_args_buffers.pop(chunk.item_id, None)
                            if buf is not None:
                                for tc in tool_calls:
                                    if tc["id"] == chunk.item_id:
                                        tc["function"]["arguments"] = buf
                                        break

                        # annotations
                        elif etype == "response.output_text.annotation.added":
                            ann = chunk.annotation
                            if ann['type'] == "url_citation":
                                if citations is None:
                                    citations = []
                                url_citation = ann['url']
                                citations.append(url_citation)
                                ctx.urls = citations
                            elif ann['type'] == "container_file_citation":
                                files.append({
                                    "container_id": ann['container_id'],
                                    "file_id": ann['file_id'],
                                })

                        # computer use
                        elif etype == "response.reasoning_summary_text.delta":
                            response = chunk.delta

                        elif etype == "response.output_item.done":
                            tool_calls, has_calls = core.gpt.computer.handle_stream_chunk(ctx, chunk, tool_calls)
                            if has_calls:
                                force_func_call = True

                        # code interpreter
                        elif etype == "response.code_interpreter_call_code.delta":
                            if not is_code:
                                response = "\n\n**Code interpreter**\n```python\n" + chunk.delta
                                is_code = True
                            else:
                                response = chunk.delta
                        elif etype == "response.code_interpreter_call_code.done":
                            response = "\n\n```\n-----------\n"

                        # image gen
                        elif etype == "response.image_generation_call.partial_image":
                            image_base64 = chunk.partial_image_b64
                            image_bytes = base64.b64decode(image_base64)
                            # prosty i bezpieczny overwrite (jak w oryginale)
                            with open(img_path, "wb") as f:
                                f.write(image_bytes)
                            is_image = True

                        # response ID
                        elif etype == "response.created":
                            ctx.msg_id = str(chunk.response.id)
                            core.ctx.update_item(ctx)

                        # end/error etype – nic nie robimy
                        elif etype in {"response.done", "response.failed", "error"}:
                            pass

                    # OpenAI completion
                    elif chunk_type == "api_completion":
                        choice0 = chunk.choices[0]
                        if choice0.text is not None:
                            response = choice0.text

                    # langchain chat
                    elif chunk_type == "langchain_chat":
                        if chunk.content is not None:
                            response = str(chunk.content)

                    # llama chat
                    elif chunk_type == "llama_chat":
                        if chunk.delta is not None:
                            response = str(chunk.delta)
                        tool_chunks = getattr(chunk.message, "additional_kwargs", {}).get("tool_calls", [])
                        if tool_chunks:
                            for tool_chunk in tool_chunks:
                                id_val = getattr(tool_chunk, "call_id", None) or getattr(tool_chunk, "id", None)
                                name = getattr(tool_chunk, "name", None) or getattr(getattr(tool_chunk, "function", None), "name", None)
                                args = getattr(tool_chunk, "arguments", None)
                                if args is None:
                                    f = getattr(tool_chunk, "function", None)
                                    args = getattr(f, "arguments", None) if f else None
                                if id_val:
                                    if not args:
                                        args = "{}"
                                    tool_call = {
                                        "id": id_val,
                                        "type": "function",
                                        "function": {"name": name, "arguments": args}
                                    }
                                    tool_calls.clear()
                                    tool_calls.append(tool_call)

                    # raw text (llama-index / langchain completion)
                    else:
                        if chunk is not None:
                            response = str(chunk)

                    if response is not None and response != "" and not stopped:
                        if begin and response == "":
                            continue
                        output_parts.append(response)
                        output_tokens += 1
                        emit_event(
                            RenderEvent(
                                RenderEvent.STREAM_APPEND,
                                {
                                    "meta": ctx.meta,
                                    "ctx": ctx,
                                    "chunk": response,
                                    "begin": begin,
                                },
                            )
                        )
                        begin = False

                    chunk = None

                # tool calls
                if tool_calls:
                    ctx.force_call = force_func_call
                    core.debug.info("[chat] Tool calls found, unpacking...")
                    core.command.unpack_tool_calls_chunks(ctx, tool_calls)

                # image
                if is_image:
                    core.debug.info("[chat] Image generation call found")
                    ctx.images = [img_path]

        except Exception as e:
            error = e

        finally:
            output = "".join(output_parts)
            output_parts.clear()

            if has_unclosed_code_tag(output):
                output += "\n```"

            if generator and hasattr(generator, 'close'):
                try:
                    generator.close()
                except Exception:
                    pass

            del generator

            ctx.output = output
            ctx.set_tokens(ctx.input_tokens, output_tokens)
            core.ctx.update_item(ctx)

            if files and not stopped:
                core.debug.info("[chat] Container files found, downloading...")
                try:
                    core.gpt.container.download_files(ctx, files)
                except Exception as e:
                    core.debug.error(f"[chat] Error downloading container files: {e}")

            if error:
                emit_error(error)

            emit_end(ctx)

            fn_args_buffers.clear()
            files.clear()
            tool_calls.clear()
            if citations is not None:
                citations.clear()

            self.cleanup()

    def cleanup(self):
        """
        Cleanup resources after worker execution.
        """
        self.ctx = None
        self.window = None
        try:
            QMetaObject.invokeMethod(self.signals, "deleteLater", Qt.QueuedConnection)
        except Exception:
            pass


class Stream:
    def __init__(self, window=None):
        """
        Stream controller

        :param window: Window instance
        """
        self.window = window
        self.ctx = None
        self.mode = None
        self.thread = None
        self.worker = None
        self.is_response = False
        self.reply = False
        self.internal = False
        self.context = None
        self.extra = {}

    def append(
            self,
            ctx: CtxItem,
            mode: str = None,
            is_response: bool = False,
            reply: str = False,
            internal: bool = False,
            context: Optional[BridgeContext] = None,
            extra: Optional[dict] = None
    ):
        """
        Asynchronous append of stream worker to the thread.
        """
        self.ctx = ctx
        self.mode = mode
        self.is_response = is_response
        self.reply = reply
        self.internal = internal
        self.context = context
        self.extra = extra if extra is not None else {}

        worker = StreamWorker(ctx, self.window)
        self.worker = worker

        worker.signals.eventReady.connect(self.handleEvent)
        worker.signals.errorOccurred.connect(self.handleError)
        worker.signals.end.connect(self.handleEnd)

        self.window.core.debug.info("[chat] Stream begin...")
        self.window.threadpool.start(worker)

    @Slot(object)
    def handleEnd(self, ctx: CtxItem):
        """
        Slot for handling end of stream
        """
        self.window.controller.ui.update_tokens()

        data = {"meta": self.ctx.meta, "ctx": self.ctx}
        event = RenderEvent(RenderEvent.STREAM_END, data)
        self.window.dispatch(event)
        self.window.controller.chat.output.handle_after(
            ctx=ctx,
            mode=self.mode,
            stream=True,
        )

        if self.mode == MODE_ASSISTANT:
            self.window.controller.assistant.threads.handle_output_message_after_stream(ctx)
        else:
            if self.is_response:
                self.window.controller.chat.response.post_handle(
                    ctx=ctx,
                    mode=self.mode,
                    stream=True,
                    reply=self.reply,
                    internal=self.internal
                )

        self.worker = None

    def handleEvent(self, event):
        self.window.dispatch(event)

    def handleError(self, error):
        self.window.core.debug.log(error)
        if self.is_response:
            if not isinstance(self.extra, dict):
                self.extra = {}
            self.extra["error"] = error
            self.window.controller.chat.response.failed(self.context, self.extra)
            self.window.controller.chat.response.post_handle(
                ctx=self.ctx,
                mode=self.mode,
                stream=True,
                reply=self.reply,
                internal=self.internal,
            )

    def log(self, data: object):
        self.window.core.debug.info(data)