#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.21 21:30:00
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


# Temporary compatibility switch: Research models currently do not handle
# PyGPT app-level tools reliably. Keep the policy centralized in the bridge so
# it can be removed by flipping a single constant once provider support is ready.
DISABLE_RESEARCH_TOOLS = True


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

    def resolve_api_provider(self, model) -> Optional[str]:
        """
        Resolve the direct API backend for a model.

        Native provider SDKs take precedence when explicitly enabled. If a
        native SDK is disabled, providers that expose an OpenAI-compatible
        endpoint use the OpenAI transport. ``None`` means there is no direct
        API transport for the model and the caller may use a higher-level
        fallback such as LlamaIndex.

        :param model: ModelItem instance or None
        :return: API attribute name: openai/google/anthropic/xai, or None
        """
        if model is None:
            return "openai"

        provider = getattr(model, "provider", None)
        native = {
            "google": ("api_native_google", "google"),
            "anthropic": ("api_native_anthropic", "anthropic"),
            "x_ai": ("api_native_xai", "xai"),
        }
        if provider in native:
            config_key, api_provider = native[provider]
            if self.window.core.config.get(config_key, False):
                return api_provider

        if model.is_openai_supported():
            return "openai"

        return None

    def call_api(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None,
            rt_signals=None,
            signals=None,
            quick: bool = False
    ):
        """
        Call the resolved API backend, with LlamaIndex as the final fallback.

        This is the common provider dispatch used by both normal bridge workers
        and synchronous quick calls. Native/OpenAI-compatible routing and the
        final LlamaIndex fallback therefore cannot drift between the two paths.

        :param context: Bridge context
        :param extra: extra data
        :param rt_signals: realtime signals for normal provider calls
        :param signals: bridge worker signals used by the LlamaIndex fallback
        :param quick: use provider quick_call instead of call
        :return: provider result
        """
        api_provider = self.resolve_api_provider(context.model)
        if api_provider is None:
            model_id = getattr(context.model, "id", None) or "unknown"
            self.window.core.debug.info(
                "[bridge] No direct API provider for model {}. "
                "Falling back to LlamaIndex.".format(model_id)
            )
            if quick:
                return self.call_llama_index_quick(context, extra)
            return self.window.core.idx.chat.call(
                context=context,
                extra=extra,
                signals=signals,
            )

        api = getattr(self.window.core.api, api_provider)
        label = {
            "openai": "OpenAI",
            "google": "Google",
            "anthropic": "Anthropic",
            "xai": "xAI",
        }.get(api_provider, api_provider)
        suffix = " (quick)" if quick else ""
        self.window.core.debug.info(
            "[bridge] Using {} SDK{}.".format(label, suffix)
        )

        if quick:
            return api.quick_call(
                context=context,
                extra=extra,
            )

        return api.call(
            context=context,
            extra=extra,
            rt_signals=rt_signals,
        )

    def apply_mode_tool_policy(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
    ):
        """Apply temporary mode-specific tool compatibility rules."""
        if not DISABLE_RESEARCH_TOOLS:
            return

        # parent_mode preserves the visible mode when Research is routed through
        # the shared RAG/LlamaIndex runtime. Checking both also covers direct and
        # quick Research calls.
        if context.mode != MODE_RESEARCH and context.parent_mode != MODE_RESEARCH:
            return

        if context.external_functions:
            self.window.core.debug.info(
                "[bridge] Research mode: temporarily disabling app tools."
            )
        context.external_functions = []

        # LlamaIndex/RAG prepares its tools from the global command registry
        # rather than context.external_functions, so carry an explicit runtime
        # marker for that path as well.
        if extra is not None:
            extra["disable_tools"] = True

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

        # Chat with Files is a legacy UI alias from 2.8.28. Normalize it to
        # Chat before runtime routing; the shared RAG selection then decides
        # whether Chat uses the native SDK path or LlamaIndex. Research remains
        # a first-class mode because it has research-specific runtime behavior.
        if mode == MODE_LLAMA_INDEX:
            self.window.core.debug.info("[bridge] Legacy Chat with Files alias -> Chat")
            mode = MODE_CHAT
            context.mode = MODE_CHAT

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
        # worker enters core.idx.completion instead of the chat-with-index path.
        # RAG participates only while Completion is using chat-style assembly.
        completion_as_chat = bool(
            self.window.core.config.get("completion.as_chat", True)
        )
        rag_completion = (
            base_mode == MODE_COMPLETION
            and completion_as_chat
            and valid_rag
        )
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

        self.apply_mode_tool_policy(context, extra)

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
            context.system_prompt, ensure_last=True, mode=context.mode
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
            self.apply_mode_tool_policy(context, extra)

            model = context.model
            if model is not None:
                # Research-only models keep the legacy quick-call mode switch.
                # Transport selection is resolved independently by call_api().
                if context.mode is None or context.mode == MODE_CHAT:
                    if not model.is_supported(MODE_CHAT):
                        if model.is_supported(MODE_RESEARCH):
                            context.mode = MODE_RESEARCH

            return self.call_api(
                context=context,
                extra=extra,
                quick=True,
            )
        finally:
            context.model = original_model

    def call_llama_index_quick(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Make a synchronous LlamaIndex fallback call and return response text.

        :param context: Bridge context
        :param extra: extra data
        :return: response content
        """
        context.stream = False
        ctx = context.ctx
        ctx.input = context.prompt
        try:
            res = self.window.core.idx.chat.chat(
                context=context,
                extra=extra,
                disable_cmd=True,
            )
            if res:
                return ctx.output
        except Exception as e:
            self.window.core.debug.error(
                "Error in Llama-index quick call: " + str(e)
            )
            self.window.core.debug.error(e)
        return ""

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
