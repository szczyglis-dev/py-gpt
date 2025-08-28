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
from agents import Agent, WebSearchTool
from agents.model_settings import ModelSettings

from pygpt_net.core.types import OPENAI_REMOTE_TOOL_DISABLE_WEB_SEARCH
from pygpt_net.item.preset import PresetItem
from pygpt_net.provider.api.openai.agents.remote_tools import append_tools


def get_search_agent(
        window,
        preset: PresetItem,
        tools: list,
        config: dict
) -> Agent:
    tool_kwargs = append_tools(
        tools=tools,
        window=window,
        model=config["model"],
        preset=preset,
        allow_local_tools=config["allow_local_tools"],
        allow_remote_tools=config["allow_remote_tools"],
    )
    kwargs = {
        "name": "SearchAgent",
        "instructions": config["prompt"],
        "model": window.core.agents.provider.get_openai_model(config["model"]),
    }
    kwargs.update(tool_kwargs)  # update kwargs with tools

    if config["allow_remote_tools"]:
        if not window.core.config.get("remote_tools.web_search", False):
            if (config["model"].is_gpt()
                    and not config["model"].id in OPENAI_REMOTE_TOOL_DISABLE_WEB_SEARCH
                    and not config["model"].id.startswith("computer-use")):
                if "tools" not in kwargs:
                    kwargs["tools"] = []
                kwargs["tools"].append(WebSearchTool())

    if config["allow_local_tools"] or config["allow_remote_tools"]:
        kwargs["model_settings"] = ModelSettings(tool_choice="required")

    return Agent(**kwargs)