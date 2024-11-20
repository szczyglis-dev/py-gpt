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

from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.core.events import KernelEvent

class BridgeSignals(QObject):
    """Bridge signals"""
    response = Signal(object)  # KernelEvent


class BridgeWorker(QObject, QRunnable):
    """Bridge worker"""
    def __init__(self, *args, **kwargs):
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.signals = BridgeSignals()
        self.args = args
        self.kwargs = kwargs
        self.window = None
        self.context = None
        self.extra = None
        self.mode = None

    @Slot()
    def run(self):
        """Run bridge worker"""
        self.window.core.debug.info("[bridge] Worker started.")
        result = False
        try:
            # Langchain
            if self.mode == "langchain":
                result = self.window.core.chain.call(
                    context=self.context,
                    extra=self.extra,
                )

            # Llama-index: chat with files
            elif self.mode == "llama_index":
                result = self.window.core.idx.chat.call(
                    context=self.context,
                    extra=self.extra,
                )

            # Llama-index: agents
            elif self.mode == "agent_llama":
                result = self.window.core.agents.runner.call(
                    context=self.context,
                    extra=self.extra,
                    signals=self.signals,
                )
                if result:
                    return  # don't emit any signals (handled in agent runner, step by step)
                else:
                    self.extra["error"] = str(self.window.core.agents.runner.get_error())

            # Loop: next step
            elif self.mode == "loop_next":
                result = self.window.core.agents.runner.run_next(
                    context=self.context,
                    extra=self.extra,
                    signals=self.signals,
                )
                if result:
                    return  # don't emit any signals (handled in agent runner, step by step)
                else:
                    self.extra["error"] = str(self.window.core.agents.runner.get_error())

            # API OpenAI: chat, completion, vision, image, assistants
            else:
                result = self.window.core.gpt.call(
                    context=self.context,
                    extra=self.extra,
                )
        except Exception as e:
            if self.signals:
                self.extra["error"] = e
                event = KernelEvent(KernelEvent.RESPONSE_FAILED, {
                    'context': self.context,
                    'extra': self.extra,
                })
                self.signals.response.emit(event)
                return

        # send response to main thread
        if self.signals:
            name = KernelEvent.RESPONSE_OK if result else KernelEvent.RESPONSE_ERROR
            event = KernelEvent(name, {
                'context': self.context,
                'extra': self.extra,
            })
            self.signals.response.emit(event)
