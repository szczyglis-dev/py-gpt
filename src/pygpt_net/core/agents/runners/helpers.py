#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.14 01:00:00                  #
# ================================================== #

import copy
import re
import time
from typing import Optional, Tuple

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.events import Event, KernelEvent, RenderEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

class Helpers:
    def __init__(self, window=None):
        """
        Helpers for agent runner

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
        ctx = CtxItem()
        ctx.meta = from_ctx.meta
        ctx.internal = True
        ctx.current = True  # mark as current context item
        ctx.mode = from_ctx.mode
        ctx.model = from_ctx.model
        ctx.prev_ctx = from_ctx
        ctx.images = from_ctx.images  # copy from parent if appended from plugins
        ctx.urls = from_ctx.urls  # copy from parent if appended from plugins
        ctx.attachments = from_ctx.attachments  # copy from parent if appended from plugins
        ctx.files = from_ctx.files  # copy from parent if appended from plugins
        ctx.live = True

        if with_tool_outputs:
            # copy tool outputs from parent context item
            ctx.cmds = copy.deepcopy(from_ctx.cmds)
            ctx.results = copy.deepcopy(from_ctx.results)
            if "tool_output" in from_ctx.extra:
                ctx.extra["tool_output"] = copy.deepcopy(from_ctx.extra["tool_output"])
        return ctx

    def add_next_ctx(
            self,
            from_ctx: CtxItem,
    ) -> CtxItem:
        """
        Prepare next context item (used for new context in the cycle)

        :param from_ctx: CtxItem (parent, source)
        :return: CtxItem with copied data from parent context item
        """
        ctx = CtxItem()
        ctx.meta = from_ctx.meta
        ctx.mode = from_ctx.mode
        ctx.model = from_ctx.model
        ctx.prev_ctx = from_ctx
        # ctx.images = from_ctx.images  # copy from parent if appended from plugins
        # ctx.urls = from_ctx.urls  # copy from parent if appended from plugins
        # ctx.attachments = from_ctx.attachments # copy from parent if appended from plugins
        # ctx.files = from_ctx.files  # copy from parent if appended from plugins
        ctx.extra = from_ctx.extra.copy()  # copy extra data
        ctx.output_timestamp = int(time.time())  # set output timestamp
        return ctx

    def send_stream(
            self,
            ctx: CtxItem,
            signals: BridgeSignals,
            begin: bool = False
    ):
        """
        Send stream chunk to chat window (BridgeSignals)

        :param ctx: CtxItem
        :param signals: BridgeSignals
        :param begin: True if it is the beginning of the text
        """
        if signals is None:
            return
        chunk = ctx.stream.replace("<execute>", "\n```python\n").replace("</execute>", "\n```\n") if ctx.stream else ""
        data = {
            "meta": ctx.meta,
            "ctx": ctx,
            "chunk": chunk,  # use stream for live output
            "begin": begin,
        }
        event = RenderEvent(RenderEvent.STREAM_APPEND, data)
        signals.response.emit(event)

    def end_stream(self, ctx: CtxItem, signals: BridgeSignals):
        """
        End of stream in chat window (BridgeSignals)

        :param ctx: CtxItem
        :param signals: BridgeSignals
        """
        if signals is None:
            return
        data = {
            "meta": ctx.meta,
            "ctx": ctx,
        }
        event = RenderEvent(RenderEvent.STREAM_END, data)
        signals.response.emit(event)

    def next_stream(self, ctx: CtxItem, signals: BridgeSignals):
        """
        End of stream in chat window (BridgeSignals)

        :param ctx: CtxItem
        :param signals: BridgeSignals
        """
        if signals is None:
            return
        data = {
            "meta": ctx.meta,
            "ctx": ctx,
        }
        event = RenderEvent(RenderEvent.STREAM_NEXT, data)
        signals.response.emit(event)

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
        if signals is None:
            return
        context = BridgeContext()
        context.ctx = ctx
        event = KernelEvent(event_name, {
            'context': context,
            'extra': kwargs,
        })
        signals.response.emit(event)

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
        if signals is None:
            return
        data = {
            "id": "agent",
            "msg": trans("status.agent.reasoning"),
        }
        event = KernelEvent(KernelEvent.STATE_BUSY, data)
        data.update(kwargs)
        signals.response.emit(event)

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
        if signals is None:
            return
        data = {
            "id": "agent",
        }
        event = KernelEvent(KernelEvent.STATE_IDLE, data)
        data.update(kwargs)
        signals.response.emit(event)

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
        if signals is None:
            return
        data = {
            "status": msg,
        }
        event = KernelEvent(KernelEvent.STATUS, data)
        signals.response.emit(event)

    def prepare_input(self, prompt: str) -> str:
        """
        Prepare input context

        :param prompt: input text
        """
        event = Event(Event.AGENT_PROMPT, {
            'value': prompt,
        })
        self.window.dispatch(event)
        return event.data['value']

    def is_stopped(self) -> bool:
        """
        Check if run is stopped

        :return: True if stopped
        """
        return self.window.controller.kernel.stopped()

    def set_error(self, error: Exception):
        """
        Set last error

        :param error: Exception to set
        """
        self.window.core.debug.error(error)
        self.window.core.agents.runner.last_error = error

    def get_error(self) -> Optional[Exception]:
        """
        Get last error

        :return: last exception or None if no error
        """
        return self.window.core.agents.runner.last_error

    def extract_final_response(self, input_text: str) -> Tuple[str, str]:
        """
        Extract final response from input text.

        :param input_text: str
        :return: thought and answer
        """
        pattern = r"\s*Thought:(.*?)Answer:(.*?)(?:$)"

        match = re.search(pattern, input_text, re.DOTALL)
        if not match:
            return "", ""

        thought = match.group(1).strip()
        answer = match.group(2).strip()
        return thought, answer