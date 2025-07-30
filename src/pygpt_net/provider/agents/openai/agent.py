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

from pygpt_net.provider.gpt.agents.client import get_custom_model_provider, set_openai_env
from pygpt_net.provider.gpt.agents.remote_tools import get_remote_tools, is_computer_tool
from pygpt_net.provider.gpt.agents.computer import Agent as ComputerAgent, LocalComputer
from pygpt_net.provider.gpt.agents.response import StreamHandler

from ..base import BaseAgent

class Agent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super(Agent, self).__init__(*args, **kwargs)
        self.id = "openai_agent_base"
        self.type = AGENT_TYPE_OPENAI
        self.mode = AGENT_MODE_OPENAI
        self.name = "OpenAI Agents: simple"

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
        agent = self.get_agent(window, agent_kwargs)
        context = agent_kwargs.get("context", BridgeContext())
        max_steps = agent_kwargs.get("max_iterations", 10)
        preset = context.preset if context else None
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

        tool_kwargs = {
            "window": window,
            "model": model,
            "preset": preset,
            "is_expert_call": False,
        }

        # call computer agent if computer tool is enabled
        if is_computer_tool(**tool_kwargs):
            computer = LocalComputer(window)
            agent = ComputerAgent(
                computer=computer,
                ctx=ctx,
                stream=stream,
                stopped=stopped,
                on_step=on_step,
                on_stop=on_stop,
                on_error=on_error,
            )
            items = messages
            output_items, response_id = agent.run(
                input=items,
                debug=verbose,
            )
            if output_items[-1]["type"] == "message":
                if verbose:
                    print("Final response:", response_id, output_items[-1])
                final_output = output_items[-1]["content"][0]["text"]

        # call default agent
        else:
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


