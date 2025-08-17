#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.17 02:00:00                  #
# ================================================== #

from typing import Dict, Any, List

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import (
    AGENT_TYPE_LLAMA,
    AGENT_MODE_WORKFLOW,
)
from llama_index.core.llms.llm import LLM
from llama_index.core.tools.types import BaseTool

from .workflow.supervisor import (
    get_workflow,
    SUPERVISOR_PROMPT,
    WORKER_PROMPT,
)
from ..base import BaseAgent

class SupervisorAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super(SupervisorAgent, self).__init__(*args, **kwargs)
        self.id = "supervisor"
        self.type = AGENT_TYPE_LLAMA
        self.mode = AGENT_MODE_WORKFLOW
        self.name = "Supervisor + worker"

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Get agent instance

        :param window: Window instance
        :param kwargs: Agent parameters
        :return: PlannerWorkflow instance
        """
        context = kwargs.get("context", BridgeContext())
        preset = context.preset
        tools: List[BaseTool] = kwargs.get("tools", []) or []
        llm_supervisor: LLM = kwargs.get("llm", None)
        verbose: bool = kwargs.get("verbose", False)
        max_steps: int = kwargs.get("max_steps", 12)

        # get prompts from options or use defaults
        prompt_supervisor = self.get_option(preset, "supervisor", "prompt")
        prompt_worker = self.get_option(preset, "worker", "prompt")
        if not prompt_supervisor:
            prompt_supervisor = SUPERVISOR_PROMPT
        if not prompt_worker:
            prompt_worker = WORKER_PROMPT

        # get worker LLM from options
        model_worker = window.core.models.get(
            self.get_option(preset, "worker", "model")
        )
        llm_worker = window.core.idx.llm.get(model_worker, stream=False)
        worker_memory_session_id = ""
        if context.ctx and context.ctx.meta:
            worker_memory_session_id = "llama_worker_session_" + str(context.ctx.meta.id)

        # create workflow
        return get_workflow(
                tools,
                llm_supervisor=llm_supervisor,
                llm_worker=llm_worker,
                verbose=verbose,
                max_steps=max_steps,
                prompt_supervisor=prompt_supervisor,
                prompt_worker=prompt_worker,
                worker_memory_session_id=worker_memory_session_id,
        )

    def get_options(self) -> Dict[str, Any]:
        """
        Return Agent options

        :return: dict of options
        """
        return {
            "supervisor": {
                "label": "Supervisor",
                "options": {
                    "prompt": {
                        "type": "textarea",
                        "label": "Prompt",
                        "description": "Prompt for supervisor",
                        "default": SUPERVISOR_PROMPT,
                    },
                }
            },
            "worker": {
                "label": "Worker",
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
                        "description": "Prompt for worker",
                        "default": WORKER_PROMPT,
                    },
                }
            },
        }
