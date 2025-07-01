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

from typing import Any
from pygpt_net.item.model import ModelItem
from pygpt_net.item.ctx import CtxItem

class Response:
    def __init__(self, window=None):
        """
        Response

        :param window: Window instance
        """
        self.window = window

    def from_react(
            self,
            ctx: CtxItem,
            model: ModelItem,
            response: Any
    ) -> None:
        output = str(response.response)
        if output is None:
            output = ""
        ctx.set_output(output, "")

    def from_index(
            self,
            ctx: CtxItem,
            model: ModelItem,
            response: Any
    ) -> None:
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
        ctx.stream = response.response_gen
        ctx.set_output("", "")

    def from_llm_stream(
            self,
            ctx: CtxItem,
            model: ModelItem,
            llm,
            response: Any
    ) -> None:
        ctx.stream = response  # chunk is in response.delta
        ctx.set_output("", "")