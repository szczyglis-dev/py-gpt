#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.26 18:00:00                  #
# ================================================== #

import base64
import json
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot, QRunnable

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.events import RenderEvent
from pygpt_net.core.types import MODE_ASSISTANT
from pygpt_net.item.ctx import CtxItem


class StreamWorker(QObject, QRunnable):
    end = Signal(object)
    errorOccurred = Signal(Exception)
    eventReady = Signal(object)

    def __init__(self, ctx: CtxItem, window, parent=None):
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.ctx = ctx
        self.window = window

    @Slot()
    def run(self):
        output = ""
        output_tokens = 0
        begin = True
        error = None
        fn_args_buffers = {}
        citations = []
        files = []
        img_path = self.window.core.image.gen_unique_path(self.ctx)
        is_image = False
        is_code = False
        force_func_call = False

        data = {
            "meta": self.ctx.meta,
            "ctx": self.ctx
        }
        event = RenderEvent(RenderEvent.STREAM_BEGIN, data)
        self.eventReady.emit(event)

        try:
            if self.ctx.stream is not None:
                tool_calls = []
                for chunk in self.ctx.stream:
                    # if force stop then break
                    if self.window.controller.kernel.stopped():
                        break
                    if error is not None:
                        break  # break if error

                    etype = None
                    response = None
                    chunk_type = "raw"

                    if self.ctx.use_responses_api:
                        if hasattr(chunk, 'type'):  # streaming event type
                            etype = chunk.type
                            chunk_type = "api_chat_responses"  # responses API
                        else:
                            continue
                    else:
                        if (hasattr(chunk, 'choices')
                                and chunk.choices[0] is not None
                                and hasattr(chunk.choices[0], 'delta')
                                and chunk.choices[0].delta is not None):
                            chunk_type = "api_chat"  # chat completions API
                        elif (hasattr(chunk, 'choices')
                              and chunk.choices[0] is not None
                              and hasattr(chunk.choices[0], 'text')
                              and chunk.choices[0].text is not None):
                            chunk_type = "api_completion"
                        elif (hasattr(chunk, 'content')
                              and chunk.content is not None):
                            chunk_type = "langchain_chat"
                        elif (hasattr(chunk, 'delta')
                              and chunk.delta is not None):
                            chunk_type = "llama_chat"

                    # OpenAI chat completion
                    if chunk_type == "api_chat":
                        citations = None
                        if chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                            if citations is None:
                                if chunk and hasattr(chunk, 'citations') and chunk.citations is not None:
                                    citations = chunk.citations
                                    self.ctx.urls = citations
                            response = chunk.choices[0].delta.content

                        if chunk.choices[0].delta and chunk.choices[0].delta.tool_calls:
                            tool_chunks = chunk.choices[0].delta.tool_calls
                            for tool_chunk in tool_chunks:
                                if tool_chunk.index is None:
                                    tool_chunk.index = 0
                                if len(tool_calls) <= tool_chunk.index:
                                    tool_calls.append(
                                        {
                                            "id": "",
                                            "type": "function",
                                            "function": {
                                                "name": "",
                                                "arguments": ""
                                            }
                                        }
                                    )
                                tool_call = tool_calls[tool_chunk.index]
                                if tool_chunk.id:
                                    tool_call["id"] += tool_chunk.id
                                if tool_chunk.function.name:
                                    tool_call["function"]["name"] += tool_chunk.function.name
                                if tool_chunk.function.arguments:
                                    tool_call["function"]["arguments"] += tool_chunk.function.arguments

                    # OpenAI Responses API
                    elif chunk_type == "api_chat_responses":
                        if etype == "response.completed":
                            # MCP tools
                            for item in chunk.response.output:
                                # MCP: list tools
                                if item.type == "mcp_list_tools":
                                    tools = item.tools
                                    self.window.core.gpt.responses.mcp_tools = tools  # store MCP tools for later use
                                # MCP: tool call
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
                                        "function": {
                                            "name": item.name,
                                            "arguments": item.arguments
                                        }
                                    })
                                    self.ctx.extra["mcp_call"] = call
                                    self.window.core.ctx.update_item(self.ctx)
                                # MCP: approval request
                                elif item.type == "mcp_approval_request":
                                    call = {
                                        "id": item.id,
                                        "type": "mcp_call",
                                        "arguments": item.arguments,
                                        "name": item.name,
                                        "server_label": item.server_label,
                                    }
                                    self.ctx.extra["mcp_approval_request"] = call
                                    self.window.core.ctx.update_item(self.ctx)

                        # text chunk
                        elif etype == "response.output_text.delta":
                            response = chunk.delta

                        # ---------- function_call ----------
                        elif etype == "response.output_item.added" and chunk.item.type == "function_call":
                            tool_calls.append({
                                "id": chunk.item.id,
                                "call_id": chunk.item.call_id,
                                "type": "function",
                                "function": {
                                    "name": chunk.item.name,
                                    "arguments": ""
                                }
                            })
                            fn_args_buffers[chunk.item.id] = ""
                        elif etype == "response.function_call_arguments.delta":
                            fn_args_buffers[chunk.item_id] += chunk.delta
                        elif etype == "response.function_call_arguments.done":
                            for tc in tool_calls:
                                if tc["id"] == chunk.item_id:
                                    tc["function"]["arguments"] = fn_args_buffers[chunk.item_id]
                                    break
                            fn_args_buffers.pop(chunk.item_id, None)

                        # ---------- annotations ----------
                        elif etype == "response.output_text.annotation.added":
                            if chunk.annotation['type'] == "url_citation":
                                if citations is None:
                                    citations = []
                                url_citation = chunk.annotation['url']
                                citations.append(url_citation)
                                self.ctx.urls = citations
                            if chunk.annotation['type'] == "container_file_citation":
                                container_id = chunk.annotation['container_id']
                                file_id = chunk.annotation['file_id']
                                files.append({
                                    "container_id": container_id,
                                    "file_id": file_id,
                                })

                        # ---------- computer use ----------
                        elif etype == "response.reasoning_summary_text.delta":
                            response = chunk.delta

                        elif etype == "response.output_item.done":
                           tool_calls, has_calls = self.window.core.gpt.computer.handle_stream_chunk(chunk, tool_calls)
                           if has_calls:
                               force_func_call = True  # force function call if computer use found


                        # ---------- code interpreter ----------
                        elif etype == "response.code_interpreter_call_code.delta":
                            if not is_code:
                                response = "\n\n**Code interpreter**\n```python\n" + chunk.delta
                                is_code = True
                            else:
                                response = chunk.delta
                        elif etype == "response.code_interpreter_call_code.done":
                            response = "\n\n```\n-----------\n"

                        # ---------- image gen ----------
                        elif etype == "response.image_generation_call.partial_image":
                            image_base64 = chunk.partial_image_b64
                            image_bytes = base64.b64decode(image_base64)
                            with open(img_path, "wb") as f:
                                f.write(image_bytes)
                            is_image = True

                        # ---------- response ID ----------
                        elif etype == "response.created":
                            self.ctx.msg_id = chunk.response.id
                            self.window.core.ctx.update_item(self.ctx)  # prevent non-existing response ID

                        # ---------- end / error ----------
                        elif etype in {"response.done", "response.failed", "error"}:
                            pass

                    # OpenAI completion
                    elif chunk_type == "api_completion":
                        if chunk.choices[0].text is not None:
                            response = chunk.choices[0].text

                    # langchain chat
                    elif chunk_type == "langchain_chat":
                        if chunk.content is not None:
                            response = str(chunk.content)

                    # llama chat
                    elif chunk_type == "llama_chat":
                        if chunk.delta is not None:
                            response = str(chunk.delta)
                        tool_chunks = chunk.message.additional_kwargs.get("tool_calls", [])
                        if tool_chunks:
                            for tool_chunk in tool_chunks:
                                id_val = None
                                name = None
                                args = {}
                                if hasattr(tool_chunk, 'arguments'):
                                    args = tool_chunk.arguments
                                elif hasattr(tool_chunk, 'function') and hasattr(tool_chunk.function, 'arguments'):
                                    args = tool_chunk.function.arguments
                                if hasattr(tool_chunk, 'call_id'):
                                    id_val = tool_chunk.call_id
                                elif hasattr(tool_chunk, 'id'):
                                    id_val = tool_chunk.id
                                if hasattr(tool_chunk, 'name'):
                                    name = tool_chunk.name
                                elif hasattr(tool_chunk, 'function') and hasattr(tool_chunk.function, 'name'):
                                    name = tool_chunk.function.name
                                if id_val:
                                    if not args:
                                        args = "{}"  # JSON encoded
                                    tool_call = {
                                        "id": id_val,
                                        "type": "function",
                                        "function": {
                                            "name": name,
                                            "arguments": args
                                        }
                                    }
                                    tool_calls.clear()
                                    tool_calls.append(tool_call)

                    # raw text: llama-index and langchain completion
                    else:
                        if chunk is not None:
                            response = str(chunk)

                    if response is not None and response != "":
                        if begin and response == "":  # prevent empty beginning
                            continue
                        output += response
                        output_tokens += 1
                        data = {
                            "meta": self.ctx.meta,
                            "ctx": self.ctx,
                            "chunk": response,
                            "begin": begin,
                        }
                        event = RenderEvent(RenderEvent.STREAM_APPEND, data)
                        self.eventReady.emit(event)
                        begin = False

                # unpack and store tool calls
                if tool_calls:
                    self.ctx.force_call = force_func_call
                    self.window.core.debug.info("[chat] Tool calls found, unpacking...")
                    self.window.core.command.unpack_tool_calls_chunks(self.ctx, tool_calls)

                # append images
                if is_image:
                    self.window.core.debug.info("[chat] Image generation call found")
                    self.ctx.images = [img_path]  # save image path to ctx

        except Exception as e:
            error = e

        # update ctx
        self.ctx.output = output
        self.ctx.set_tokens(self.ctx.input_tokens, output_tokens)

        # if files from container are found, download them and append to ctx
        if files:
            self.window.core.debug.info("[chat] Container files found, downloading...")
            try:
                self.window.core.gpt.container.download_files(self.ctx, files)
            except Exception as e:
                self.window.core.debug.error(f"[chat] Error downloading container files: {e}")

        self.end.emit(self.ctx)
        if error:
            self.errorOccurred.emit(error)


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

        :param ctx: CtxItem
        :param mode: Mode of stream processing
        :param is_response: Is this a response stream?
        :param reply: Reply text
        :param internal: Internal flag for handling
        :param context: Optional BridgeContext for additional context
        :param extra: Optional extra data for the stream
        """
        self.ctx = ctx
        self.mode = mode
        self.is_response = is_response
        self.reply = reply
        self.internal = internal
        self.context = context
        self.extra = extra if extra is not None else {}

        self.worker = StreamWorker(ctx, self.window)
        self.worker.eventReady.connect(self.handleEvent)
        self.worker.errorOccurred.connect(self.handleError)
        self.worker.end.connect(self.handleEnd)

        self.window.core.debug.info("[chat] Stream begin...")
        self.window.threadpool.start(self.worker)

    @Slot(object)
    def handleEnd(self, ctx: CtxItem):
        """
        Slot for handling end of stream

        This method is called when the stream processing is finished.

        :param ctx: CtxItem
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

        # finish: assistant thread run
        if self.mode == MODE_ASSISTANT:
            self.window.controller.assistant.threads.handle_output_message_after_stream(ctx)
        else:
            # finish: KernelEvent.RESPONSE_OK, KernelEvent.RESPONSE_ERROR
            if self.is_response:
                # post-handle, execute cmd, etc.
                self.window.controller.chat.response.post_handle(
                    ctx=ctx,
                    mode=self.mode,
                    stream=True,
                    reply=self.reply,
                    internal=self.internal
                )

    def handleEvent(self, event):
        """
        Slot for handling RenderEvent

        :param event: RenderEvent
        """
        self.window.dispatch(event)

    def handleError(self, error):
        """
        Slot for handling errors

        :param error: Exception
        """
        self.window.core.debug.log(error)
        if self.is_response:
            if not isinstance(self.extra, dict):
                self.extra = {}
            self.extra["error"] = error
            self.window.controller.chat.response.failed(self.context, self.extra) # send error
            # post-handle, execute cmd, etc.
            self.window.controller.chat.response.post_handle(
                ctx=self.ctx,
                mode=self.mode,
                stream=True,
                reply=self.reply,
                internal=self.internal,
            )

    def log(self, data: object):
        """
        Save debug log data

        :param data: log data
        """
        self.window.core.debug.info(data)