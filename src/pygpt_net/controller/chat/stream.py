#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.01 01:00:00                  #
# ================================================== #
import base64
import uuid
from typing import Any

from PySide6.QtWidgets import QApplication

from pygpt_net.core.events import RenderEvent
from pygpt_net.item.ctx import CtxItem


class Stream:
    def __init__(self, window=None):
        """
        Stream controller

        :param window: Window instance
        """
        self.window = window

    def append(self, ctx: CtxItem):
        """
        Handle stream response

        :param ctx: CtxItem
        """
        output = ""
        output_tokens = 0
        begin = True
        error = None
        fn_args_buffers = {}
        citations = []
        img_path = self.window.core.image.gen_unique_path(ctx)
        is_image = False
        is_code = False

        # chunks: stream begin
        data = {
            "meta": ctx.meta,
            "ctx": ctx,
        }
        event = RenderEvent(RenderEvent.STREAM_BEGIN, data)
        self.window.dispatch(event)

        # read stream
        try:
            if ctx.stream is not None:
                self.log("[chat] Stream begin...")  # log

                tool_calls = []

                for chunk in ctx.stream:
                    # if force stop then break
                    if self.window.controller.kernel.stopped():
                        break

                    if error is not None:
                        break  # break if error

                    etype = None
                    response = None
                    chunk_type = "raw"
                    if ctx.use_responses_api:
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
                                    ctx.urls = citations
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
                        if etype == "response.output_text.delta":
                            response = chunk.delta

                        # ---------- function_call ----------
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
                                ctx.urls = citations

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
                            ctx.msg_id = chunk.response.id # store previous response ID

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
                                id = None
                                name = None
                                args = {}
                                if hasattr(tool_chunk, 'arguments'):
                                    args = tool_chunk.arguments
                                elif hasattr(tool_chunk, 'function') and hasattr(tool_chunk.function, 'arguments'):
                                    args = tool_chunk.function.arguments
                                if hasattr(tool_chunk, 'call_id'):
                                    id = tool_chunk.call_id
                                elif hasattr(tool_chunk, 'id'):
                                    id = tool_chunk.id
                                if hasattr(tool_chunk, 'name'):
                                    name = tool_chunk.name
                                elif hasattr(tool_chunk, 'function') and hasattr(tool_chunk.function, 'name'):
                                    name = tool_chunk.function.name
                                if id:
                                    if not args:
                                        args = "{}"  # JSON encoded
                                    tool_call = {
                                            "id": id,
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
                            "meta": ctx.meta,
                            "ctx": ctx,
                            "chunk": response,
                            "begin": begin,
                        }
                        event = RenderEvent(RenderEvent.STREAM_APPEND, data)
                        self.window.dispatch(event)
                        QApplication.processEvents()  # process events to update UI after each chunk
                        begin = False

                # unpack and store tool calls
                if tool_calls:
                    self.window.core.debug.info("[chat] Tool calls found, unpacking...")
                    self.window.core.command.unpack_tool_calls_chunks(ctx, tool_calls)

                # append images
                if is_image:
                    self.window.core.debug.info("[chat] Image generation call found")
                    ctx.images = [img_path]  # save image path to ctx

        except Exception as e:
            self.window.core.debug.log(e)
            error = e

        self.window.controller.ui.update_tokens()  # update UI tokens

        # update ctx
        ctx.output = output
        ctx.set_tokens(ctx.input_tokens, output_tokens)

        # chunks: stream end
        data = {
            "meta": ctx.meta,
            "ctx": ctx,
        }
        event = RenderEvent(RenderEvent.STREAM_END, data)
        self.window.dispatch(event)

        # log
        self.log("[chat] Stream end.")

        if error is not None:
            raise error  # raise error if any, to display in UI

    def log(self, data: Any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)
