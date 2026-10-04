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

from typing import Optional, Dict, Any, Union

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.item.ctx import CtxItem

from .preparation import AgentPreparation
from .execution import AgentExecution
from .runners.llama_assistant import LlamaAssistant
from .runners.llama_plan import LlamaPlan
from .runners.llama_steps import LlamaSteps
from .runners.llama_workflow import LlamaWorkflow
from .runners.openai_workflow import OpenAIWorkflow
from .runners.helpers import Helpers
from .runners.loop import Loop


class Runner:
    """Prepare a legacy request, select its execution mode and report errors."""

    APPEND_SYSTEM_PROMPT_TO_MSG = [
        "react",  # llama-index
    ]
    ADDITIONAL_CONTEXT_PREFIX = "ADDITIONAL CONTEXT:"

    def __init__(self, window=None):
        """
        Agent runner

        :param window: Window instance
        """
        self.window = window
        self.helpers = Helpers(window)
        self.loop = Loop(window)
        self.last_error = None  # last exception

        # runners
        self.llama_assistant = LlamaAssistant(window)
        self.llama_plan = LlamaPlan(window)
        self.llama_steps = LlamaSteps(window)
        self.llama_workflow = LlamaWorkflow(window)
        self.openai_workflow = OpenAIWorkflow(window)

        self.preparation = AgentPreparation(
            window, self.APPEND_SYSTEM_PROMPT_TO_MSG, self.ADDITIONAL_CONTEXT_PREFIX)

    # ========================================
    # Agent calls
    # ========================================

    def call(self, context: BridgeContext, extra: Dict[str, Any], signals: BridgeSignals) -> bool:
        """Execute a user-facing agent request."""
        if self.window.controller.kernel.stopped():
            return True
        self.last_error = None
        agent_id = self.window.core.agents.provider.resolve_id(
            extra.get("agent_provider", "llama_agent_base"), context.mode)
        verbose = self.is_verbose()
        execution = AgentExecution(self)
        try:
            prepared = self.preparation.prepare(context, extra, signals, agent_id, verbose)
            return execution.run(prepared)
        except Exception as error:
            execution.fail(error)
            self._record_error(error)
            return False

    def call_once(self, context: BridgeContext, extra: Dict[str, Any],
                  signals: BridgeSignals) -> Union[CtxItem, bool, None]:
        """Execute an invisible expert/evaluation call and return its context."""
        if self.window.controller.kernel.stopped():
            return True
        self.last_error = None
        agent_id = self.window.core.agents.provider.resolve_id(
            extra.get("agent_provider", "llama_agent_base"), context.mode)
        verbose = self.is_verbose()
        try:
            prepared = self.preparation.prepare(context, extra, signals, agent_id, verbose, once=True)
            return AgentExecution(self).run_once(prepared)
        except Exception as error:
            self._record_error(error)

    # ========================================
    # Diagnostics
    # ========================================

    def is_verbose(self) -> bool:
        """
        Check if verbose mode is enabled

        :return: True if verbose mode is enabled
        """
        return self.window.core.config.get("agent.llama.verbose", False)

    def get_error(self) -> Optional[Exception]:
        """
        Get last error

        :return: last exception or None if no error
        """
        return self.last_error

    def _record_error(self, error):
        self.window.core.debug.log(error)
        self.last_error = error
