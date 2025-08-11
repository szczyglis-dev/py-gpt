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
# Based on OpenAI examples: https://github.com/openai/openai-agents-python/blob/main/examples
# Agent used to synthesize a final report from the individual summaries.
from pydantic import BaseModel

from agents import Agent

from pygpt_net.item.preset import PresetItem
from pygpt_net.provider.gpt.agents.remote_tools import append_tools


class ReportData(BaseModel):
    short_summary: str
    """A short 2-3 sentence summary of the findings."""

    markdown_report: str
    """The final report"""

    follow_up_questions: list[str]
    """Suggested topics to research further"""

def get_writer_agent(
        window,
        preset: PresetItem,
        tools: list,
        config: dict,
) -> Agent:
    kwargs = {
        "name": "WriterAgent",
        "instructions": config["prompt"],
        "model": config["model"].id,
        "output_type": ReportData,
    }
    if config.get("experts"):
        kwargs["handoffs"] = config["experts"]

    tool_kwargs = append_tools(
        tools=tools,
        window=window,
        model=config["model"],
        preset=preset,
        allow_local_tools=config["allow_local_tools"],
        allow_remote_tools= config["allow_remote_tools"],
    )
    kwargs.update(tool_kwargs)  # update kwargs with tools
    return Agent(**kwargs)
