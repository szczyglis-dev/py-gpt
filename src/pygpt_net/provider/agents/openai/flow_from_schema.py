#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.24 23:00:00                  #
# ================================================== #

from __future__ import annotations
from typing import Any, Dict, Tuple, Optional, List

from pygpt_net.core.types import AGENT_TYPE_OPENAI, AGENT_MODE_OPENAI
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem

from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.core.bridge import BridgeContext

from agents import TResponseInputItem

from ..base import BaseAgent

from pygpt_net.core.agents.custom.logging import NullLogger, StdLogger
from pygpt_net.core.agents.custom.runner import FlowOrchestrator
from pygpt_net.core.agents.custom.utils import make_option_getter


class Agent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super(Agent, self).__init__(*args, **kwargs)
        self.id = "openai_custom"
        self.type = AGENT_TYPE_OPENAI
        self.mode = AGENT_MODE_OPENAI
        self.name = "Custom"

    async def run(
        self,
        window: Any = None,
        agent_kwargs: Dict[str, Any] = None,
        previous_response_id: str = None,
        messages: List[TResponseInputItem] = None,
        ctx: CtxItem = None,
        stream: bool = False,
        bridge: ConnectionContext = None,
        use_partial_ctx: Optional[bool] = False,
        schema: Optional[list] = None,
    ) -> Tuple[CtxItem, str, str]:
        agent_kwargs = agent_kwargs or {}
        messages = messages or []

        context: BridgeContext = agent_kwargs.get("context", BridgeContext())
        preset: Optional[PresetItem] = context.preset
        model: ModelItem = agent_kwargs.get("model", ModelItem())
        function_tools: list = agent_kwargs.get("function_tools", [])

        base_prompt = self.get_option(preset, "base", "prompt")
        allow_local_tools_default = bool(self.get_option(preset, "base", "allow_local_tools"))
        allow_remote_tools_default = bool(self.get_option(preset, "base", "allow_remote_tools"))
        max_iterations = int(self.get_option(preset, "base", "max_iterations") or agent_kwargs.get("max_iterations", 20))
        trace_id = self.get_option(preset, "debug", "trace_id") or agent_kwargs.get("trace_id", None)
        router_stream_mode = self.get_option(preset, "router", "stream_mode") or agent_kwargs.get("router_stream_mode", "realtime")
        verbose = bool(agent_kwargs.get("verbose", False))
        logger = StdLogger(prefix="[flow]") if verbose else NullLogger()
        option_get = make_option_getter(self, preset)

        orchestrator = FlowOrchestrator(window=window, logger=logger)
        logger.debug(f"[schema] {schema}")

        result = await orchestrator.run_flow(
            schema=schema or [],
            messages=messages,
            ctx=ctx,
            bridge=bridge,
            agent_kwargs=agent_kwargs,
            preset=preset,
            model=model,
            stream=stream,
            use_partial_ctx=use_partial_ctx or False,
            base_prompt=base_prompt,
            allow_local_tools_default=allow_local_tools_default,
            allow_remote_tools_default=allow_remote_tools_default,
            function_tools=function_tools,
            trace_id=trace_id,
            max_iterations=max_iterations,
            router_stream_mode=str(router_stream_mode).lower(),
            option_get=option_get,
        )

        final_output = result.final_output or ""
        last_response_id = result.last_response_id or ""

        return result.ctx, final_output, last_response_id