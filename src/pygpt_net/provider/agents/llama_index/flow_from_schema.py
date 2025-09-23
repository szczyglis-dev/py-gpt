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
from typing import Any, Dict, Optional, List, Tuple

from pygpt_net.core.agents.custom.logging import StdLogger, NullLogger
from pygpt_net.core.types import AGENT_MODE_WORKFLOW, AGENT_TYPE_LLAMA
from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem
from pygpt_net.core.bridge import BridgeContext

from agents import TResponseInputItem

from ..base import BaseAgent
from pygpt_net.core.agents.custom.llama_index.runner import DynamicFlowWorkflowLI
from pygpt_net.core.agents.custom.llama_index.utils import make_option_getter


class Agent(BaseAgent):
    """
    Dynamic Flow (LlamaIndex 0.13) – provider that returns a workflow-like object
    compatible with predefined LlamaWorkflow runner (run() -> handler.stream_events()).
    """
    def __init__(self, *args, **kwargs):
        super(Agent, self).__init__(*args, **kwargs)
        self.id = "llama_custom"
        self.type = AGENT_TYPE_LLAMA
        self.mode = AGENT_MODE_WORKFLOW
        self.name = "Custom"

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Build and return DynamicFlowWorkflowLI.
        Expected kwargs from your app:
          - schema: List[dict]
          - llm: LlamaIndex LLM (base) – użyty gdy brak per-node modelu
          - tools: List[BaseTool] (LI)
          - messages: Optional[List[TResponseInputItem]] – initial, dla pierwszego agenta
          - context: BridgeContext (preset do get_option)
          - router_stream_mode / max_iterations / stream / logger / model (default ModelItem)
        """
        schema: List[Dict[str, Any]] = kwargs.get("schema") or []
        llm = kwargs.get("llm")
        tools = kwargs.get("tools", []) or []
        initial_messages: Optional[List[TResponseInputItem]] = kwargs.get("chat_history")
        verbose = bool(kwargs.get("verbose", False))

        context: BridgeContext = kwargs.get("context", BridgeContext())
        preset: Optional[PresetItem] = context.preset
        default_model: ModelItem = kwargs.get("model", ModelItem())

        base_prompt = self.get_option(preset, "base", "prompt")
        allow_local_tools_default = bool(self.get_option(preset, "base", "allow_local_tools"))
        allow_remote_tools_default = bool(self.get_option(preset, "base", "allow_remote_tools"))
        max_iterations = int(self.get_option(preset, "base", "max_iterations") or kwargs.get("max_iterations", 20))
        router_stream_mode = self.get_option(preset, "router", "stream_mode") or kwargs.get("router_stream_mode", "realtime")

        option_get = make_option_getter(self, preset)
        stream = bool(kwargs.get("stream", False))
        logger = StdLogger(prefix="[flow]") if verbose else NullLogger()

        return DynamicFlowWorkflowLI(
            window=window,
            logger=logger,
            schema=schema,
            initial_messages=initial_messages,
            preset=preset,
            default_model=default_model,
            option_get=option_get,
            router_stream_mode=str(router_stream_mode).lower(),
            allow_local_tools_default=allow_local_tools_default,
            allow_remote_tools_default=allow_remote_tools_default,
            max_iterations=max_iterations,
            llm=llm,
            tools=tools,
            stream=stream,
            base_prompt=base_prompt,
            timeout=120,
            verbose=True,
        )

    async def run(self, *args, **kwargs) -> Tuple[Any, str, str]:
        raise NotImplementedError("Use get_agent() and run it via LlamaWorkflow runner.")