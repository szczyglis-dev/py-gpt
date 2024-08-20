#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.20 19:00:00                  #
# ================================================== #

import time
from datetime import datetime, timedelta

from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem


class BridgeContext:
    def __init__(self, **kwargs):
        """
        Bridge context

        :param kwargs: keyword arguments
        """
        self.ctx = kwargs.get("ctx", CtxItem())
        self.history = kwargs.get("history", [])
        self.mode = kwargs.get("mode", None)
        self.parent_mode = kwargs.get("parent_mode", None)  # real mode (global)
        self.model = kwargs.get("model", None)  # model instance, not model name
        self.temperature = kwargs.get("temperature", 1.0)
        self.prompt = kwargs.get("prompt", "")
        self.system_prompt = kwargs.get("system_prompt", "")
        self.system_prompt_raw = kwargs.get("system_prompt_raw", "")  # without plugins addons
        self.stream = kwargs.get("stream", False)
        self.assistant_id = kwargs.get("assistant_id", "")
        self.thread_id = kwargs.get("thread_id", "")
        self.external_functions = kwargs.get("external_functions", [])
        self.tools_outputs = kwargs.get("tools_outputs", [])
        self.max_tokens = kwargs.get("max_tokens", 150)
        self.idx = kwargs.get("idx", None)
        self.idx_raw = kwargs.get("idx_raw", False)
        self.attachments = kwargs.get("attachments", [])
        self.file_ids = kwargs.get("file_ids", [])

        # check types
        if self.ctx is not None and not isinstance(self.ctx, CtxItem):
            raise ValueError("Invalid context instance")
        if self.model is not None and not isinstance(self.model, ModelItem):
            raise ValueError("Invalid model instance")

    def to_dict(self) -> dict:
        """
        Return as dictionary

        :return: dictionary
        """
        return {
            "ctx": self.ctx,  # "ctx": self.ctx.dump() ??
            "history": self.history,
            "mode": self.mode,
            "parent_mode": self.parent_mode,
            "model": self.model,
            "temperature": self.temperature,
            "prompt": self.prompt,
            "system_prompt": self.system_prompt,
            "system_prompt_raw": self.system_prompt_raw,
            "stream": self.stream,
            "assistant_id": self.assistant_id,
            "thread_id": self.thread_id,
            "external_functions": self.external_functions,
            "tools_outputs": self.tools_outputs,
            "max_tokens": self.max_tokens,
            "idx": self.idx,
            "idx_raw": self.idx_raw,
            "attachments": self.attachments,
            "file_ids": self.file_ids,
        }


class Bridge:
    def __init__(self, window=None):
        """
        Provider bridge

        :param window: Window instance
        """
        self.window = window
        self.last_call = None  # last API call time, for throttling

    def call(self, context: BridgeContext, extra: dict = None) -> bool:
        """
        Make call to provider

        :param context: Bridge context
        :param extra: extra data  # TODO: object also
        """
        allowed_model_change = ["vision"]

        self.window.stateChanged.emit(self.window.STATE_BUSY)  # set busy

        # debug
        self.window.core.debug.info("Bridge call...")
        if self.window.core.debug.enabled():
            if self.window.core.config.get("log.ctx"):
                debug = {k: str(v) for k, v in context.to_dict().items()}
                self.window.core.debug.debug(str(debug))

        # get data
        ctx = context.ctx
        prompt = context.prompt
        mode = context.mode
        model = context.model  # model instance

        # get agent internal sub-mode
        if mode == "agent":
            mode = "chat"  # inline switch to sub-mode, because agent is a virtual mode only
            sub_mode = self.window.core.agents.get_mode()
            if sub_mode is not None and sub_mode != "_":
                mode = sub_mode
            if mode == "llama_index":
                context.idx_raw = False
                idx = self.window.core.agents.get_mode()
                if idx is not None and idx != "_":
                    context.idx = idx

        # inline: internal mode switch if needed
        context.parent_mode = mode  # store REAL mode
        mode = self.window.controller.mode.switch_inline(mode, ctx, prompt)
        context.mode = mode

        # inline: model switch
        if mode in allowed_model_change:
            model = self.window.controller.model.switch_inline(mode, model)
            context.model = model

        # debug
        self.window.core.debug.info("Bridge call (after inline)...")
        if self.window.core.debug.enabled():
            if self.window.core.config.get("log.ctx"):
                debug = {k: str(v) for k, v in context.to_dict().items()}
                self.window.core.debug.debug(str(debug))

        self.apply_rate_limit()  # apply RPM limit

        # Langchain
        if mode == "langchain":
            return self.window.core.chain.call(
                context=context,
                extra=extra,
            )

        # Llama-index
        elif mode == "llama_index":
            return self.window.core.idx.chat.call(
                context=context,
                extra=extra,
            )

        # OpenAI API: chat, completion, vision, image, assistants, etc.
        else:
            return self.window.core.gpt.call(
                context=context,
                extra=extra,
            )

    def quick_call(self, context: BridgeContext, extra: dict = None) -> str:
        """
        Make quick call to provider and get response content

        :param context: Bridge context
        :param extra: extra data
        :return: response content
        """
        self.window.core.debug.info("Bridge quick call...")
        # check if model is supported by chat API, if not try to use llama-index call
        if context.model is not None:
            if "chat" not in context.model.mode:
                if "llama_index" in context.model.mode:
                    context.stream = False
                    ctx = context.ctx  # output will be filled in query
                    try:
                        res = self.window.core.idx.chat.query(
                            context=context,
                            extra=extra,
                        )
                        if res:
                            return ctx.output
                    except Exception as e:
                        self.window.core.debug.error("Error in Llama-index quick call: " + str(e))
                        self.window.core.debug.error(e)
                    return ""

        if self.window.core.debug.enabled():
            if self.window.core.config.get("log.ctx"):
                debug = {k: str(v) for k, v in context.to_dict().items()}
                self.window.core.debug.debug(str(debug))
        return self.window.core.gpt.quick_call(
            context=context,
            extra=extra,
        )

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
