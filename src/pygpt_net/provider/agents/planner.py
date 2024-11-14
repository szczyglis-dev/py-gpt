#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.15 00:00:00                  #
# ================================================== #

from llama_index.core.agent import (
    StructuredPlannerAgent,
    FunctionCallingAgentWorker,
    ReActAgentWorker,
)

from .base import BaseAgent

class PlannerAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super(PlannerAgent, self).__init__(*args, **kwargs)
        self.id = "planner"
        self.mode = "plan"  # step|plan

    def get_agent(self, window, kwargs: dict):
        """
        Return Agent provider instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent provider instance
        """
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
