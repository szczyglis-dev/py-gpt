#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.21 10:20:00
# ================================================== #

import copy
import time
import weakref
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from pygpt_net.core.text.mentions import to_model_text as mentions_to_model_text
from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_V2,
    MODE_ASSISTANT,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_COMPUTER,
    MODE_EXPERT,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_RESEARCH,
)

from .context import BridgeContext
from .worker import BridgeWorker

class Bridge:
    def __init__(self, window=None):
        """
        Provider bridge

        :param window: Window instance
        """
        self.window = window
        self.last_call = None  # last API call time, for throttling
        self.last_context = None  # last context
        self.last_context_quick = None  # last context for quick call
        self.sync_modes = (
            MODE_ASSISTANT,
            MODE_EXPERT,
        )
        self.worker = None

    def request(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Make request to provider

        :param context: Bridge context
        :param extra: extra data
        """
        if self.window.controller.kernel.stopped():
            return False

        allowed_model_change = [MODE_CHAT]
        force_sync = False

        self.window.stateChanged.emit(self.window.STATE_BUSY)  # set busy

        # debug
        self.window.core.debug.info("[bridge] Request...")
        if self.window.core.debug.enabled():
            if self.window.core.config.get("log.ctx"):
                debug = {k: str(v) for k, v in context.to_dict().items()}
                self.window.core.debug.debug(str(debug))

        # get data
        ctx = context.ctx
        prompt = context.prompt
        mode = context.mode
        model = context.model  # model instance, not ID
        base_mode = mode
        context.parent_mode = base_mode  # store base mode

        # Autonomous and Experts are virtual Chat-backed modes. The global RAG
        # selector is the only source of truth; there is no mode-specific index.
        if base_mode in (MODE_AGENT, MODE_EXPERT):
            mode = MODE_CHAT
            if self.window.core.idx.is_valid(context.idx):
                mode = MODE_LLAMA_INDEX
                self.window.core.debug.info("[bridge] Using RAG index: " + str(context.idx))

        # Shared RAG gateway: the visible UI mode stays unchanged, while the
        # provider runtime is switched to the Chat with Files (LlamaIndex) path.
        # Computer Use is supported here as well: the LlamaIndex chat layer binds
        # the same provider-native ComputerRuntime adapter used by agent flows.
        rag_gateway = base_mode in (
            MODE_CHAT,
            MODE_RESEARCH,
            MODE_COMPUTER,
        )
        valid_rag = self.window.core.idx.is_valid(context.idx)
        if rag_gateway and valid_rag:
            mode = MODE_LLAMA_INDEX
            self.window.core.debug.info("[bridge] RAG gateway -> LlamaIndex chat: " + str(context.idx))

        # Completion has its own LlamaIndex runtime. Keep MODE_COMPLETION so the
        # worker enters core.idx.completion instead of the chat-with-index path;
        # the completion runtime performs RAG retrieval before complete/stream_complete.
        rag_completion = base_mode == MODE_COMPLETION and valid_rag
        if rag_completion:
            mode = MODE_COMPLETION
            context.idx_mode = MODE_COMPLETION
            self.window.core.debug.info("[bridge] RAG gateway -> LlamaIndex completion: " + str(context.idx))

        # A user-selected RAG index is an explicit routing decision. Do not let
        # model mode metadata silently switch an active RAG request back to a
        # native SDK mode (notably Research-only models), nor convert Completion
        # with RAG into another provider mode.
        force_rag_runtime = valid_rag and (
            mode == MODE_LLAMA_INDEX or rag_completion
        )

        # check if model is supported by selected mode - if not, then try to use supported mode
        if model is not None:
            # Agents v2 is a virtual orchestration mode backed by the app's LlamaIndex
            # LLM adapter, so model capability is checked against LlamaIndex separately.
            if base_mode == MODE_AGENT_V2:
                mode = MODE_AGENT_V2
            elif not force_rag_runtime and not model.is_supported(mode):  # check selected mode
                mode = self.window.core.models.get_supported_mode(model, mode)  # switch
                if base_mode == MODE_CHAT and mode == MODE_LLAMA_INDEX:
                    context.idx = None # capability fallback only; no RAG was explicitly selected
        self.window.core.debug.info("[bridge] Using mode: " + str(mode))

        if mode == MODE_LLAMA_INDEX and base_mode != MODE_LLAMA_INDEX:
            context.idx_mode = MODE_CHAT  # default in sub-mode

        # inline: internal mode switch if needed
        mode = self.window.controller.mode.switch_inline(mode, ctx, prompt)
        context.mode = mode

        # inline: model switch
        if mode in allowed_model_change:
            context.model = self.window.controller.model.switch_inline(mode, model)

        # Resolve semantic @mentions only after the final inline mode/model has
        # been selected. Image attachment mentions are mapped to Attached Image #N only
        # when the actual request model accepts image input; otherwise the
        # original attachment filename remains provider-facing text.
        if context.prompt_mentions:
            if context.model is not None and context.model.is_image_input():
                context.prompt = mentions_to_model_text(
                    context.prompt_mentions,
                    attachments=context.attachments,
                )
            else:
                context.prompt = mentions_to_model_text(context.prompt_mentions)

        # debug
        self.window.core.debug.info("[bridge] After inline...")
        if self.window.core.debug.enabled():
            if self.window.core.config.get("log.ctx"):
                debug = {k: str(v) for k, v in context.to_dict().items()}
                self.window.core.debug.debug(str(debug))

        self.apply_rate_limit()  # apply RPM limit

        if extra is None:
            extra = {}

        # async worker
        worker = self.get_worker()
        worker.context = context
        worker.extra = extra
        worker.mode = mode

        # some modes must be called synchronously
        if mode in self.sync_modes or force_sync:
            self.window.core.debug.info("[bridge] Starting worker (sync)...")
            worker.run()
            return True

        # async call
        self.window.core.debug.info("[bridge] Starting worker (async)...")
        self.window.threadpool.start(worker)
        self.worker = worker
        return True

    def request_next(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Make next call to provider (loop next step)

        :param context: Bridge context
        :param extra: extra data
        """
        if self.window.controller.kernel.stopped():
            return False

        if extra is None:
            extra = {}

        # async worker
        worker = self.get_worker()
        worker.context = context
        worker.extra = extra
        worker.mode = "loop_next"

        # async call
        self.window.threadpool.start(worker)
        self.worker = worker
        return True

    def call(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Make quick call to provider and get response content.

        Quick bridge calls intentionally do not inherit the global runtime
        reasoning-effort preference. They are used for lightweight auxiliary
        requests where applying the user's chat reasoning budget would add
        unnecessary latency/token usage. The original model object is never
        mutated.

        :param context: Bridge context
        :param extra: extra data
        :return: response content
        """
        if self.window.controller.kernel.stopped() and not context.force:
            return ""

        context.system_prompt = self.window.core.security.append_prompt_injection_guard(
            context.system_prompt, ensure_last=True
        )

        self.window.core.debug.info("[bridge] Call...")
        if self.window.core.debug.enabled():
            if self.window.core.config.get("log.ctx"):
                debug = {k: str(v) for k, v in context.to_dict().items()}
                self.window.core.debug.debug(str(debug))

        # Providers resolve the effective effort from ModelItem.reasoning_effort.
        # Use a shallow request-local copy with that capability disabled so the
        # global model.reasoning_effort value is not injected into quick calls.
        original_model = context.model
        if original_model is not None and bool(getattr(original_model, "reasoning_effort", False)):
            context.model = copy.copy(original_model)
            context.model.reasoning_effort = False

        try:
            if context.model is not None:
                # check if model is supported by OpenAI API, if not then try to use llama-index or langchain call
                if not context.model.is_supported(MODE_CHAT):

                    # tmp switch to: llama-index
                    if context.model.is_supported(MODE_LLAMA_INDEX):
                        context.stream = False  # force disable stream
                        ctx = context.ctx  # output will be filled in query
                        ctx.input = context.prompt
                        try:
                            res = self.window.core.idx.chat.chat(
                                context=context,
                                extra=extra,
                                disable_cmd=True,
                            )
                            if res:
                                return ctx.output  # response text is in ctx.output
                        except Exception as e:
                            self.window.core.debug.error("Error in Llama-index quick call: " + str(e))
                            self.window.core.debug.error(e)
                        return ""

                    # tmp switch to: langchain
                    """
                    elif context.model.is_supported(MODE_LANGCHAIN):
                        context.stream = False
                        ctx = context.ctx
                        ctx.input = context.prompt
                        try:
                            res = self.window.core.chain.chat(
                                context=context,
                                extra=extra,
                            )
                            if res:
                                return ctx.output  # response text is in ctx.output
                        except Exception as e:
                            self.window.core.debug.error("Error in Langchain quick call: " + str(e))
                            self.window.core.debug.error(e)
                        return ""
                    """

            # if model is research model, then switch to research / Perplexity endpoint
            if context.mode is None or context.mode == MODE_CHAT:
                if context.model is not None:
                    if not context.model.is_supported(MODE_CHAT):
                        if context.model.is_supported(MODE_RESEARCH):
                            context.mode = MODE_RESEARCH

            # default: OpenAI API call
            return self.window.core.api.openai.quick_call(
                context=context,
                extra=extra,
            )
        finally:
            context.model = original_model

    def get_worker(self) -> BridgeWorker:
        """
        Prepare async worker

        :return: BridgeWorker
        """
        worker = BridgeWorker()
        worker.window = self.window
        worker.signals.response.connect(self.window.controller.kernel.listener)
        worker.rt_signals = self.window.controller.realtime.signals  # Realtime signals
        return worker

    def apply_rate_limit(self):
        """Apply API calls RPM limit"""
        max_per_minute = 60
        if self.window.core.config.has("max_requests_limit"):
            max_per_minute = int(self.window.core.config.get("max_requests_limit")) # per minute
        if max_per_minute <= 0:
            return
        interval = timedelta(minutes=1) / max_per_minute
        now = datetime.now()
        if self.last_call is not None:
            time_since_last_call = now - self.last_call
            if time_since_last_call < interval:
                sleep_time = (interval - time_since_last_call).total_seconds()
                self.window.core.debug.debug("RPM limit: sleep for {} seconds".format(sleep_time))
                time.sleep(sleep_time)
        self.last_call = now
