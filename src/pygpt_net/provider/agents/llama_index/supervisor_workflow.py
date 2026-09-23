#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 17:58:00                  #
# ================================================== #

from __future__ import annotations

from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from llama_index.core.tools.types import BaseTool
    from llama_index.core.llms.llm import LLM

from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import (
    AGENT_TYPE_LLAMA,
    AGENT_MODE_WORKFLOW,
)

from pygpt_net.utils import trans
from .workflow.supervisor_prompts import SUPERVISOR_PROMPT, WORKER_PROMPT
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
        from .workflow.supervisor import get_workflow

        context = kwargs.get("context", BridgeContext())
        preset = context.preset
        tools: List[BaseTool] = kwargs.get("tools", []) or []
        verbose: bool = kwargs.get("verbose", False)
        max_steps: int = kwargs.get("max_steps", 12)
        computer_runtime = kwargs.get("computer_runtime")
        main_model = kwargs.get("model")

        supervisor_allow_local_tools = bool(
            self.get_option(preset, "supervisor", "allow_local_tools")
        )
        supervisor_allow_remote_tools = bool(
            self.get_option(preset, "supervisor", "allow_remote_tools")
        )
        worker_allow_local_tools = bool(
            self.get_option(preset, "worker", "allow_local_tools")
        )
        worker_allow_remote_tools = bool(
            self.get_option(preset, "worker", "allow_remote_tools")
        )

        # Build LLM adapters per role so provider-native remote tools are truly
        # controlled independently for Supervisor and Worker.
        llm_supervisor: LLM = kwargs.get("llm", None)
        if main_model is not None:
            llm_supervisor = window.core.idx.llm.get_agent(
                main_model,
                stream=False,
                allow_remote_tools=supervisor_allow_remote_tools,
                computer_runtime=computer_runtime if supervisor_allow_remote_tools else None,
            )

        # get prompts from options or use defaults
        prompt_supervisor = self.get_option(preset, "supervisor", "prompt")
        prompt_worker = self.get_option(preset, "worker", "prompt")
        if not prompt_supervisor:
            prompt_supervisor = SUPERVISOR_PROMPT
        if not prompt_worker:
            prompt_worker = WORKER_PROMPT
        prompt_supervisor = self.append_system_prompt_extra(prompt_supervisor, kwargs)
        prompt_worker = self.append_system_prompt_extra(prompt_worker, kwargs)

        # Worker inherits the active model unless its preset explicitly overwrites it.
        model_worker = self.resolve_model_option(
            window,
            preset,
            "worker",
            kwargs.get("model"),
        )
        llm_worker = window.core.idx.llm.get_agent(
            model_worker,
            stream=False,
            allow_remote_tools=worker_allow_remote_tools,
            computer_runtime=computer_runtime if worker_allow_remote_tools else None,
        )
        worker_memory_session_id = ""
        if context.ctx and context.ctx.meta:
            worker_memory_session_id = "llama_worker_session_" + str(context.ctx.meta.id)

        # create workflow
        return get_workflow(
                tools,
                llm_supervisor=llm_supervisor,
                llm_worker=llm_worker,
                supervisor_tools=tools if supervisor_allow_local_tools else [],
                worker_tools=tools if worker_allow_local_tools else [],
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
                "label": trans("agent.option.section.supervisor"),
                "options": {
                    "prompt": {
                        "type": "textarea",
                        "label": trans("agent.option.prompt"),
                        "description": trans("agent.option.prompt.supervisor.desc"),
                        "default": SUPERVISOR_PROMPT,
                    },
                    "allow_local_tools": {
                        "type": "bool",
                        "label": trans("agent.option.tools.local"),
                        "description": trans("agent.option.tools.local.desc"),
                        "default": False,
                    },
                    "allow_remote_tools": {
                        "type": "bool",
                        "label": trans("agent.option.tools.remote"),
                        "description": trans("agent.option.tools.remote.desc"),
                        "default": False,
                    },
                }
            },
            "worker": {
                "label": trans("agent.option.section.worker"),
                "options": {
                    "model": {
                        "label": trans("agent.option.model"),
                        "type": "combo",
                        "use": "models",
                        "default": "gpt-4o",
                    },
                    "model_overwrite": {
                        "label": trans("agent.option.model.overwrite"),
                        "type": "bool",
                        "default": False,
                    },
                    "prompt": {
                        "type": "textarea",
                        "label": trans("agent.option.prompt"),
                        "description": trans("agent.option.prompt.worker.desc"),
                        "default": WORKER_PROMPT,
                    },
                    "allow_local_tools": {
                        "type": "bool",
                        "label": trans("agent.option.tools.local"),
                        "description": trans("agent.option.tools.local.desc"),
                        "default": True,
                    },
                    "allow_remote_tools": {
                        "type": "bool",
                        "label": trans("agent.option.tools.remote"),
                        "description": trans("agent.option.tools.remote.desc"),
                        "default": True,
                    },
                }
            },
        }
