#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.28 16:00:00                  #
# ================================================== #

from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.core.types import (
    MODE_AGENT_LLAMA,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_ASSISTANT,
)
from pygpt_net.core.events import KernelEvent, Event


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
            # POST PROMPT ASYNC: handle post prompt async event
            self.handle_post_prompt_async()

            # ADDITIONAL CONTEXT: append additional context from attachments
            if self.mode != MODE_ASSISTANT:
                self.handle_additional_context()

            # POST PROMPT END: handle post prompt end event
            self.handle_post_prompt_end()

            # Langchain
            if self.mode == MODE_LANGCHAIN:
                raise Exception("Langchain mode is deprecated from v2.5.20 and no longer supported. ")
                """
                result = self.window.core.chain.call(
                    context=self.context,
                    extra=self.extra,
                )
                """

            # LlamaIndex: chat with files
            if self.mode == MODE_LLAMA_INDEX:
                result = self.window.core.idx.chat.call(
                    context=self.context,
                    extra=self.extra,
                )

            # LlamaIndex: agents
            elif self.mode == MODE_AGENT_LLAMA:
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
            elif self.mode == "loop_next":  # virtual mode
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

    def handle_post_prompt_async(self):
        """Handle post prompt async event"""
        event = Event(Event.POST_PROMPT_ASYNC, {
            'mode': self.context.mode,
            'reply': self.context.ctx.reply,
            'value': self.context.system_prompt,
        })
        event.ctx = self.context.ctx
        self.window.dispatch(event)
        self.context.system_prompt = event.data['value']

    def handle_post_prompt_end(self):
        """Handle post prompt end event"""
        event = Event(Event.POST_PROMPT_END, {
            'mode': self.context.mode,
            'reply': self.context.ctx.reply,
            'value': self.context.system_prompt,
        })
        event.ctx = self.context.ctx
        self.window.dispatch(event)
        self.context.system_prompt = event.data['value']

    def handle_additional_context(self):
        """Append additional context"""
        ctx = self.context.ctx
        if ctx is None:
            return
        if ctx.meta is None:
            return
        if not self.window.controller.chat.attachment.has_context(ctx.meta):
            return
        ad_context = self.window.controller.chat.attachment.get_context(ctx, self.context.history)
        ad_mode = self.window.controller.chat.attachment.get_mode()
        if ad_context:
            self.context.prompt += "\n\n" + ad_context  # append to input text
            if (ad_mode == self.window.controller.chat.attachment.MODE_QUERY_CONTEXT
                    or self.mode == MODE_AGENT_LLAMA):
                ctx.hidden_input = ad_context  # store for future use, only if query context
                # if full context or summary, then whole extra context will be applied to current input
