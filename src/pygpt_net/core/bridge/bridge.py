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
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_ASSISTANT,
    MODE_CHAT,
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
        self.sync_modes = [
            MODE_ASSISTANT,
            MODE_EXPERT,
        ]
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

        allowed_model_change = [MODE_VISION]
        is_virtual = False

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

        # get agent or expert internal sub-mode
        if base_mode in [MODE_AGENT, MODE_EXPERT]:
            is_virtual = True
            sub_mode = None  # inline switch to sub-mode, because agent is a virtual mode only
            if base_mode == MODE_AGENT:
                sub_mode = self.window.core.agents.legacy.get_mode()
            elif base_mode == MODE_EXPERT:
                sub_mode = self.window.core.experts.get_mode()
            if sub_mode is not None and sub_mode != "_":
                mode = sub_mode

        # check if model is supported by selected mode - if not, then try to use supported mode
        if model is not None:
            if not model.is_supported(mode):  # check selected mode
                mode = self.window.core.models.get_supported_mode(model, mode)  # switch
                if base_mode == MODE_CHAT and mode == MODE_LLAMA_INDEX:
                    context.idx = None # disable index if in Chat mode and switch to Llama Index
                    if not self.window.core.idx.chat.is_stream_allowed():
                        context.stream = False  # disable stream in cmd mode

        self.window.core.debug.info("[bridge] Using mode: " + str(mode))

        if mode == MODE_LLAMA_INDEX and base_mode != MODE_LLAMA_INDEX:
            context.idx_mode = MODE_CHAT  # default in sub-mode

        if is_virtual:
            if mode == MODE_LLAMA_INDEX:  # after switch
                idx = self.window.core.agents.legacy.get_idx()  # get index, idx is common for agent and expert
                if idx is not None and idx != "_":
                    context.idx = idx
                    self.window.core.debug.info("[agent/expert] Using index: " + idx)
                else:
                    context.idx = None  # don't use index

        # inline: internal mode switch if needed
        mode = self.window.controller.mode.switch_inline(mode, ctx, prompt)
        context.mode = mode

        # inline: model switch
        if mode in allowed_model_change:
            context.model = self.window.controller.model.switch_inline(mode, model)

        # debug
        self.window.core.debug.info("[bridge] After inline...")
        if self.window.core.debug.enabled():
            if self.window.core.config.get("log.ctx"):
                debug = {k: str(v) for k, v in context.to_dict().items()}
                self.window.core.debug.debug(str(debug))

        self.apply_rate_limit()  # apply RPM limit
        self.last_context = context  # store last context for call (debug)

        if extra is None:
            extra = {}

        # async worker
        self.worker = self.get_worker()
        self.worker.context = context
        self.worker.extra = extra
        self.worker.mode = mode

        # some modes must be called synchronously
        if mode in self.sync_modes:
            self.window.core.debug.info("[bridge] Starting worker (sync)...")
            self.worker.run()
            return True

        # async call
        self.window.core.debug.info("[bridge] Starting worker (async)...")
        self.window.threadpool.start(self.worker)
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
        self.worker = self.get_worker()
        self.worker.context = context
        self.worker.extra = extra
        self.worker.mode = "loop_next"

        # async call
        self.window.threadpool.start(self.worker)
        return True

    def call(
            self,
            context: BridgeContext,
            extra: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Make quick call to provider and get response content

        :param context: Bridge context
        :param extra: extra data
        :return: response content
        """
        if self.window.controller.kernel.stopped():
            return ""

        self.window.core.debug.info("[bridge] Call...")
        if self.window.core.debug.enabled():
            if self.window.core.config.get("log.ctx"):
                debug = {k: str(v) for k, v in context.to_dict().items()}
                self.window.core.debug.debug(str(debug))

        # --- DEBUG ONLY ---
        self.last_context_quick = context  # store last context for quick call (debug)

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
        return self.window.core.gpt.quick_call(
            context=context,
            extra=extra,
        )

    def get_worker(self) -> BridgeWorker:
        """
        Prepare async worker

        :return: BridgeWorker
        """
        worker = BridgeWorker()
        worker.window = self.window
        worker.signals.response.connect(self.window.controller.kernel.listener)
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
