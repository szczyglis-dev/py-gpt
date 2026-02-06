#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.02.06 01:00:00                  #
# ================================================== #

from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.core.types import (
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_ASSISTANT,
    MODE_VISION,
    MODE_LOOP_NEXT,
    MODE_CHAT,
    MODE_RESEARCH,
    MODE_COMPUTER,
)
from pygpt_net.core.events import KernelEvent, Event


class BridgeSignals(QObject):
    """Bridge signals"""
    response = Signal(object)  # KernelEvent


class BridgeWorker(QRunnable):
    __slots__ = ('signals', 'rt_signals', 'args', 'kwargs', 'window', 'context', 'extra', 'mode')

    """Bridge worker"""
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.signals = BridgeSignals()
        self.rt_signals = None
        self.args = args
        self.kwargs = kwargs
        self.window = None
        self.context = None
        self.extra = None
        self.mode = None

    @Slot()
    def run(self):
        """Run bridge worker"""
        core = self.window.core
        core.debug.info("[bridge] Worker started.")
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
                result = core.chain.call(
                    context=self.context,
                    extra=self.extra,
                )
                """
            elif self.mode == MODE_VISION:
                raise Exception("Vision mode is deprecated from v2.6.30 and integrated into Chat. ")

            # LlamaIndex: chat with files
            if self.mode == MODE_LLAMA_INDEX:
                result = core.idx.chat.call(
                    context=self.context,
                    extra=self.extra,
                    signals=self.signals,
                )

            # Agents (OpenAI, Llama)
            elif self.mode in (
                    MODE_AGENT_LLAMA,
                    MODE_AGENT_OPENAI
            ):
                result = core.agents.runner.call(
                    context=self.context,
                    extra=self.extra,
                    signals=self.signals,
                )
                if result:
                    self.cleanup()
                    return  # don't emit any signals (handled in agent runner, step by step)
                else:
                    self.extra["error"] = str(core.agents.runner.get_error())

            # Agents loop: next step
            elif self.mode == MODE_LOOP_NEXT:  # virtual mode
                result = core.agents.runner.loop.run_next(
                    context=self.context,
                    extra=self.extra,
                    signals=self.signals,
                )
                if result:
                    return  # don't emit any signals (handled in agent runner, step by step)
                else:
                    self.extra["error"] = str(core.agents.runner.get_error())

            # API SDK: chat, completion, vision, image, assistants
            else:
                sdk = "openai"  # default to OpenAI SDK
                model = self.context.model
                if model.provider == "google":
                    if core.config.get("api_native_google", False):
                        sdk = "google"
                elif model.provider == "anthropic":
                    if core.config.get("api_native_anthropic", False):
                        sdk = "anthropic"
                elif model.provider == "x_ai":
                    if core.config.get("api_native_xai", False):
                        sdk = "x_ai"

                # call appropriate SDK
                if sdk == "google":
                    core.debug.info("[bridge] Using Google SDK.")
                    result = core.api.google.call(
                        context=self.context,
                        extra=self.extra,
                        rt_signals=self.rt_signals,
                    )
                elif sdk == "anthropic":
                    core.debug.info("[bridge] Using Anthropic SDK.")
                    result = core.api.anthropic.call(
                        context=self.context,
                        extra=self.extra,
                        rt_signals=self.rt_signals,
                    )
                elif sdk == "x_ai":
                    core.debug.info("[bridge] Using xAI SDK.")
                    result = core.api.xai.call(
                        context=self.context,
                        extra=self.extra,
                        rt_signals=self.rt_signals,
                    )
                elif sdk == "openai":
                    core.debug.info("[bridge] Using OpenAI SDK.")
                    result = core.api.openai.call(
                        context=self.context,
                        extra=self.extra,
                        rt_signals=self.rt_signals,
                    )
        except Exception as e:
            if self.signals:
                self.extra["error"] = e
                event = KernelEvent(KernelEvent.RESPONSE_FAILED, {
                    'context': self.context,
                    'extra': self.extra,
                })
                self.signals.response.emit(event)
                self.cleanup()
                return

        # send response to main thread
        if self.signals:
            name = KernelEvent.RESPONSE_OK if result else KernelEvent.RESPONSE_ERROR
            event = KernelEvent(name, {
                'context': self.context,
                'extra': self.extra,
            })
            self.signals.response.emit(event)

        self.cleanup()

    def cleanup(self):
        """Cleanup resources after worker execution."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass

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

    def allowed_single_append(self, context) -> bool:
        """Check if only single append of additional context is allowed for current mode and provider"""
        if context is None or context.model is None:
            return False
        allowed_modes = [MODE_CHAT, MODE_RESEARCH, MODE_COMPUTER]
        if context.model.provider == "openai":
            use_responses_api = self.window.core.api.openai.responses.is_enabled(
                context.model,
                context.mode,
                context.parent_mode,
                context.is_expert_call,
                context.preset
            )
            if use_responses_api and context.mode in allowed_modes:
                return True
        elif context.model.provider == "x_ai":
            if not context.model.id.startswith("grok-3") and context.mode in allowed_modes:
                return True
        return False

    def handle_additional_context(self):
        """Append additional context"""
        ctx = self.context.ctx
        if ctx is None:
            return
        if ctx.meta is None:
            return
        if not self.window.controller.chat.attachment.has_context(ctx.meta):
            return

        # determine if only current attachment content should be appended
        only_current = self.window.core.config.get("ctx.attachment.append_once", False)  # force single append
        auto_detect = self.window.core.config.get("ctx.attachment.auto_append", True) # auto-detect if allowed
        if not only_current and auto_detect:
            if self.allowed_single_append(self.context):
                only_current = True

        # if group additional context exists, append it to current additional context
        if only_current and ctx.meta.group:
            if ctx.meta.group.additional_ctx is None:
                ctx.meta.group.additional_ctx = []
            if ctx.meta.additional_ctx_current is None:
                ctx.meta.additional_ctx_current = []
            ctx.meta.additional_ctx_current.extend(ctx.meta.group.additional_ctx)

        ad_context = self.window.controller.chat.attachment.get_context(
            ctx,
            self.context.history,
            only_current=only_current
        )
        ad_mode = self.window.controller.chat.attachment.get_mode()
        if ad_context:
            self.context.prompt += f"\n\n{ad_context}"  # append to input text
            if (ad_mode == self.window.controller.chat.attachment.MODE_QUERY_CONTEXT
                    or self.mode in [MODE_AGENT_LLAMA, MODE_AGENT_OPENAI]):
                ctx.hidden_input = ad_context  # store for future use, only if query context
                # if full context or summary, then whole extra context will be applied to current input
