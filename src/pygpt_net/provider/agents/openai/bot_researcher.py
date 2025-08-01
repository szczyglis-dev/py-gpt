#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.01 19:00:00                  #
# ================================================== #

from typing import Dict, Any, Tuple, Union

from agents import (
    Agent as OpenAIAgent,
    Runner,
    RunConfig,
    ModelSettings,
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
from .bots.research_bot.manager import ResearchManager

class Agent(BaseAgent):

    PROMPT_PLANNER = (
        "You are a helpful research assistant. Given a query, come up with a set of web searches "
        "to perform to best answer the query. Output between 5 and 20 terms to query for."
    )

    PROMPT_SEARCH = (
        "You are a research assistant. Given a search term, you search the web for that term and "
        "produce a concise summary of the results. The summary must be 2-3 paragraphs and less than 300 "
        "words. Capture the main points. Write succinctly, no need to have complete sentences or good "
        "grammar. This will be consumed by someone synthesizing a report, so its vital you capture the "
        "essence and ignore any fluff. Do not include any additional commentary other than the summary "
        "itself."
    )

    PROMPT_WRITER = (
        "You are a senior researcher tasked with writing a cohesive report for a research query. "
        "You will be provided with the original query, and some initial research done by a research "
        "assistant.\n"
        "You should first come up with an outline for the report that describes the structure and "
        "flow of the report. Then, generate the report and return that as your final output.\n"
        "The final output should be in markdown format, and it should be lengthy and detailed. Aim "
        "for 5-10 pages of content, at least 1000 words."
    )

    def __init__(self, *args, **kwargs):
        super(Agent, self).__init__(*args, **kwargs)
        self.id = "openai_agent_bot_researcher"
        self.type = AGENT_TYPE_OPENAI
        self.mode = AGENT_MODE_OPENAI
        self.name = "Research bot"

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
        kwargs = {
            "name": agent_name,
            "instructions": system_prompt,
            "model": model.id,
            "handoffs": handoffs,
        }
        tool_kwargs = append_tools(
            tools=tools,
            window=window,
            model=model,
            preset=preset,
            allow_local_tools=True,
            allow_remote_tools=True,
        )
        kwargs.update(tool_kwargs)  # update kwargs with tools
        return OpenAIAgent(**kwargs)

    async def run(
            self,
            window: Any = None,
            agent_kwargs: Dict[str, Any] = None,
            previous_response_id: str = None,
            messages: list = None,
            ctx: CtxItem = None,
            stream: bool = False,
            bridge: ConnectionContext = None,
    ) -> Tuple[str, Union[str, None]]:
        """
        Run agent (async)

        :param window: Window instance
        :param agent_kwargs: Additional agent parameters
        :param previous_response_id: ID of the previous response (if any)
        :param messages: Conversation messages
        :param ctx: Context item
        :param stream: Whether to stream output
        :param bridge: Connection context for agent operations
        :return: Final output and response ID
        """
        response_id = None
        model = agent_kwargs.get("model", ModelItem())
        verbose = agent_kwargs.get("verbose", False)
        context = agent_kwargs.get("context", BridgeContext())
        preset = context.preset if context else None
        query = context.prompt if context else ""
        max_steps = agent_kwargs.get("max_iterations", 10)
        tools = agent_kwargs.get("function_tools", [])

        # allow usage of custom prompt for the writer (final report)
        prompt = self.PROMPT_WRITER
        custom_prompt = self.get_option(preset, "writer", "prompt")
        if custom_prompt and custom_prompt.strip() != "":
            prompt = custom_prompt

        model_planner = window.core.models.get(
            self.get_option(preset, "planner", "model")
        )
        model_search = window.core.models.get(
            self.get_option(preset, "search", "model")
        )

        # prepare provider config
        model_kwargs = {}
        model_search_kwargs = {}
        model_planner_kwargs = {}

        if model.provider != "openai":
            custom_provider = get_custom_model_provider(window, model)
            model_kwargs["run_config"] = RunConfig(model_provider=custom_provider)

        if model_search.provider != "openai":
            custom_provider = get_custom_model_provider(window, model_search)
            model_search_kwargs["run_config"] = RunConfig(model_provider=custom_provider)

        if model_planner.provider != "openai":
            custom_provider = get_custom_model_provider(window, model_planner)
            model_planner_kwargs["run_config"] = RunConfig(model_provider=custom_provider)

        bot = ResearchManager(
            window=window,
            ctx=ctx,
            preset=preset,
            tools=tools,
            bridge=bridge,
            stream=stream,
            planner_config={
                "prompt": self.get_option(preset, "planner", "prompt"),
                "model": model_planner,
                "allow_local_tools": self.get_option(preset, "planner", "allow_local_tools"),
                "allow_remote_tools": self.get_option(preset, "planner", "allow_remote_tools"),
                "run_kwargs": model_planner_kwargs,
            },
            search_config={
                "prompt": self.get_option(preset, "search", "prompt"),
                "model": model_search,
                "allow_local_tools": self.get_option(preset, "search", "allow_local_tools"),
                "allow_remote_tools": self.get_option(preset, "search", "allow_remote_tools"),
                "run_kwargs": model_search_kwargs,
            },
            writer_config={
                "prompt": prompt,
                "model": model,
                "allow_local_tools": self.get_option(preset, "writer", "allow_local_tools"),
                "allow_remote_tools": self.get_option(preset, "writer", "allow_remote_tools"),
                "run_kwargs": model_kwargs,
            },
            history=messages if messages else [],
        )

        if model.provider == "openai":
            set_openai_env(window)

        if not stream:
            final_output = await bot.run(query)
        else:
            final_output = await bot.run(query)

        return final_output, response_id


    def get_options(self) -> Dict[str, Any]:
        """
        Return Agent options

        :return: dict of options
        """
        return {
            "writer": {
                "label": "Base agent",
                "options": {
                    "prompt": {
                        "type": "textarea",
                        "label": "Prompt",
                        "description": "Prompt for base agent",
                        "default": self.PROMPT_WRITER,
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
            "planner": {
                "label": "Planner",
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
                        "description": "Prompt for planner agent",
                        "default": self.PROMPT_PLANNER,
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
            "search": {
                "label": "Search",
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
                        "description": "Prompt for search agent",
                        "default": self.PROMPT_SEARCH,
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
                        "default": True,
                    },
                }
            },
        }


