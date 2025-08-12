#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.12 19:00:00                  #
# ================================================== #

from typing import Dict, Any

from pygpt_net.core.types import (
    AGENT_MODE_PLAN,
    AGENT_TYPE_LLAMA,
)

from ..base import BaseAgent

class PlannerAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super(PlannerAgent, self).__init__(*args, **kwargs)
        self.id = "planner"
        self.type = AGENT_TYPE_LLAMA
        self.mode = AGENT_MODE_PLAN
        self.name = "Planner (sub-tasks)"

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Return Agent provider instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent provider instance
        """
        from llama_index.core.agent import (
            StructuredPlannerAgent,
            FunctionCallingAgentWorker,
        )

        tools = kwargs.get("tools", [])
        verbose = kwargs.get("verbose", False)
        llm = kwargs.get("llm", None)
        chat_history = kwargs.get("chat_history", [])
        max_iterations = kwargs.get("max_iterations", 10)
        worker = FunctionCallingAgentWorker.from_tools(
            tools=tools,
            llm=llm,
            verbose=verbose,
        )
        return StructuredPlannerAgent(
            agent_worker=worker,
            llm=llm,
            chat_history=chat_history,
            tools=tools,
            verbose=verbose,
        )
