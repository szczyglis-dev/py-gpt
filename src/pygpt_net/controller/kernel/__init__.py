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

import time
from typing import Any, Dict, Optional, Union, List

from PySide6.QtCore import QObject, Slot

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_ASSISTANT,
    MODE_EXPERT, MODE_LLAMA_INDEX,
)
from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

from .reply import Reply
from .stack import Stack


class Kernel(QObject):

    STATE_IDLE = "idle"
    STATE_BUSY = "busy"
    STATE_ERROR = "error"

    def __init__(self, window=None):
        super(Kernel, self).__init__(window)
        self.window = window
        self.replies = Reply(window)
        self.stack = Stack(window)
        self.halt = False
        self.busy = False
        self.last_stack = []
        self.status = ""
        self.state = self.STATE_IDLE

    def init(self):
        """Init kernel"""
        self.last_stack = []
        self.halt = False
        self.busy = False
        self.state = self.STATE_IDLE
        self.status = ""

    @Slot(object)
    def listener(self, event: KernelEvent):
        """
        Async listener for kernel events

        :param event: kernel event
        """
        if self.stopped() and event.name != KernelEvent.INPUT_USER:
            return

        self.window.dispatch(event)  # return event to handle()

    def handle(self, event: KernelEvent):
        """
        Handle kernel events

        :param event: kernel event
        """
        if self.stopped() and event.name != KernelEvent.INPUT_USER:
            return

        self.store(event)  # store event in stack
        name = event.name
        context = event.data.get("context")
        extra = event.data.get("extra")
        response = event.data.get("response")

        if name in [
            KernelEvent.INPUT_USER,
            KernelEvent.INPUT_SYSTEM,
        ]:
            response = self.input(context, extra, event)
        elif name in [
            KernelEvent.REQUEST,
            KernelEvent.REQUEST_NEXT,
            KernelEvent.RESPONSE_OK,
            KernelEvent.RESPONSE_ERROR,
            KernelEvent.RESPONSE_FAILED,
            KernelEvent.APPEND_BEGIN,
            KernelEvent.APPEND_DATA,
            KernelEvent.APPEND_END,
            KernelEvent.TOOL_CALL,
            KernelEvent.AGENT_CONTINUE,
            KernelEvent.AGENT_CALL,
            KernelEvent.CALL,
        ]:
            response = self.queue(context, extra, event)
        elif name in [
            KernelEvent.REPLY_ADD,
            KernelEvent.REPLY_RETURN,
        ]:
            response = self.reply(context, extra, event)

        elif name in [
            KernelEvent.STATE_BUSY,
            KernelEvent.STATE_IDLE,
            KernelEvent.STATE_ERROR,
        ]:
            self.set_state(event)

        elif name == KernelEvent.STATUS:
            self.set_status(event.data.get("status"))

        event.data["response"] = response  # update response

    def input(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            event: KernelEvent
    ):
        """
        Input message to kernel

        :param context: bridge context
        :param extra: extra data
        :param event: kernel event
        """
        if self.stopped() and event.name != KernelEvent.INPUT_USER:
            return

        if event.name in [
            KernelEvent.INPUT_USER,
            KernelEvent.INPUT_SYSTEM,
        ]:
            return self.window.controller.chat.input.send(context, extra)

    def queue(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            event: KernelEvent
    ) -> Optional[Union[bool, str, List[Dict]]]:
        """
        Queue messages to kernel

        :param context: bridge context
        :param extra: extra data
        :param event: kernel event
        :return: response
        """
        if self.stopped():
            return

        if event.name in [
            KernelEvent.REQUEST,
            KernelEvent.REQUEST_NEXT,
        ]:
            return self.call(context, extra, event)
        elif event.name in [
            KernelEvent.RESPONSE_OK,
            KernelEvent.RESPONSE_ERROR,
            KernelEvent.RESPONSE_FAILED,
            KernelEvent.APPEND_BEGIN,
            KernelEvent.APPEND_DATA,
            KernelEvent.APPEND_END,
        ]:
            return self.output(context, extra, event)
        elif event.name in [
            KernelEvent.TOOL_CALL,
            KernelEvent.AGENT_CONTINUE,
            KernelEvent.AGENT_CALL,
        ]:
            return self.stack.add(context.reply_context)  # to reply stack
        elif event.name == KernelEvent.CALL:
            return self.call(context, extra, event)

    def call(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            event: KernelEvent
    ) -> Optional[Union[bool, str]]:
        """
        Execute message

        :param context: bridge context
        :param extra: extra data
        :param event: kernel event
        :return: response
        """
        if self.stopped():
            return

        if event.name == KernelEvent.REQUEST:
            return self.window.core.bridge.request(context, extra)
        elif event.name == KernelEvent.REQUEST_NEXT:
            return self.window.core.bridge.request_next(context, extra)
        elif event.name == KernelEvent.CALL:
            return self.window.core.bridge.call(context, extra)

    def reply(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            event: KernelEvent
    ) -> Optional[List[Dict]]:
        """
        Queue reply message

        :param context: bridge context
        :param extra: extra data
        :param event: kernel event
        :return: response
        """
        if self.stopped():
            return

        if event.name == KernelEvent.REPLY_ADD:
            return self.replies.add(context, extra)
        elif event.name == KernelEvent.REPLY_RETURN:
            return self.input(context, extra, KernelEvent(KernelEvent.INPUT_SYSTEM))

    def output(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            event: KernelEvent
    ):
        """
        Handle output from kernel

        :param context: bridge context
        :param extra: extra data
        :param event: kernel event
        """
        if self.stopped():
            return

        if event.name == KernelEvent.RESPONSE_OK:
            return self.window.controller.chat.response.handle(context, extra, True)
        elif event.name == KernelEvent.RESPONSE_ERROR:
            return self.window.controller.chat.response.handle(context, extra, False)
        elif event.name == KernelEvent.RESPONSE_FAILED:
            return self.window.controller.chat.response.failed(context, extra)
        elif event.name == KernelEvent.APPEND_BEGIN:
            return self.window.controller.chat.response.begin(context, extra)
        elif event.name == KernelEvent.APPEND_DATA:
            return self.window.controller.chat.response.append(context, extra)
        elif event.name == KernelEvent.APPEND_END:
            return self.window.controller.chat.response.end(context, extra)

    def restart(self):
        """Restart kernel"""
        self.window.dispatch(KernelEvent(KernelEvent.RESTART))
        self.init()

    def terminate(self):
        """Terminate kernel"""
        self.window.dispatch(KernelEvent(KernelEvent.TERMINATE))
        self.stop(exit=True)
        self.window.ui.hide_loading()
        self.window.controller.plugins.destroy()

    def stop(self, exit: bool = False):
        """
        Stop kernel

        :param exit: on app exit
        """
        self.halt = True
        self.window.controller.chat.common.stop(exit=exit)  # it stops legacy agent also
        self.window.controller.audio.stop_audio()
        if not exit:
            self.window.dispatch(KernelEvent(KernelEvent.STOP))
            self.set_state(KernelEvent(KernelEvent.STATE_IDLE, {"msg": trans("status.stopped")}))

    def set_state(self, event: KernelEvent):
        """
        Set kernel state

        :param: KernelEvent event
        """
        # update state
        if event.name == KernelEvent.STATE_BUSY:
            self.busy = True
            self.state = self.STATE_BUSY
            self.window.ui.tray.set_icon(self.STATE_BUSY)
            if not self.halt:
                self.window.ui.show_loading()
        elif event.name == KernelEvent.STATE_IDLE:
            self.busy = False
            self.state = self.STATE_IDLE
            self.window.ui.tray.set_icon(self.STATE_IDLE)
            self.window.ui.hide_loading()
        elif event.name == KernelEvent.STATE_ERROR:
            self.busy = False
            self.state = self.STATE_ERROR
            self.window.ui.tray.set_icon(self.STATE_ERROR)
            self.window.ui.hide_loading()

        # update message if provided
        msg = event.data.get("msg", None)
        if msg is not None:
            self.set_status(msg)

    def set_status(self, status: str):
        """
        Set kernel status

        :param status: status
        """
        self.status = status
        self.window.ui.status(status)

    def resume(self):
        """Resume kernel"""
        self.halt = False

    def stopped(self) -> bool:
        """
        Check if kernel is stopped

        :return: True if stopped
        """
        return self.halt

    def store(self, event):
        """
        Store event in stack

        :param event: event
        """
        # last 30 events
        if len(self.last_stack) > 30:
            self.last_stack.pop(0)
        ts = time.strftime("%H:%M:%S: ", time.localtime())
        self.last_stack.append(ts + event.name)

    def async_allowed(self, ctx: CtxItem) -> bool:
        """
        Check if async execution are allowed

        :param ctx: context item
        :return: True if async commands are allowed
        """
        disabled = [MODE_ASSISTANT, MODE_AGENT, MODE_EXPERT, MODE_AGENT_LLAMA, MODE_LLAMA_INDEX]
        if self.window.core.config.get("mode") in disabled:
            return False
        if ctx.agent_call:
            return False
        if self.window.controller.agent.legacy.enabled() or self.window.controller.agent.experts.enabled():
            return False
        return True

    def is_threaded(self) -> bool:
        """
        Check if plugin run is threaded

        :return: True if threaded
        """
        if self.window.core.config.get("mode") == MODE_AGENT_LLAMA:
            return True
        return False