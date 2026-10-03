#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.22 11:20:00                  #
# ================================================== #

from PySide6.QtCore import QObject, Signal, QRunnable, Slot

from pygpt_net.core.types import (
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
    MODE_AGENT_V2,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_ASSISTANT,
    MODE_VISION,
    MODE_LOOP_NEXT,
    MODE_CHAT,
    MODE_RESEARCH,
    MODE_COMPUTER,
    MODE_COMPLETION,
)
from pygpt_net.core.events import KernelEvent, Event
from pygpt_net.core.qt import safe_emit


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


    def _emit(self, name: str, *args) -> bool:
        """Safely emit a bridge Qt signal during late worker teardown."""
        return safe_emit(self.signals, name, *args)

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

            # Apply the global prompt-injection annotation after all late system
            # prompt hooks so external-context warnings remain the final policy.
            self.context.system_prompt = core.security.append_prompt_injection_guard(
                self.context.system_prompt, ensure_last=True, mode=self.mode
            )

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

            # Agents v2 (new isolated orchestration runtime)
            elif self.mode == MODE_AGENT_V2:
                result = core.agents_v2.runner.call(
                    context=self.context,
                    extra=self.extra,
                    signals=self.signals,
                )
                if result:
                    self.cleanup()
                    return
                self.extra["error"] = str(core.agents_v2.runner.get_error())

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

            # Completion normally uses the LlamaIndex completion provider so all
            # configured backends share one path. Keep one narrow exception for
            # OpenAI's legacy instruct model: without active chat-style RAG it
            # must use the native OpenAI SDK Completions endpoint. A selected RAG
            # index is intentionally ignored when Completion "As chat" is off.
            elif self.mode == MODE_COMPLETION \
                    and self.context.model is not None:
                model = self.context.model
                completion_as_chat = bool(
                    core.config.get("completion.as_chat", True)
                )
                native_openai_completion = (
                    model.provider == "openai"
                    and model.id == "gpt-3.5-turbo-instruct"
                    and (
                        not completion_as_chat
                        or not core.idx.is_valid(self.context.idx)
                    )
                )
                if native_openai_completion:
                    core.debug.info(
                        "[bridge] Using native OpenAI SDK completion provider."
                    )
                    result = core.bridge.call_api(
                        context=self.context,
                        extra=self.extra,
                        rt_signals=self.rt_signals,
                        signals=self.signals,
                    )
                else:
                    core.debug.info("[bridge] Using LlamaIndex completion provider.")
                    result = core.idx.completion.call(
                        context=self.context,
                        extra=self.extra,
                    )

            # API/provider dispatch with the same LlamaIndex fallback as quick calls.
            else:
                result = core.bridge.call_api(
                    context=self.context,
                    extra=self.extra,
                    rt_signals=self.rt_signals,
                    signals=self.signals,
                )
        except Exception as e:
            if self.extra is not None:
                self.extra["error"] = e
            event = KernelEvent(KernelEvent.RESPONSE_FAILED, {
                'context': self.context,
                'extra': self.extra,
            })
            self._emit("response", event)
            self.cleanup()
            return

        # send response to main thread
        name = KernelEvent.RESPONSE_OK if result else KernelEvent.RESPONSE_ERROR
        event = KernelEvent(name, {
            'context': self.context,
            'extra': self.extra,
        })
        self._emit("response", event)

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

    def handle_additional_context(self):
        """Append additional context"""
        ctx = self.context.ctx
        if ctx is None:
            return
        if ctx.meta is None:
            return
        if getattr(ctx, "internal", False) or getattr(ctx, "turn_continuation", False):
            return
        if not self.window.controller.chat.attachment.has_context(ctx.meta):
            return

        attachment = self.window.controller.chat.attachment
        # Attachments belong to the uploading turn. History providers replay
        # hidden_input; Responses providers retain that same user message.
        ad_context = attachment.get_context(ctx, self.context.history, only_current=True)
        attachment.bind_current_to_ctx(ctx)
        if ad_context:
            hidden = ctx.hidden_input or ""
            if ad_context not in hidden:
                ctx.hidden_input = "\n\n".join(filter(None, [hidden, ad_context]))
            if ad_context not in self.context.prompt:
                self.context.prompt = f"{self.context.prompt}\n\n{ad_context}"
