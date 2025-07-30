#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.30 00:00:00                  #
# ================================================== #

from typing import Dict, Any, Tuple

from agents import (
    Agent as OpenAIAgent,
    Runner,
    RunConfig,
    ModelSettings,
)

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import (
    AGENT_MODE_OPENAI,
    AGENT_TYPE_OPENAI,
)

from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem

from pygpt_net.provider.gpt.agents.client import get_custom_model_provider, set_openai_env
from pygpt_net.provider.gpt.agents.remote_tools import get_remote_tools, is_computer_tool
from pygpt_net.provider.gpt.agents.response import StreamHandler

from ..base import BaseAgent

class Agent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super(Agent, self).__init__(*args, **kwargs)
        self.id = "openai_agent_experts"
        self.type = AGENT_TYPE_OPENAI
        self.mode = AGENT_MODE_OPENAI
        self.name = "OpenAI Agents: with experts"

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Return Agent provider instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent provider instance
        """
        context = kwargs.get("context", BridgeContext())
        preset = context.preset
        system_prompt = kwargs.get("system_prompt", "")
        agent_name = preset.name if preset else "Agent"
        model = kwargs.get("model", ModelItem())
        tools = kwargs.get("function_tools", [])
        handoffs = kwargs.get("handoffs", [])

        # append remote tools if available
        tool_kwargs = {
            "window": window,
            "model": model,
            "preset": preset,
            "is_expert_call": False,
        }
        remote_tools = get_remote_tools(**tool_kwargs)
        all_tools = remote_tools + tools

        kwargs = {
            "name": agent_name,
            "instructions": system_prompt,
            "model": model.id,
            "tools": all_tools,
            "handoffs": handoffs,
        }
        if is_computer_tool(**tool_kwargs):
            kwargs["model_settings"] = ModelSettings(truncation="auto")
        return OpenAIAgent(**kwargs)


    def get_expert(
            self,
            window,
            prompt: str,
            model: ModelItem,
            preset: PresetItem = None,
            tools: list = None,
    ) -> OpenAIAgent:
        """
        Return Agent provider instance

        :param window: window instance
        :param prompt: Expert prompt
        :param model: Model item
        :param preset: Preset item
        :param tools: List of function tools
        :return: Agent provider instance
        """
        agent_name = preset.name if preset else "Agent"

        # append remote tools if available
        tool_kwargs = {
            "window": window,
            "model": model,
            "preset": preset,
            "is_expert_call": True,
        }
        remote_tools = get_remote_tools(**tool_kwargs)
        all_tools = remote_tools + tools
        kwargs = {
            "name": agent_name,
            "instructions": prompt,
            "model": model.id,
            "tools": all_tools,
        }
        if is_computer_tool(**tool_kwargs):
            kwargs["model_settings"] = ModelSettings(truncation="auto")
        return OpenAIAgent(**kwargs)

    async def run(
            self,
            window: Any = None,
            agent_kwargs: Dict[str, Any] = None,
            previous_response_id: str = None,
            messages: list = None,
            ctx: CtxItem = None,
            stream: bool = False,
            stopped: callable = None,
            on_step: callable = None,
            on_stop: callable = None,
            on_error: callable = None,
    ) -> Tuple[str, str]:
        """
        Run agent (async)

        :param window: Window instance
        :param agent_kwargs: Additional agent parameters
        :param previous_response_id: ID of the previous response (if any)
        :param messages: Conversation messages
        :param ctx: Context item
        :param stream: Whether to stream output
        :param stopped: Callback for stop event received from the user
        :param on_step: Callback for each step
        :param on_stop: Callback for stopping the process
        :param on_error: Callback for error handling
        :return: Final output and response ID
        """
        final_output = ""
        response_id = None
        model = agent_kwargs.get("model", ModelItem())
        verbose = agent_kwargs.get("verbose", False)
        context = agent_kwargs.get("context", BridgeContext())
        tools = agent_kwargs.get("function_tools", [])
        max_steps = agent_kwargs.get("max_iterations", 10)
        preset = context.preset if context else None

        # prepare experts as agents
        experts = []
        uuids = preset.experts
        for uuid in uuids:
            expert = window.core.presets.get_by_uuid(uuid)
            if expert:
                experts.append(expert)

        expert_agents = []
        for expert in experts:
            model = window.core.models.get(expert.model)
            expert_agent = self.get_expert(
                window=window,
                prompt=expert.prompt,
                model=model,
                preset=expert,
                tools=tools,
            )
            expert_agents.append(expert_agent)
            if verbose:
                print(f"Adding expert: {expert.name} ({model.id})")

        agent_kwargs["handoffs"] = expert_agents
        agent = self.get_agent(window, agent_kwargs)

        kwargs = {
            "input": messages,
            "max_turns": int(max_steps),
        }
        if model.provider != "openai":
            custom_provider = get_custom_model_provider(window, model)
            kwargs["run_config"] = RunConfig(model_provider=custom_provider)
        else:
            set_openai_env(window)
            if previous_response_id:
                kwargs["previous_response_id"] = previous_response_id

        if not stream:
            result = await Runner.run(
                agent,
                **kwargs
            )
            final_output, last_response_id = window.core.gpt.responses.unpack_agent_response(result, ctx)
            response_id = result.last_response_id
            if verbose:
                print("Final response:", result)
        else:
            result = Runner.run_streamed(
                agent,
                **kwargs
            )
            handler = StreamHandler(window, on_step)
            async for event in result.stream_events():
                if stopped():
                    on_stop(ctx)
                    break
                final_output, response_id = handler.handle(event, ctx)

        return final_output, response_id


