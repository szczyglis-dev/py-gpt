#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.28 16:00:00                  #
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
        self.idx_mode = kwargs.get("idx_mode", "chat")
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
        data = {
            "ctx": self.ctx,
            "history": len(self.history),
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
            "idx_mode": self.idx_mode,
            "attachments": self.attachments,
            "file_ids": self.file_ids,
        }
        if self.ctx is not None:
            data["ctx"] = self.ctx.to_dict()
        if self.model is not None:
            data["model"] = self.model.to_dict()

        # sort by keys
        data = dict(sorted(data.items(), key=lambda item: item[0]))
        return data


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

    def call(self, context: BridgeContext, extra: dict = None) -> bool:
        """
        Make call to provider

        :param context: Bridge context
        :param extra: extra data  # TODO: object also
        """
        allowed_model_change = ["vision"]
        is_virtual = False

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
        model = context.model  # model instance, not ID
        base_mode = mode
        context.parent_mode = base_mode  # store base mode

        # get agent or expert internal sub-mode
        if base_mode == "agent" or base_mode == "expert":
            is_virtual = True
            sub_mode = None  # inline switch to sub-mode, because agent is a virtual mode only
            if base_mode == "agent":
                sub_mode = self.window.core.agents.get_mode()
            elif base_mode == "expert":
                sub_mode = self.window.core.experts.get_mode()
            if sub_mode is not None and sub_mode != "_":
                mode = sub_mode

        # check if model is supported by selected mode - if not, then try to use supported mode
        if model is not None:
            if not model.is_supported(mode):  # check selected mode
                mode = self.window.core.models.get_supported_mode(model, mode)  # switch

        if mode == "llama_index" and base_mode != "llama_index":
            context.idx_mode = "chat"

        if is_virtual:
            if mode == "llama_index":  # after switch
                idx = self.window.core.agents.get_idx()  # get index, idx is common for agent and expert
                if idx is not None and idx != "_":
                    context.idx = idx
                    self.window.core.debug.info("AGENT/EXPERT: Using index: " + idx)
                else:
                    context.idx = None  # don't use index

        # inline: internal mode switch if needed
        mode = self.window.controller.mode.switch_inline(mode, ctx, prompt)
        context.mode = mode

        # inline: model switch
        if mode in allowed_model_change:
            context.model = self.window.controller.model.switch_inline(mode, model)

        # debug
        self.window.core.debug.info("Bridge call (after inline)...")
        if self.window.core.debug.enabled():
            if self.window.core.config.get("log.ctx"):
                debug = {k: str(v) for k, v in context.to_dict().items()}
                self.window.core.debug.debug(str(debug))

        self.apply_rate_limit()  # apply RPM limit
        self.last_context = context  # store last context for call (debug)

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
        if self.window.core.debug.enabled():
            if self.window.core.config.get("log.ctx"):
                debug = {k: str(v) for k, v in context.to_dict().items()}
                self.window.core.debug.debug(str(debug))

        self.last_context_quick = context  # store last context for quick call (debug)

        if context.model is not None:
            # check if model is supported by chat API, if not then try to use llama-index or langchain call
            if not context.model.is_supported("chat"):
                # tmp switch to: llama-index
                if context.model.is_supported("llama_index"):
                    context.stream = False  # force disable stream
                    ctx = context.ctx  # output will be filled in query
                    ctx.input = context.prompt
                    try:
                        res = self.window.core.idx.chat.chat(
                            context=context,
                            extra=extra,
                        )
                        if res:
                            return ctx.output  # response text is in ctx.output
                    except Exception as e:
                        self.window.core.debug.error("Error in Llama-index quick call: " + str(e))
                        self.window.core.debug.error(e)
                    return ""
                # tmp switch to: langchain
                elif context.model.is_supported("langchain"):
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

        # default: OpenAI API call
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
