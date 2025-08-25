#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.26 01:00:00                  #
# ================================================== #

from typing import Dict, Any

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import (
    AGENT_MODE_WORKFLOW,
    AGENT_TYPE_LLAMA,
)
from pygpt_net.utils import trans

from .workflow.codeact import DEFAULT_CODE_ACT_PROMPT
from ..base import BaseAgent

class CodeActAgent(BaseAgent):

    def __init__(self, *args, **kwargs):
        super(CodeActAgent, self).__init__(*args, **kwargs)
        self.id = "code_act"
        self.type = AGENT_TYPE_LLAMA
        self.mode = AGENT_MODE_WORKFLOW
        self.name = "CodeAct"

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Return Agent provider instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent provider instance
        """
        # from llama_index.core.agent.workflow import CodeActAgent as Agent
        from .workflow.codeact import CodeActAgent as Agent  # <-- custom version with tools

        context = kwargs.get("context", BridgeContext())
        tools = kwargs.get("plugin_tools", {})
        specs = kwargs.get("plugin_specs", [])
        retriever_tool = kwargs.get("retriever_tools", None)
        workdir = kwargs.get("workdir", "/data")
        llm = kwargs.get("llm", None)
        preset = context.preset
        system_prompt = self.get_option(preset, "additional", "prompt")
        code_prompt = self.get_option(preset, "base", "prompt")
        if not code_prompt:
            code_prompt = DEFAULT_CODE_ACT_PROMPT  # use default prompt if not set
        kwargs = {
            "code_execute_fn": window.core.agents.tools.code_execute_fn.execute,
            "plugin_tool_fn": window.core.agents.tools.tool_exec,
            "plugin_tools": tools,
            "plugin_specs": specs,
            "tool_retriever": retriever_tool,
            "llm": llm,
            "system_prompt": system_prompt,  # additional
            "code_act_system_prompt": code_prompt.replace("{workdir}", workdir),
        }
        return Agent(**kwargs)

    def get_options(self) -> Dict[str, Any]:
        """
        Return Agent options

        :return: dict of options
        """
        return {
            "base": {
                "label": trans("agent.coder.base.label"),
                "options": {
                    "prompt": {
                        "type": "textarea",
                        "label": trans("agent.option.prompt"),
                        "description": trans("agent.coder.base.prompt.desc"),
                        "default": DEFAULT_CODE_ACT_PROMPT,
                    },
                }
            },
            "additional": {
                "label": trans("agent.coder.additional.label"),
                "options": {
                    "prompt": {
                        "type": "textarea",
                        "label": trans("agent.option.prompt"),
                        "description": trans("agent.coder.additional.prompt.desc"),
                        "default": "",
                    },
                }
            },
        }