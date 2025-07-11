#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.11 19:00:00                  #
# ================================================== #

from typing import Dict, Any

# from llama_index.core.agent.workflow import CodeActAgent as Agent
from .codeact_agent_custom import DEFAULT_CODE_ACT_PROMPT, CodeActAgent as Agent  # <-- custom version with tools

from .base import BaseAgent

class CodeActAgent(BaseAgent):

    def __init__(self, *args, **kwargs):
        super(CodeActAgent, self).__init__(*args, **kwargs)
        self.id = "code_act"
        self.mode = "workflow"

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Return Agent provider instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent provider instance
        """
        tools = kwargs.get("plugin_tools", {})
        specs = kwargs.get("plugin_specs", [])
        retriever_tool = kwargs.get("retriever_tools", None)
        workdir = kwargs.get("workdir", "/data")
        llm = kwargs.get("llm", None)
        system_prompt = kwargs.get("system_prompt", "")
        are_cmds = kwargs.get("are_commands", True)
        kwargs = {
            "code_execute_fn": window.core.agents.tools.code_execute_fn.execute,
            "plugin_tool_fn": window.core.agents.tools.tool_exec,
            "plugin_tools": tools,
            "plugin_specs": specs,
            "tool_retriever": retriever_tool,
            "llm": llm,
            "system_prompt": system_prompt,
            "code_act_system_prompt": DEFAULT_CODE_ACT_PROMPT.replace("{workdir}", workdir),
        }
        return Agent(**kwargs)
