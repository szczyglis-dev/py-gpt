#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.01 03:00:00                  #
# ================================================== #
# Based on OpenAI examples: https://github.com/openai/openai-agents-python/blob/main/examples

from pydantic import BaseModel

from agents import Agent

from pygpt_net.item.preset import PresetItem
from pygpt_net.provider.api.openai.agents.remote_tools import append_tools


class WebSearchItem(BaseModel):
    reason: str
    "Your reasoning for why this search is important to the query."

    query: str
    "The search term to use for the web search."

class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem]
    """A list of web searches to perform to best answer the query."""

def get_planner_agent(
        window,
        preset: PresetItem,
        tools: list,
        config: dict,
) -> Agent:
    """
    Returns the planner agent used to create a web search plan.

    :param window: The application window context.
    :param preset: The preset configuration for the agent.
    :param tools: A list of tools that the agent can use.
    :param config
    """
    kwargs = {
        "name": "PlannerAgent",
        "instructions": config["prompt"],
        "model": window.core.agents.provider.get_openai_model(config["model"]),
        "output_type": WebSearchPlan,
    }
    tool_kwargs = append_tools(
        tools=tools,
        window=window,
        model=config["model"],
        preset=preset,
        allow_local_tools=config["allow_local_tools"],
        allow_remote_tools=config["allow_remote_tools"],
    )
    kwargs.update(tool_kwargs)  # update kwargs with tools
    return Agent(**kwargs)