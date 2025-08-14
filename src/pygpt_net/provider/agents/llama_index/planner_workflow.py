#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.14 03:00:00                  #
# ================================================== #

from typing import Dict, Any, List

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import (
    AGENT_TYPE_LLAMA,
    AGENT_MODE_WORKFLOW,
)
from llama_index.core.llms.llm import LLM
from llama_index.core.tools.types import BaseTool

from .workflow.planner import (
    DEFAULT_INITIAL_PLAN_PROMPT,
    DEFAULT_PLAN_REFINE_PROMPT,
    DEFAULT_EXECUTE_PROMPT
)
from ..base import BaseAgent

class PlannerAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super(PlannerAgent, self).__init__(*args, **kwargs)
        self.id = "planner"
        self.type = AGENT_TYPE_LLAMA
        self.mode = AGENT_MODE_WORKFLOW
        self.name = "Planner"

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Get agent instance

        :param window: Window instance
        :param kwargs: Agent parameters
        :return: PlannerWorkflow instance
        """
        from .workflow.planner import PlannerWorkflow

        context = kwargs.get("context", BridgeContext())
        preset = context.preset
        tools: List[BaseTool] = kwargs.get("tools", []) or []
        llm: LLM = kwargs.get("llm", None)
        verbose: bool = kwargs.get("verbose", False)
        max_steps: int = kwargs.get("max_steps", 12)

        # get prompts from options or use defaults
        prompt_step = self.get_option(preset, "step", "prompt")
        prompt_plan_initial = self.get_option(preset, "plan", "prompt")
        prompt_plan_refine = self.get_option(preset, "plan_refine", "prompt")
        if not prompt_step:
            prompt_step = DEFAULT_EXECUTE_PROMPT
        if not prompt_plan_initial:
            prompt_plan_initial = DEFAULT_INITIAL_PLAN_PROMPT
        if not prompt_plan_refine:
            prompt_plan_refine = DEFAULT_PLAN_REFINE_PROMPT

        return PlannerWorkflow(
            tools=tools,
            llm=llm,
            verbose=verbose,
            max_steps=max_steps,
            system_prompt=prompt_step,
            initial_plan_prompt= prompt_plan_initial,
            plan_refine_prompt= prompt_plan_refine,
        )

    def get_options(self) -> Dict[str, Any]:
        """
        Return Agent options

        :return: dict of options
        """
        return {
            "step": {
                "label": "Execute prompt",
                "options": {
                    "prompt": {
                        "type": "textarea",
                        "label": "Prompt",
                        "description": "Steps execute prompt",
                        "default": DEFAULT_EXECUTE_PROMPT,
                    },
                }
            },
            "plan": {
                "label": "Planner (initial))",
                "options": {
                    "prompt": {
                        "type": "textarea",
                        "label": "Prompt",
                        "description": "Initial plan prompt",
                        "default": DEFAULT_INITIAL_PLAN_PROMPT,
                    },
                }
            },
            "plan_refine": {
                "label": "Planner (refine)",
                "options": {
                    "prompt": {
                        "type": "textarea",
                        "label": "Prompt",
                        "description": "Plan refine prompt",
                        "default": DEFAULT_PLAN_REFINE_PROMPT,
                    },
                }
            },
        }