#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.03 14:00:00                  #
# ================================================== #

from typing import Optional, Tuple

from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.item.ctx import CtxItem


class BaseRunner:
    def __init__(self, window=None):
        """
        Agent runner base class

        :param window: Window instance
        """
        self.window = window

    def add_ctx(
            self,
            from_ctx: CtxItem,
            with_tool_outputs: bool = False
    ) -> CtxItem:
        """
        Prepare response context item

        :param from_ctx: CtxItem (parent, source)
        :param with_tool_outputs: True if tool outputs should be copied
        :return: CtxItem with copied data from parent context item
        """
        return self.window.core.agents.runner.helpers.add_ctx(
            from_ctx=from_ctx,
            with_tool_outputs=with_tool_outputs
        )

    def add_next_ctx(
            self,
            from_ctx: CtxItem,
    ) -> CtxItem:
        """
        Prepare next context item (used for new context in the cycle)

        :param from_ctx: CtxItem (parent, source)
        :return: CtxItem with copied data from parent context item
        """
        return self.window.core.agents.runner.helpers.add_next_ctx(
            from_ctx=from_ctx
        )

    def send_stream(
            self,
            ctx: CtxItem,
            signals: BridgeSignals,
            begin: bool=False
    ):
        """
        Send stream chunk to chat window (BridgeSignals)

        :param ctx: CtxItem
        :param signals: BridgeSignals
        :param begin: True if it is the beginning of the text
        """
        self.window.core.agents.runner.helpers.send_stream(
            ctx=ctx,
            signals=signals,
            begin=begin
        )

    def end_stream(self, ctx: CtxItem, signals: BridgeSignals):
        """
        End of stream in chat window (BridgeSignals)

        :param ctx: CtxItem
        :param signals: BridgeSignals
        """
        self.window.core.agents.runner.helpers.end_stream(
            ctx=ctx,
            signals=signals
        )

    def next_stream(self, ctx: CtxItem, signals: BridgeSignals):
        """
        End of stream in chat window (BridgeSignals)

        :param ctx: CtxItem
        :param signals: BridgeSignals
        """
        self.window.core.agents.runner.helpers.next_stream(
            ctx=ctx,
            signals=signals
        )

    def send_response(
            self,
            ctx: CtxItem,
            signals: BridgeSignals,
            event_name: str,
            **kwargs
    ):
        """
        Send async response to chat window (BridgeSignals)

        :param ctx: CtxItem
        :param signals: BridgeSignals
        :param event_name: kernel event
        :param kwargs: extra data
        """
        self.window.core.agents.runner.helpers.send_response(
            ctx=ctx,
            signals=signals,
            event_name=event_name,
            **kwargs
        )

    def set_busy(
            self,
            signals: BridgeSignals,
            **kwargs
    ):
        """
        Set busy status

        :param signals: BridgeSignals
        :param kwargs: extra data
        """
        self.window.core.agents.runner.helpers.set_busy(
            signals=signals,
            **kwargs
        )

    def set_idle(
            self,
            signals: BridgeSignals,
            **kwargs
    ):
        """
        Set idle status

        :param signals: BridgeSignals
        :param kwargs: extra data
        """
        self.window.core.agents.runner.helpers.set_idle(
            signals=signals,
            **kwargs
        )

    def set_status(
            self,
            signals: BridgeSignals,
            msg: str
    ):
        """
        Set busy status

        :param signals: BridgeSignals
        :param msg: status message
        """
        self.window.core.agents.runner.helpers.set_status(
            signals=signals,
            msg=msg
        )

    def prepare_input(self, prompt: str) -> str:
        """
        Prepare input context

        :param prompt: input text
        """
        return self.window.core.agents.runner.helpers.prepare_input(
            prompt=prompt
        )

    def is_stopped(self) -> bool:
        """
        Check if run is stopped

        :return: True if stopped
        """
        return self.window.core.agents.runner.helpers.is_stopped()

    def set_error(self, error: Exception):
        """
        Set last error

        :param error: Exception to set
        """
        self.window.core.agents.runner.helpers.set_error(
            error=error
        )

    def get_error(self) -> Optional[Exception]:
        """
        Get last error

        :return: last exception or None if no error
        """
        return self.window.core.agents.runner.helpers.get_error()

    def extract_final_response(self, input_text: str) -> Tuple[str, str]:
        """
        Extract final response from input text.

        :param input_text: str
        :return: thought and answer
        """
        return self.window.core.agents.runner.helpers.extract_final_response(
            input_text=input_text
        )