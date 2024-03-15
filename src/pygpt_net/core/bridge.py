#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.07 23:00:00                  #
# ================================================== #

import time
from datetime import datetime, timedelta


class Bridge:
    def __init__(self, window=None):
        """
        Provider bridge

        :param window: Window instance
        """
        self.window = window
        self.last_call = None

    def call(self, **kwargs) -> bool:
        """
        Make call to provider

        :param kwargs: keyword arguments
        """
        allowed_model_change = ["vision"]

        self.window.stateChanged.emit(self.window.STATE_BUSY)  # set busy

        # debug
        self.window.core.debug.info("Bridge call...")
        if self.window.core.debug.enabled():
            if self.window.core.config.get("log.ctx"):
                debug = {k: str(v) for k, v in kwargs.items()}
                self.window.core.debug.debug(str(debug))

        # get kwargs
        ctx = kwargs.get("ctx", None)
        prompt = kwargs.get("prompt", None)
        mode = kwargs.get("mode", None)
        model = kwargs.get("model", None)  # model instance

        # get mode from config
        if mode == "agent":
            mode = "chat"  # inline switch to chat mode, because agent is a virtual mode only
            tmp_mode = self.window.core.config.get("agent.mode")
            if tmp_mode is not None and tmp_mode != "_":
                mode = tmp_mode
            if mode == "llama_index":
                kwargs['idx_raw'] = False
                idx = self.window.core.config.get("agent.idx")
                if idx is not None and idx != "_":
                    kwargs['idx'] = idx

        # inline: mode switch
        kwargs['parent_mode'] = mode  # store current (parent) mode
        mode = self.window.controller.mode.switch_inline(mode, ctx, prompt)
        kwargs['mode'] = mode

        # inline: model switch
        if mode in allowed_model_change:
            model = self.window.controller.model.switch_inline(mode, model)
            kwargs['model'] = model

        # debug
        self.window.core.debug.info("Bridge call (after inline)...")
        if self.window.core.debug.enabled():
            if self.window.core.config.get("log.ctx"):
                debug = {k: str(v) for k, v in kwargs.items()}
                self.window.core.debug.debug(str(debug))

        # apply RPM limit
        self.apply_rate_limit()

        # Langchain
        if mode == "langchain":
            return self.window.core.chain.call(**kwargs)

        # Llama-index
        elif mode == "llama_index":
            return self.window.core.idx.chat.call(**kwargs)

        # OpenAI API, chat, completion, vision, image, etc.
        else:
            return self.window.core.gpt.call(**kwargs)

    def quick_call(self, **kwargs) -> str:
        """
        Make quick call to provider and get response content

        :param kwargs: keyword arguments
        :return: response content
        """
        self.window.core.debug.info("Bridge quick call...")
        if self.window.core.debug.enabled():
            if self.window.core.config.get("log.ctx"):
                debug = {k: str(v) for k, v in kwargs.items()}
                self.window.core.debug.debug(str(debug))
        return self.window.core.gpt.quick_call(**kwargs)

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
