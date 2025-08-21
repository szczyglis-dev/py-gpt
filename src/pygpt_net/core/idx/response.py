#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.21 07:00:00                  #
# ================================================== #

from typing import Any

from pygpt_net.item.model import ModelItem
from pygpt_net.item.ctx import CtxItem

class Response:
    def __init__(self, window=None):
        """
        Response handler for processing responses from LLM or index.

        :param window: Window instance
        """
        self.window = window

    def handle(
            self,
            ctx: CtxItem,
            model: ModelItem,
            llm,
            response: Any,
            cmd_enabled: bool,
            use_react: bool,
            use_index: bool,
            stream: bool
    ) -> None:
        """
        Handle response based on the context, model, and response type.

        :param ctx: Context item
        :param model: Model item
        :param llm: LLM instance
        :param response: Response data
        :param cmd_enabled: Tools enabled flag
        :param use_react: Use REACT flag
        :param use_index: Use index flag
        :param stream: Stream enabled flag
        """
        if cmd_enabled:
            # tools enabled
            if use_react:
                self.from_react(ctx, model, response)  # TOOLS + REACT, non-stream
            else:
                if stream:
                    if use_index:
                        self.from_index_stream(ctx, model, response)  # INDEX + STREAM
                    else:
                        self.from_llm_stream(ctx, model, llm, response)  # LLM + STREAM
                else:
                    if use_index:
                        self.from_index(ctx, model, response)  # TOOLS + INDEX
                    else:
                        self.from_llm(ctx, model, llm, response)  # TOOLS + LLM
        else:
            # no tools
            if stream:
                if use_index:
                    self.from_index_stream(ctx, model, response)  # INDEX + STREAM
                else:
                    self.from_llm_stream(ctx, model, llm, response)  # LLM + STREAM
            else:
                if use_index:
                    self.from_index(ctx, model, response)  # INDEX
                else:
                    self.from_llm(ctx, model, llm, response)  # LLM

    def from_react(
            self,
            ctx: CtxItem,
            model: ModelItem,
            response: Any
    ) -> None:
        """
        Handle response from REACT.

        :param ctx: CtxItem
        :param model: ModelItem
        :param response: Response data
        """
        output = str(response)
        if output is None:
            output = ""
        ctx.set_output(output, "")

    def from_index(
            self,
            ctx: CtxItem,
            model: ModelItem,
            response: Any
    ) -> None:
        """
        Handle response from index.

        :param ctx: CtxItem
        :param model: ModelItem
        :param response: Response data
        """
        output = str(response.response)
        if output is None:
            output = ""
        ctx.set_output(output, "")

    def from_llm(
            self,
            ctx: CtxItem,
            model: ModelItem,
            llm,
            response: Any
    ) -> None:
        """
        Handle response from LLM.

        :param ctx: CtxItem
        :param model: ModelItem
        :param llm: LLM instance
        :param response: Response data
        """
        output = response.message.content
        tool_calls = llm.get_tool_calls_from_response(
            response,
            error_on_no_tool_call=False,
        )
        if output is None:
            output = ""
        ctx.set_output(output, "")
        ctx.tool_calls = self.window.core.command.unpack_tool_calls_from_llama(tool_calls)

    def from_index_stream(
            self,
            ctx: CtxItem,
            model: ModelItem,
            response: Any
    ) -> None:
        """
        Handle streaming response from index.

        :param ctx: CtxItem
        :param model: ModelItem
        :param response: Response data
        """
        ctx.stream = response.response_gen
        ctx.set_output("", "")

    def from_llm_stream(
            self,
            ctx: CtxItem,
            model: ModelItem,
            llm,
            response: Any
    ) -> None:
        """
        Handle streaming response from LLM.

        :param ctx: CtxItem
        :param model: ModelItem
        :param llm: LLM instance
        :param response: Response data
        """
        ctx.stream = response  # chunk is in response.delta
        ctx.set_output("", "")