#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.27 06:00:00                  #
# ================================================== #

from __future__ import annotations

from typing import Any, Dict, List, Optional
from agents import TResponseInputItem
from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem

from .logging import Logger, NullLogger
from .flow_types import DebugConfig, FlowResult, FlowOptions
from .flow import FlowRun
from .utils import OptionGetter


class FlowOrchestrator:
    """Execute a node-editor flow with explicit preparation/execution/routing phases."""

    def __init__(self, window, logger: Optional[Logger] = None) -> None:
        self.window = window
        self.logger = logger or NullLogger()

    # ========================================
    # Workflows
    # ========================================

    async def run_flow(
        self,
        schema: List[Dict[str, Any]],
        messages: List[TResponseInputItem],
        ctx: CtxItem,
        bridge: ConnectionContext,
        agent_kwargs: Dict[str, Any],
        preset: Optional[PresetItem],
        model: ModelItem,
        stream: bool,
        use_partial_ctx: bool,
        base_prompt: Optional[str],
        system_prompt_extra: Optional[str],
        allow_local_tools_default: bool,
        allow_remote_tools_default: bool,
        function_tools: List[dict],
        trace_id: Optional[str],
        max_iterations: int = 20,
        router_stream_mode: str = "off",  # "off" | "delayed" | "realtime"
        option_get: Optional[OptionGetter] = None,
    ) -> FlowResult:
        options = FlowOptions(
            agent_kwargs=agent_kwargs, preset=preset, model=model, stream=stream,
            use_partial_ctx=use_partial_ctx, base_prompt=base_prompt,
            system_prompt_extra=system_prompt_extra,
            allow_local_tools=allow_local_tools_default,
            allow_remote_tools=allow_remote_tools_default,
            function_tools=function_tools, max_iterations=max_iterations,
            router_stream_mode=router_stream_mode,
            option_get=option_get or (lambda s, k, d=None: d),
        )
        return await FlowRun(self.window, self.logger, schema, messages, ctx, bridge, options).run()
