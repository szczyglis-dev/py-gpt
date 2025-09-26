#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.26 17:00:00                  #
# ================================================== #

import copy
from typing import Dict, Any, Tuple, Union, Optional

from agents import (
    Agent as OpenAIAgent,
    Runner,
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

from pygpt_net.provider.api.openai.agents.remote_tools import append_tools
from pygpt_net.provider.api.openai.agents.response import StreamHandler
from pygpt_net.provider.api.openai.agents.experts import get_experts
from pygpt_net.utils import trans

from ..base import BaseAgent


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
            "name": self.get_option(preset, option_key, "name"),
            "instructions": self.get_option(preset, option_key, "prompt"),
            "model": window.core.agents.provider.get_openai_model(model),
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

    def reverse_history(
            self,
            items: list[TResponseInputItem]
    ):
        """
        Reverse the roles of items in the input list in history (assistant to user)

        :param items: List of input items
        :return: List of input items with reversed roles
        """
        counter = 1
        for item in items:
            if item.get("role") == "assistant":
                if counter % 2 == 0:
                    item["role"] = "user"
                counter += 1
        return items

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
        if model.provider == "openai":
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
            use_partial_ctx: Optional[bool] = False,
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
        :param use_partial_ctx: Use partial ctx per cycle
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

        bot_1_name = self.get_option(preset, "bot_1", "name")
        bot_1_kwargs = copy.deepcopy(agent_kwargs)
        bot_2_kwargs = copy.deepcopy(agent_kwargs)

        bot_1_kwargs["bot_id"] = 1
        if experts:
            bot_1_kwargs["handoffs"] = experts
        bot_1 = self.get_agent(window, bot_1_kwargs)

        model_2 = model
        model_name_2 = self.get_option(preset, "bot_2", "model")
        if model_name_2:
            model_2 = window.core.models.get(model_name_2)
            bot_2_kwargs["model"] = model_2
        bot_2_name = self.get_option(preset, "bot_2", "name")
        bot_2_kwargs["bot_id"] = 2
        if experts:
            bot_2_kwargs["handoffs"] = experts
        bot_2 = self.get_agent(window, bot_2_kwargs)

        kwargs = {
            "max_turns": int(max_steps),
        }
        input_items: list[TResponseInputItem] = messages

        # reverse history if needed
        if use_partial_ctx:
            input_items = self.reverse_history(input_items)

        if not stream:
            while True:
                # -------- bot 1 --------
                kwargs["input"] = input_items
                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                kwargs = self.prepare_model(model, window, previous_response_id, kwargs)
                ctx.set_agent_name(bot_1.name)
                result = await Runner.run(
                    bot_1,
                    **kwargs
                )
                response_id = result.last_response_id
                output_1 = final_output
                if verbose:
                    print("Final response:", result)

                final_output, last_response_id = window.core.api.openai.responses.unpack_agent_response(result, ctx)

                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                # get and reverse items
                input_items = result.to_input_list()
                input_items = self.reverse_items(input_items, verbose=reverse_verbose)

                if use_partial_ctx:
                    ctx = bridge.on_next_ctx(
                        ctx=ctx,
                        input="",  # new ctx: input
                        output=output_1,  # prev ctx: output
                        response_id=response_id,
                        stream=False,
                    )

                # -------- bot 2 --------
                kwargs["input"] = input_items
                kwargs = self.prepare_model(model_2, window, previous_response_id, kwargs)
                ctx.set_agent_name(bot_2.name)
                result = await Runner.run(
                    bot_2,
                    **kwargs
                )
                response_id = result.last_response_id
                output_2 = final_output
                if verbose:
                    print("Final response:", result)

                final_output, last_response_id = window.core.api.openai.responses.unpack_agent_response(result, ctx)
                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                # get and reverse items
                input_items = result.to_input_list()
                input_items = self.reverse_items(input_items, verbose=reverse_verbose)

                if use_partial_ctx:
                    ctx = bridge.on_next_ctx(
                        ctx=ctx,
                        input="", # new ctx: input
                        output=output_2,  # prev ctx: output
                        response_id=response_id,
                        stream=False,
                    )
        else:
            handler = StreamHandler(window, bridge)
            begin = True
            while True:
                # -------- bot 1 --------
                kwargs["input"] = input_items
                kwargs = self.prepare_model(model, window, previous_response_id, kwargs)
                ctx.set_agent_name(bot_1.name)
                result = Runner.run_streamed(
                    bot_1,
                    **kwargs
                )

                handler.reset()

                # bot 1 title
                # title = f"\n\n**{bot_1_name}**\n\n"
                # ctx.stream = title
                bridge.on_step(ctx, begin)
                begin = False
                handler.begin = begin
                # if not use_partial_ctx:
                    # handler.to_buffer(title)
                async for event in result.stream_events():
                    if bridge.stopped():
                        result.cancel()
                        bridge.on_stop(ctx)
                        break
                    final_output, response_id = handler.handle(event, ctx)

                output_1 = final_output

                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                # get and reverse items
                input_items = result.to_input_list()
                input_items = self.reverse_items(input_items, verbose=reverse_verbose)

                if use_partial_ctx:
                    ctx = bridge.on_next_ctx(
                        ctx=ctx,
                        input="",  # new ctx: input
                        output=output_1,  # prev ctx: output
                        response_id=response_id,
                        stream=True,
                    )
                    handler.new()
                else:
                    bridge.on_next(ctx)

                # -------- bot 2 --------
                kwargs["input"] = input_items
                kwargs = self.prepare_model(model_2, window, previous_response_id, kwargs)
                ctx.set_agent_name(bot_2.name)
                result = Runner.run_streamed(
                    bot_2,
                    **kwargs
                )
                handler.reset()

                # bot 2 title
                # title = f"\n\n**{bot_2_name}**\n\n"
                # ctx.stream = title
                bridge.on_step(ctx, False)
                # if not use_partial_ctx:
                    # handler.to_buffer(title)
                async for event in result.stream_events():
                    if bridge.stopped():
                        result.cancel()
                        bridge.on_stop(ctx)
                        break
                    final_output, response_id = handler.handle(event, ctx)

                output_2 = final_output

                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                # get and reverse items
                input_items = result.to_input_list()
                input_items = self.reverse_items(input_items, verbose=reverse_verbose)

                if use_partial_ctx:
                    ctx = bridge.on_next_ctx(
                        ctx=ctx,
                        input="", # new ctx: input
                        output=output_2,  # prev ctx: output
                        response_id=response_id,
                        stream=True,
                    )
                    handler.new()
                else:
                    bridge.on_next(ctx)

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
                    "name": {
                        "type": "text",
                        "label": trans("agent.option.name"),
                        "default": "Bot 1",
                    },
                    "prompt": {
                        "type": "textarea",
                        "label": trans("agent.option.prompt"),
                        "description": trans("agent.option.prompt.b1.desc"),
                        "default": self.PROMPT_BOT_1,
                    },
                    "allow_local_tools": {
                        "type": "bool",
                        "label": trans("agent.option.tools.local"),
                        "description": trans("agent.option.tools.local.desc"),
                        "default": False,
                    },
                    "allow_remote_tools": {
                        "type": "bool",
                        "label": trans("agent.option.tools.remote"),
                        "description": trans("agent.option.tools.remote.desc"),
                        "default": False,
                    },
                }
            },
            "bot_2": {
                "label": "Bot 2",
                "options": {
                    "name": {
                        "type": "text",
                        "label": trans("agent.option.name"),
                        "default": "Bot 2",
                    },
                    "model": {
                        "label": trans("agent.option.model"),
                        "type": "combo",
                        "use": "models",
                        "default": "gpt-4o",
                    },
                    "prompt": {
                        "type": "textarea",
                        "label": trans("agent.option.prompt"),
                        "description": trans("agent.option.prompt.b2.desc"),
                        "default": self.PROMPT_BOT_2,
                    },
                    "allow_local_tools": {
                        "type": "bool",
                        "label": trans("agent.option.tools.local"),
                        "description": trans("agent.option.tools.local.desc"),
                        "default": False,
                    },
                    "allow_remote_tools": {
                        "type": "bool",
                        "label": trans("agent.option.tools.remote"),
                        "description": trans("agent.option.tools.remote.desc"),
                        "default": False,
                    },
                }
            },
        }


