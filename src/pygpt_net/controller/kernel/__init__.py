#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 03:00:00                  #
# ================================================== #

from PySide6.QtCore import QObject, Slot

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem

from .reply import Reply
from .stack import Stack

class Kernel(QObject):

    def __init__(self, window=None):
        super(Kernel, self).__init__(window)
        self.window = window
        self.replies = Reply(window)
        self.stack = Stack(window)
        self.halt = False

    def init(self):
        """Init kernel"""
        self.halt = False

    @Slot(object)
    def listener(self, event: KernelEvent):
        """
        Async listener for kernel events

        :param event: kernel event
        """
        if self.stopped() and event.name != KernelEvent.INPUT_USER:
            return

        self.window.core.dispatcher.dispatch(event)

    def handle(self, event: KernelEvent):
        """
        Handle kernel events

        :param event: kernel event
        """
        if self.stopped() and event.name != KernelEvent.INPUT_USER:
            return

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
            KernelEvent.SET_STATUS,
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

        event.data["response"] = response  # update response

    def input(self, context: BridgeContext, extra: dict, event: KernelEvent) -> any:
        """
        Input message to kernel

        :param context: bridge context
        :param extra: extra data
        :param event: kernel event
        :return: response
        """
        if self.stopped() and event.name != KernelEvent.INPUT_USER:
            return

        if event.name in [
            KernelEvent.INPUT_USER,
            KernelEvent.INPUT_SYSTEM,
        ]:
            return self.window.controller.chat.input.send(context, extra)

    def queue(self, context: BridgeContext, extra: dict, event: KernelEvent) -> any:
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
            KernelEvent.SET_STATUS,
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

    def call(self, context: BridgeContext, extra: dict, event: KernelEvent) -> any:
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

    def reply(self, context: BridgeContext, extra: dict, event: KernelEvent) -> any:
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

    def output(self, context: BridgeContext, extra: dict, event: KernelEvent) -> any:
        """
        Handle output from kernel

        :param context: bridge context
        :param extra: extra data
        :param event: kernel event
        :return: response
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
        elif event.name == KernelEvent.SET_STATUS:
            return self.window.controller.chat.response.update_status(context, extra)

    def restart(self):
        """Restart kernel"""
        pass

    def terminate(self):
        """Terminate kernel"""
        pass  # to output end

    def stop(self):
        """Stop kernel"""
        self.halt = True
        self.window.controller.chat.common.stop()

    def resume(self):
        """Resume kernel"""
        self.halt = False

    def stopped(self) -> bool:
        """
        Check if kernel is stopped

        :return: True if stopped
        """
        return self.halt

    def async_allowed(self, ctx: CtxItem) -> bool:
        """
        Check if async execution are allowed

        :param ctx: context item
        :return: True if async commands are allowed
        """
        disabled = ["assistant", "agent", "expert", "agent_llama"]
        if self.window.core.config.get("mode") in disabled:
            return False
        if ctx.agent_call:
            return False
        if self.window.controller.agent.enabled() or self.window.controller.agent.experts.enabled():
            return False
        return True