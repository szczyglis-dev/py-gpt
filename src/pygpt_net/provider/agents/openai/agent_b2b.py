#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.11 19:00:00                  #
# ================================================== #

import copy
from typing import Dict, Any, Tuple, Union

from agents import (
    Agent as OpenAIAgent,
    Runner,
    RunConfig,
    TResponseInputItem,
)

from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import (
    AGENT_MODE_OPENAI,
    AGENT_TYPE_OPENAI,
)

from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem

from pygpt_net.provider.gpt.agents.client import get_custom_model_provider, set_openai_env
from pygpt_net.provider.gpt.agents.remote_tools import append_tools
from pygpt_net.provider.gpt.agents.response import StreamHandler

from ..base import BaseAgent
from ...gpt.agents.experts import get_experts


class Agent(BaseAgent):

    PROMPT_BOT_1 = (
        "You're an advanced AI assistant and an expert in every field. "
        "Imagine that I am also such an AI assistant and converse with me in an expert manner. "
        "As two AI assistants, let's brainstorm and arrive at some advanced solutions."
    )

    PROMPT_BOT_2 = (
        "You're an advanced AI assistant and an expert in every field. "
        "Imagine that I am also such an AI assistant and converse with me in an expert manner. "
        "As two AI assistants, let's brainstorm and arrive at some advanced solutions."
    )

    def __init__(self, *args, **kwargs):
        super(Agent, self).__init__(*args, **kwargs)
        self.id = "openai_agent_b2b"
        self.type = AGENT_TYPE_OPENAI
        self.mode = AGENT_MODE_OPENAI
        self.name = "Bot 2 Bot"

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Return Agent provider instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent provider instance
        """
        context = kwargs.get("context", BridgeContext())
        preset = context.preset
        model = kwargs.get("model", ModelItem())
        tools = kwargs.get("function_tools", [])
        handoffs = kwargs.get("handoffs", [])
        id = kwargs.get("bot_id", 1)
        option_key = f"bot_{id}"
        kwargs = {
            "name": "Bot {}".format(id),
            "instructions": self.get_option(preset, option_key, "prompt"),
            "model": model.id,
        }
        if handoffs:
            kwargs["handoffs"] = handoffs

        tool_kwargs = append_tools(
            tools=tools,
            window=window,
            model=model,
            preset=preset,
            allow_local_tools=self.get_option(preset, option_key, "allow_local_tools"),
            allow_remote_tools= self.get_option(preset, option_key, "allow_remote_tools"),
        )
        kwargs.update(tool_kwargs) # update kwargs with tools
        return OpenAIAgent(**kwargs)

    def reverse_items(
            self,
            items: list[TResponseInputItem],
            verbose: bool = False
    ) -> list[TResponseInputItem]:
        """
        Reverse input items for the second bot

        :param items: List of input items
        :param verbose: Whether to print debug information
        :return: Reversed list of input items
        """
        if verbose:
            print("--- BEFORE ---")
            for item in items:
                print(item)

        reversed_items = []
        for item in items:
            if item.get("role") == "assistant":
                if isinstance(item.get("content"), str):
                    content = item.get("content", "")
                    item = {
                        "role": "user",
                        "content": content,
                    }
                else:
                    content = item["content"][0].get("text", "")
                    item = {
                        "role": "user",
                        "content": content,
                    }
            elif item.get("role") == "user":
                if isinstance(item.get("content"), str):
                    content = item.get("content", "")
                else:
                    content = item["content"][0].get("text", "")
                item = {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": content,
                        }
                    ],
                }
            reversed_items.append(item)

        if verbose:
            print("--- AFTER ---")
            for item in reversed_items:
                print(item)

        return reversed_items

    def prepare_model(
            self,
            model: ModelItem,
            window: Any,
            previous_response_id: Union[str, None],
            kwargs: Dict[str, Any]
    ):
        """
        Prepare model configuration for the agent

        :param model: ModelItem instance
        :param window: Window instance
        :param previous_response_id: ID of the previous response (if any)
        :param kwargs: Additional keyword arguments for the model configuration
        :return: Prepared keyword arguments for the model
        """
        if model.provider != "openai":
            custom_provider = get_custom_model_provider(window, model)
            kwargs["run_config"] = RunConfig(model_provider=custom_provider)
        else:
            if "run_config" in kwargs:
                kwargs.pop("run_config")
            set_openai_env(window)
            if previous_response_id:
                kwargs["previous_response_id"] = previous_response_id
        return kwargs

    async def run(
            self,
            window: Any = None,
            agent_kwargs: Dict[str, Any] = None,
            previous_response_id: str = None,
            messages: list = None,
            ctx: CtxItem = None,
            stream: bool = False,
            bridge: ConnectionContext = None,
    ) -> Tuple[CtxItem, str, str]:
        """
        Run agent (async)

        :param window: Window instance
        :param agent_kwargs: Additional agent parameters
        :param previous_response_id: ID of the previous response (if any)
        :param messages: Conversation messages
        :param ctx: Context item
        :param stream: Whether to stream output
        :param bridge: Connection context for handling stop and step events
        :return: Current ctx, final output, last response ID
        """
        final_output = ""
        response_id = None
        reverse_verbose = False
        model = agent_kwargs.get("model", ModelItem())
        verbose = agent_kwargs.get("verbose", False)
        max_steps = agent_kwargs.get("max_iterations", 10)
        preset = agent_kwargs.get("preset", PresetItem())
        tools = agent_kwargs.get("function_tools", [])

        # add experts
        experts = get_experts(
            window=window,
            preset=preset,
            verbose=verbose,
            tools=tools,
        )
        if experts:
            agent_kwargs["handoffs"] = experts

        bot_1_kwargs = copy.deepcopy(agent_kwargs)
        bot_1_kwargs["bot_id"] = 1
        bot_1 = self.get_agent(window, agent_kwargs)

        model_2 = model
        bot_2_kwargs = copy.deepcopy(agent_kwargs)
        model_name_2 = self.get_option(preset, "bot_2", "model")
        if model_name_2:
            model_2 = window.core.models.get(model_name_2)
            bot_2_kwargs["model"] = model_2
        bot_2_kwargs["bot_id"] = 2
        bot_2 = self.get_agent(window, bot_2_kwargs)

        kwargs = {
            "max_turns": int(max_steps),
        }
        input_items: list[TResponseInputItem] = messages

        if not stream:
            while True:
                # -------- bot 1 --------
                kwargs["input"] = input_items
                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                kwargs = self.prepare_model(model, window, previous_response_id, kwargs)
                result = await Runner.run(
                    bot_1,
                    **kwargs
                )
                response_id = result.last_response_id
                if verbose:
                    print("Final response:", result)

                final_output, last_response_id = window.core.gpt.responses.unpack_agent_response(result, ctx)

                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                # get and reverse items
                input_items = result.to_input_list()
                input_items = self.reverse_items(input_items, verbose=reverse_verbose)

                # -------- bot 2 --------
                kwargs["input"] = input_items
                kwargs = self.prepare_model(model_2, window, previous_response_id, kwargs)
                result = await Runner.run(
                    bot_2,
                    **kwargs
                )
                response_id = result.last_response_id
                if verbose:
                    print("Final response:", result)

                final_output, last_response_id = window.core.gpt.responses.unpack_agent_response(result, ctx)
                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                # get and reverse items
                input_items = result.to_input_list()
                input_items = self.reverse_items(input_items, verbose=reverse_verbose)
        else:
            handler = StreamHandler(window, bridge)
            begin = True
            while True:
                # -------- bot 1 --------
                kwargs["input"] = input_items
                kwargs = self.prepare_model(model, window, previous_response_id, kwargs)
                result = Runner.run_streamed(
                    bot_1,
                    **kwargs
                )

                handler.reset()

                # bot 1 title
                title = "\n\n**Bot 1**\n\n"
                ctx.stream = title
                bridge.on_step(ctx, begin)
                begin = False
                handler.begin = begin
                handler.to_buffer(title)
                async for event in result.stream_events():
                    if bridge.stopped():
                        bridge.on_stop(ctx)
                        break
                    final_output, response_id = handler.handle(event, ctx)

                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                bridge.on_next(ctx)

                # get and reverse items
                input_items = result.to_input_list()
                input_items = self.reverse_items(input_items, verbose=reverse_verbose)

                # -------- bot 2 --------
                kwargs["input"] = input_items
                kwargs = self.prepare_model(model_2, window, previous_response_id, kwargs)
                result = Runner.run_streamed(
                    bot_2,
                    **kwargs
                )
                handler.reset()

                # bot 2 title
                title = "\n\n**Bot 2**\n\n"
                ctx.stream = title
                bridge.on_step(ctx, False)
                handler.to_buffer(title)
                async for event in result.stream_events():
                    if bridge.stopped():
                        bridge.on_stop(ctx)
                        break
                    final_output, response_id = handler.handle(event, ctx)

                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                bridge.on_next(ctx)

                # get and reverse items
                input_items = result.to_input_list()
                input_items = self.reverse_items(input_items, verbose=reverse_verbose)

        return ctx, final_output, response_id


    def get_options(self) -> Dict[str, Any]:
        """
        Return Agent options

        :return: dict of options
        """
        return {
            "bot_1": {
                "label": "Bot 1",
                "options": {
                    "prompt": {
                        "type": "textarea",
                        "label": "Prompt",
                        "description": "Prompt for bot 1",
                        "default": self.PROMPT_BOT_1,
                    },
                    "allow_local_tools": {
                        "type": "bool",
                        "label": "Allow local tools",
                        "description": "Allow usage of local tools for this agent",
                        "default": False,
                    },
                    "allow_remote_tools": {
                        "type": "bool",
                        "label": "Allow remote tools",
                        "description": "Allow usage of remote tools for this agent",
                        "default": False,
                    },
                }
            },
            "bot_2": {
                "label": "Bot 2",
                "options": {
                    "model": {
                        "label": "Model",
                        "type": "combo",
                        "use": "models",
                        "default": "gpt-4o",
                    },
                    "prompt": {
                        "type": "textarea",
                        "label": "Prompt",
                        "description": "Prompt for bot 2",
                        "default": self.PROMPT_BOT_2,
                    },
                    "allow_local_tools": {
                        "type": "bool",
                        "label": "Allow local tools",
                        "description": "Allow usage of local tools for this agent",
                        "default": False,
                    },
                    "allow_remote_tools": {
                        "type": "bool",
                        "label": "Allow remote tools",
                        "description": "Allow usage of remote tools for this agent",
                        "default": False,
                    },
                }
            },
        }


