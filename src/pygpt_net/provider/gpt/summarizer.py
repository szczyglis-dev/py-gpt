#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.08 05:00:00                  #
# ================================================== #

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem


class Summarizer:
    def __init__(self, window=None):
        """
        Summarizer

        :param window: Window instance
        """
        self.window = window

    def summary_ctx(self, ctx: CtxItem) -> str:
        """
        Summarize conversation begin

        :param ctx: context item (CtxItem)
        :return: response text (generated summary)
        """
        max_chars = 700
        model = self.window.core.models.from_defaults()
        system_prompt = self.window.core.prompt.get('ctx.auto_summary.system')
        truncated_input = str(ctx.input)[:max_chars] + '...' if len(str(ctx.input)) > max_chars else str(ctx.input)
        truncated_output = str(ctx.output)[:max_chars] + '...' if len(str(ctx.output)) > max_chars else str(ctx.output)
        if truncated_output and truncated_output != "None":
            text = (self.window.core.prompt.get('ctx.auto_summary.user').
                    replace("{input}", truncated_input).
                    replace("{output}", truncated_output))
        else:
            text = (self.window.core.prompt.get('ctx.auto_summary.user').
                    replace("{input}", truncated_input).
                    replace("{output}", "..."))

        # custom model for auto summary
        if self.window.core.config.get('ctx.auto_summary.model') is not None \
                and self.window.core.config.get('ctx.auto_summary.model') != "":
            tmp_model = self.window.core.config.get('ctx.auto_summary.model')
            if self.window.core.models.has(tmp_model):
                model = self.window.core.models.get(tmp_model)

        # quick call OpenAI API
        bridge_context = BridgeContext(
            ctx=ctx,
            prompt=text,
            system_prompt=system_prompt,
            model=model,
            max_tokens=500,
            temperature=0.0,
            force=True,  # even if kernel stopped!
        )
        event = KernelEvent(KernelEvent.FORCE_CALL, {
            'context': bridge_context,
            'extra': {"disable_tools": True},
            'response': None,
        })
        self.window.dispatch(event)
        response = event.data.get('response')
        if response is not None:
            return response
