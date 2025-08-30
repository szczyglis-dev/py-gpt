#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.30 06:00:00                  #
# ================================================== #

import threading
from typing import Any, Dict, Optional, Union, List

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_ASSISTANT,
    MODE_EXPERT,
    MODE_LLAMA_INDEX,
)
from pygpt_net.core.events import KernelEvent, RenderEvent, BaseEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

from .reply import Reply
from .stack import Stack


class Kernel:

    STATE_IDLE = "idle"
    STATE_BUSY = "busy"
    STATE_ERROR = "error"

    __slots__ = (
        "window",
        "replies",
        "stack",
        "halt",
        "busy",
        "last_stack",
        "status",
        "state",
        "not_stop_on_events",
    )

    _INPUT_EVENTS = frozenset((KernelEvent.INPUT_USER, KernelEvent.INPUT_SYSTEM))
    _REPLY_EVENTS = frozenset((KernelEvent.REPLY_ADD, KernelEvent.REPLY_RETURN))
    _STATE_EVENTS = frozenset((KernelEvent.STATE_BUSY, KernelEvent.STATE_IDLE, KernelEvent.STATE_ERROR))

    _REQUEST_EVENTS = frozenset((KernelEvent.REQUEST, KernelEvent.REQUEST_NEXT))
    _OUTPUT_EVENTS = frozenset(
        (
            KernelEvent.RESPONSE_OK,
            KernelEvent.RESPONSE_ERROR,
            KernelEvent.RESPONSE_FAILED,
            KernelEvent.APPEND_BEGIN,
            KernelEvent.APPEND_DATA,
            KernelEvent.APPEND_END,
            KernelEvent.LIVE_APPEND,
            KernelEvent.LIVE_CLEAR,
        )
    )
    _STACK_ADD_EVENTS = frozenset((KernelEvent.TOOL_CALL, KernelEvent.AGENT_CONTINUE, KernelEvent.AGENT_CALL))
    _CALL_EVENTS = frozenset((KernelEvent.CALL, KernelEvent.FORCE_CALL))
    _QUEUE_EVENTS_ALL = _REQUEST_EVENTS | _OUTPUT_EVENTS | _STACK_ADD_EVENTS | _CALL_EVENTS

    _ASYNC_DISABLED_MODES = frozenset(
        (MODE_ASSISTANT, MODE_AGENT, MODE_EXPERT, MODE_AGENT_LLAMA, MODE_AGENT_OPENAI, MODE_LLAMA_INDEX)
    )
    _THREADED_MODES = frozenset((MODE_AGENT_LLAMA, MODE_AGENT_OPENAI))

    def __init__(self, window=None):
        """
        Initialize the Kernel with a window context.

        :param window: The window context to which the kernel will be bound.
        """
        self.window = window
        self.replies = Reply(window)
        self.stack = Stack(window)
        self.halt = False
        self.busy = False
        self.last_stack = []
        self.status = ""
        self.state = self.STATE_IDLE
        self.not_stop_on_events = [
            KernelEvent.APPEND_DATA,
            KernelEvent.INPUT_USER,
            KernelEvent.FORCE_CALL,
            KernelEvent.STATUS,
        ]

    def init(self):
        """
        Initialize the kernel state.
        """
        self.last_stack = []
        self.halt = False
        self.busy = False
        self.state = self.STATE_IDLE
        self.status = ""

    @Slot(object)
    def listener(self, event: BaseEvent):
        """
        Handle incoming events from the window's event dispatcher.

        :param event: BaseEvent: The event to handle.
        """
        if self.halt and event.name not in self.not_stop_on_events:
            return
        self.window.dispatch(event)

    def handle(self, event: KernelEvent):
        """
        Handle the incoming kernel event and process it based on its type.

        :param event: KernelEvent: The event to handle.
        """
        if self.halt and event.name not in self.not_stop_on_events:
            return

        self.store(event)
        name = event.name
        data = event.data
        context = data.get("context")
        extra = data.get("extra")
        response = data.get("response")

        if name in self._INPUT_EVENTS:
            response = self.input(context, extra, event)
        elif name in self._QUEUE_EVENTS_ALL:
            response = self.queue(context, extra, event)
        elif name in self._REPLY_EVENTS:
            response = self.reply(context, extra, event)
        elif name in self._STATE_EVENTS:
            self.set_state(event)
        elif name == KernelEvent.STATUS:
            self.set_status(data.get("status"))

        data["response"] = response

    def input(
        self,
        context: BridgeContext,
        extra: Dict[str, Any],
        event: KernelEvent,
    ):
        """
        Handle input events, such as user input or system input.

        :param context: BridgeContext: The context of the input event.
        :param extra: Dict[str, Any]: Additional data related to the input event.
        :param event: KernelEvent: The event that triggered the input handling.
        :return: Optional[Union[bool, str]]:
        """
        if self.halt and event.name != KernelEvent.INPUT_USER:
            return
        if event.name in self._INPUT_EVENTS:
            w = self.window
            return w.controller.chat.input.send(context, extra)

    def queue(
        self,
        context: BridgeContext,
        extra: Dict[str, Any],
        event: KernelEvent,
    ) -> Optional[Union[bool, str, List[Dict]]]:
        if self.halt and event.name not in self.not_stop_on_events:
            return
        name = event.name
        if name in self._REQUEST_EVENTS:
            return self.call(context, extra, event)
        elif name in self._OUTPUT_EVENTS:
            return self.output(context, extra, event)
        elif name in self._STACK_ADD_EVENTS:
            return self.stack.add(context.reply_context)
        elif name in self._CALL_EVENTS:
            return self.call(context, extra, event)

    def call(
        self,
        context: BridgeContext,
        extra: Dict[str, Any],
        event: KernelEvent,
    ) -> Optional[Union[bool, str]]:
        """
        Handle call events, which may involve making requests or executing commands.

        :param context: BridgeContext: The context of the call event.
        :param extra: Dict[str, Any]: Additional data related to the call event.
        :param event: KernelEvent: The event that triggered the call handling.
        :return: Optional[Union[bool, str]]:
        """
        if self.halt and event.name not in self.not_stop_on_events:
            return
        w = self.window
        name = event.name
        if name == KernelEvent.REQUEST:
            return w.core.bridge.request(context, extra)
        elif name == KernelEvent.REQUEST_NEXT:
            return w.core.bridge.request_next(context, extra)
        elif name in self._CALL_EVENTS:
            return w.core.bridge.call(context, extra)

    def reply(
        self,
        context: BridgeContext,
        extra: Dict[str, Any],
        event: KernelEvent,
    ) -> Optional[List[Dict]]:
        """
        Handle reply events, which may involve adding replies or returning input.

        :param context: BridgeContext: The context of the reply event.
        :param extra: Dict[str, Any]: Additional data related to the reply event.
        :param event: KernelEvent: The event that triggered the reply handling.
        :return: Optional[List[Dict]]:
        """
        if self.halt:
            return
        if event.name == KernelEvent.REPLY_ADD:
            return self.replies.add(context, extra)
        elif event.name == KernelEvent.REPLY_RETURN:
            return self.input(context, extra, KernelEvent(KernelEvent.INPUT_SYSTEM))

    def output(
        self,
        context: BridgeContext,
        extra: Dict[str, Any],
        event: KernelEvent,
    ):
        """
        Handle output events, which may involve processing responses or appending data.

        :param context: BridgeContext: The context of the output event.
        :param extra: Dict[str, Any]: Additional data related to the output event.
        :param event: KernelEvent: The event that triggered the output handling.
        :return: Optional[Union[bool, str]]:
        """
        if self.halt and event.name not in self.not_stop_on_events:
            return
        w = self.window
        resp = w.controller.chat.response
        name = event.name
        if name == KernelEvent.RESPONSE_OK:
            return resp.handle(context, extra, True)
        elif name == KernelEvent.RESPONSE_ERROR:
            return resp.handle(context, extra, False)
        elif name == KernelEvent.RESPONSE_FAILED:
            return resp.failed(context, extra)
        elif name == KernelEvent.APPEND_BEGIN:
            return resp.begin(context, extra)
        elif name == KernelEvent.APPEND_DATA:
            return resp.append(context, extra)
        elif name == KernelEvent.APPEND_END:
            return resp.end(context, extra)
        elif name == KernelEvent.LIVE_APPEND:
            return resp.live_append(context, extra)
        elif name == KernelEvent.LIVE_CLEAR:
            return resp.live_clear(context, extra)

    def restart(self):
        """
        Restart the kernel by dispatching a restart event and re-initializing the state.
        """
        self.window.dispatch(KernelEvent(KernelEvent.RESTART))
        self.init()

    def terminate(self):
        """
        Terminate the kernel by dispatching a terminate event, stopping the window, and destroying plugins.
        """
        self.window.dispatch(KernelEvent(KernelEvent.TERMINATE))
        self.stop(exit=True)
        self.window.controller.plugins.destroy()
        self.window.controller.realtime.shutdown()

    def stop(self, exit: bool = False):
        """
        Stop the kernel and its associated processes.

        :param exit: If True, exit the application after stopping.
        """
        self.halt = True
        w = self.window
        w.controller.chat.common.stop(exit=exit)
        w.controller.audio.stop_audio()
        if not exit:
            w.dispatch(KernelEvent(KernelEvent.STOP))
            self.set_state(KernelEvent(KernelEvent.STATE_IDLE, {"msg": trans("status.stopped")}))

    def set_state(self, event: KernelEvent):
        """
        Set the kernel state based on the event received.

        :param event: KernelEvent: The event containing the state information.
        """
        name = event.name
        w = self.window
        tray = w.ui.tray
        is_main = self.is_main_thread()

        if name == KernelEvent.STATE_BUSY:
            self.busy = True
            self.state = self.STATE_BUSY
            tray.set_icon(self.STATE_BUSY)
            if not self.halt and is_main:
                w.dispatch(RenderEvent(RenderEvent.STATE_BUSY))
        elif name == KernelEvent.STATE_IDLE:
            self.busy = False
            self.state = self.STATE_IDLE
            tray.set_icon(self.STATE_IDLE)
            if is_main:
                w.dispatch(RenderEvent(RenderEvent.STATE_IDLE))
        elif name == KernelEvent.STATE_ERROR:
            self.busy = False
            self.state = self.STATE_ERROR
            tray.set_icon(self.STATE_ERROR)
            if is_main:
                w.dispatch(RenderEvent(RenderEvent.STATE_ERROR))

        msg = event.data.get("msg", None)
        if msg is not None:
            self.set_status(msg)

    def set_status(self, status: str):
        """
        Set the status message for the kernel and update the UI.

        :param status: str: The status message to set.
        """
        self.status = status
        self.window.ui.status(status)
        QApplication.processEvents()  # process events to update UI

    def resume(self):
        """
        Resume the kernel operation after it has been halted.
        """
        self.halt = False

    def stopped(self) -> bool:
        """
        Check if the kernel is currently halted.

        :return: bool: True if the kernel is halted, False otherwise.
        """
        return self.halt

    def store(self, event):
        """
        Store the event in the kernel's stack for later processing.

        :param event: BaseEvent: The event to store.
        """
        return

    def async_allowed(self, ctx: CtxItem) -> bool:
        """
        Check if asynchronous operations are allowed based on the current mode and context.

        :param ctx: CtxItem: The context item containing information about the current operation.
        :return: bool: True if asynchronous operations are allowed, False otherwise.
        """
        if self.window.core.config.get("mode") in self._ASYNC_DISABLED_MODES:
            return False
        if ctx.agent_call:
            return False
        controller = self.window.controller
        agent = controller.agent
        if agent.legacy.enabled() or agent.experts.enabled():
            return False
        return True

    def is_threaded(self) -> bool:
        """
        Check if the current mode allows for threaded operations.

        :return: bool: True if the current mode is threaded, False otherwise.
        """
        return self.window.core.config.get("mode") in self._THREADED_MODES

    def is_main_thread(self) -> bool:
        """
        Check if the current thread is the main thread.

        :return: bool: True if the current thread is the main thread, False otherwise.
        """
        return threading.current_thread() is threading.main_thread()