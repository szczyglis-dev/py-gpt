#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.14 01:00:00                  #
# ================================================== #

from typing import Dict, Any, List

from pygpt_net.core.types import (
    AGENT_TYPE_LLAMA,
    AGENT_MODE_WORKFLOW,
)
from llama_index.core.llms.llm import LLM
from llama_index.core.tools.types import BaseTool

from ..base import BaseAgent

class OpenAIAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super(OpenAIAgent, self).__init__(*args, **kwargs)
        self.id = "openai"
        self.type = AGENT_TYPE_LLAMA
        self.mode = AGENT_MODE_WORKFLOW
        self.name = "OpenAI"

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Get agent instance

        :param window: Window instance
        :param kwargs: Agent parameters
        :return: PlannerWorkflow instance
        """
        from .workflow.openai import OpenAIWorkflowAgent

        tools: List[BaseTool] = kwargs.get("tools", []) or []
        llm: LLM = kwargs.get("llm", None)
        verbose: bool = kwargs.get("verbose", False)
        system_prompt: str = kwargs.get("system_prompt", None)
        max_steps: int = kwargs.get("max_steps", 12)

        return OpenAIWorkflowAgent(
            tools=tools,
            llm=llm,
            system_prompt=system_prompt,
            verbose=verbose,
        )