#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.28 16:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QApplication

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

        # chunks: stream begin
        self.window.controller.chat.render.stream_begin()

        # read stream
        try:
            if ctx.stream is not None:
                self.log("Reading stream...")  # log

                tool_calls = []

                for chunk in ctx.stream:
                    # if force stop then break
                    if self.window.controller.chat.input.stop:
                        break

                    response = None
                    chunk_type = "raw"
                    if (hasattr(chunk, 'choices')
                            and chunk.choices[0] is not None
                            and hasattr(chunk.choices[0], 'delta')
                            and chunk.choices[0].delta is not None):
                        chunk_type = "api_chat"
                    elif (hasattr(chunk, 'choices')
                          and chunk.choices[0] is not None
                          and hasattr(chunk.choices[0], 'text')
                          and chunk.choices[0].text is not None):
                        chunk_type = "api_completion"
                    elif (hasattr(chunk, 'content')
                          and chunk.content is not None):
                        chunk_type = "langchain_chat"

                    # OpenAI chat completion
                    if chunk_type == "api_chat":
                        if chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                            response = chunk.choices[0].delta.content
                        elif chunk.choices[0].delta and chunk.choices[0].delta.tool_calls:
                            tool_chunks = chunk.choices[0].delta.tool_calls
                            for tool_chunk in tool_chunks:
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

                    # OpenAI completion
                    elif chunk_type == "api_completion":
                        if chunk.choices[0].text is not None:
                            response = chunk.choices[0].text

                    # langchain chat
                    elif chunk_type == "langchain_chat":
                        if chunk.content is not None:
                            response = chunk.content

                    # raw text: llama-index and langchain completion
                    else:
                        if chunk is not None:
                            response = chunk

                    if response is not None:
                        if begin and response == "":  # prevent empty beginning
                            continue
                        output += response
                        output_tokens += 1
                        self.window.controller.chat.render.append_chunk(
                            ctx,
                            response,
                            begin,
                        )
                        QApplication.processEvents()  # process events to update UI after each chunk
                        begin = False

                # unpack and store tool calls
                if tool_calls:
                    self.window.core.command.unpack_tool_calls_chunks(ctx, tool_calls)

        except Exception as e:
            self.window.core.debug.log(e)

        self.window.controller.ui.update_tokens()  # update UI tokens

        # update ctx
        ctx.output = output
        ctx.set_tokens(ctx.input_tokens, output_tokens)

        # chunks: stream end
        self.window.controller.chat.render.stream_end()

        # log
        self.log("End of stream.")

    def log(self, data: any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)
