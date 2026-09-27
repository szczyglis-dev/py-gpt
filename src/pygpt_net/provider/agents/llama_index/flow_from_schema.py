#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 15:55:00                  #
# ================================================== #

from __future__ import annotations
from typing import Any, Dict, Optional, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from agents import TResponseInputItem

from pygpt_net.core.types import AGENT_MODE_WORKFLOW, AGENT_TYPE_LLAMA
from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem
from pygpt_net.core.bridge import BridgeContext


from ..base import BaseAgent


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
        from pygpt_net.core.agents.custom.logging import StdLogger, NullLogger
        from pygpt_net.core.agents.custom.llama_index.runner import DynamicFlowWorkflowLI
        from pygpt_net.core.agents.custom.llama_index.utils import make_option_getter

        schema: List[Dict[str, Any]] = kwargs.get("schema") or []
        llm = kwargs.get("llm")
        tools = kwargs.get("tools", []) or []
        initial_messages: Optional[List[TResponseInputItem]] = kwargs.get("chat_history")
        verbose = bool(kwargs.get("verbose", False))

        context: BridgeContext = kwargs.get("context", BridgeContext())
        preset: Optional[PresetItem] = context.preset
        default_model: ModelItem = kwargs.get("model", ModelItem())

        base_prompt = self.get_option(preset, "base", "prompt")
        system_prompt_extra = self.get_system_prompt_extra(kwargs)
        allow_local_tools_default = bool(self.get_option(preset, "base", "allow_local_tools"))
        allow_remote_tools_default = bool(self.get_option(preset, "base", "allow_remote_tools"))
        configured_limit = self.get_option(preset, "base", "max_iterations")
        max_iterations = int(configured_limit if configured_limit is not None else kwargs.get("max_iterations", 20))
        router_stream_mode = self.get_option(preset, "router", "stream_mode") or kwargs.get("router_stream_mode", "realtime")

        option_get = make_option_getter(self, preset)
        stream = bool(kwargs.get("stream", False))
        logger = StdLogger(prefix="[flow]") if verbose else NullLogger()

        from pygpt_net.core.agents.custom.memory import MemoryManager
        from pygpt_net.core.agents.session_memory import session_value
        memory_manager = session_value(window, self, context, "memory_manager", MemoryManager)

        return DynamicFlowWorkflowLI(
            window=window,
            logger=logger,
            schema=schema,
            initial_messages=initial_messages,
            memory_manager=memory_manager,
            preset=preset,
            default_model=default_model,
            option_get=option_get,
            router_stream_mode=str(router_stream_mode).lower(),
            allow_local_tools_default=allow_local_tools_default,
            allow_remote_tools_default=allow_remote_tools_default,
            max_iterations=max_iterations,
            llm=llm,
            computer_runtime=kwargs.get("computer_runtime"),
            tools=tools,
            stream=stream,
            base_prompt=base_prompt,
            system_prompt_extra=system_prompt_extra,
            input_builder=kwargs.get("input_builder"),
            timeout=120,
            verbose=verbose,
        )

    async def run(self, *args, **kwargs) -> Tuple[Any, str, str]:
        raise NotImplementedError("Use get_agent() and run it via LlamaWorkflow runner.")
