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

from typing import Any

from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem

from .base import BaseRunner


class LlamaAssistant(BaseRunner):
    def __init__(self, window=None):
        """
        Agent runner

        :param window: Window instance
        """
        super(LlamaAssistant, self).__init__(window)
        self.window = window

    def run(
            self,
            agent: Any,
            ctx: CtxItem,
            prompt: str,
            signals: BridgeSignals,
            verbose: bool = False
    ) -> bool:
        """
        Run agent steps

        :param agent: Agent instance
        :param ctx: Input context
        :param prompt: input text
        :param signals: BridgeSignals
        :param verbose: verbose mode
        :return: True if success
        """
        if self.is_stopped():
            return True  # abort if stopped

        if verbose:
            print("Running OpenAI Assistant...")
            print("Assistant: " + str(agent.assistant.id))
            print("Thread: " + str(agent.thread_id))
            print("Model: " + str(agent.assistant.model))
            print("Input: " + str(ctx.input))

        thread_id = agent.thread_id
        ctx.meta.thread = thread_id
        ctx.meta.assistant = agent.assistant.id
        ctx.thread = thread_id

        if self.is_stopped():
            return True  # abort if stopped

        # final response
        self.set_busy(signals)
        response = agent.chat(self.prepare_input(prompt))
        response_ctx = self.add_ctx(ctx)
        response_ctx.thread = thread_id
        response_ctx.set_input("Assistant")
        response_ctx.set_output(str(response))
        response_ctx.extra["agent_output"] = True  # mark as output response
        response_ctx.extra["agent_finish"] = True  # mark as finished
        self.send_response(response_ctx, signals, KernelEvent.APPEND_DATA)
        return True