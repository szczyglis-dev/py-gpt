#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.14 13:00:00                  #
# ================================================== #

import asyncio
from typing import Optional, Dict, Any, Union

from llama_index.core.base.llms.types import ChatMessage, MessageRole

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.types import (
    AGENT_MODE_ASSISTANT,
    AGENT_MODE_PLAN,
    AGENT_MODE_STEP,
    AGENT_MODE_WORKFLOW,
    AGENT_MODE_OPENAI,
)

from pygpt_net.item.ctx import CtxItem

from .runners.llama_assistant import LlamaAssistant
from .runners.llama_plan import LlamaPlan
from .runners.llama_steps import LlamaSteps
from .runners.llama_workflow import LlamaWorkflow
from .runners.openai_workflow import OpenAIWorkflow
from .runners.helpers import Helpers
from .runners.loop import Loop

class Runner:

    APPEND_SYSTEM_PROMPT_TO_MSG = [
        "react",  # llama-index
    ]

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

    def call(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            signals: BridgeSignals
    ) -> bool:
        """
        Call an agent

        :param context: BridgeContext
        :param extra: extra data
        :param signals: BridgeSignals
        :return: True if success
        """
        if self.window.controller.kernel.stopped():
            return True  # abort if stopped

        agent_id = extra.get("agent_provider", "openai")
        verbose = self.window.core.config.get("agent.llama.verbose", False)

        try:
            # prepare input ctx
            ctx = context.ctx
            ctx.extra["agent_input"] = True  # mark as user input
            ctx.agent_call = True  # disables reply from plugin commands
            prompt = context.prompt

            # prepare agent
            model = context.model
            vector_store_idx = extra.get("agent_idx", None)
            system_prompt = context.system_prompt
            preset = context.preset
            max_steps = self.window.core.config.get("agent.llama.steps", 10)
            is_stream = self.window.core.config.get("stream", False)
            is_cmd = self.window.core.command.is_cmd(inline=False)
            history = self.window.core.agents.memory.prepare(context)
            llm = self.window.core.idx.llm.get(model, stream=False)
            workdir = self.window.core.config.get_workdir_prefix()

            # vector store idx from preset
            if preset:
                vector_store_idx = preset.idx

            # tools
            self.window.core.agents.tools.context = context
            self.window.core.agents.tools.agent_idx = vector_store_idx

            tools = self.window.core.agents.tools.prepare(context, extra, force=True)
            function_tools = self.window.core.agents.tools.get_function_tools(ctx, extra, force=True)
            plugin_tools = self.window.core.agents.tools.get_plugin_tools(context, extra, force=True)
            plugin_specs = self.window.core.agents.tools.get_plugin_specs(context, extra, force=True)
            retriever_tool = self.window.core.agents.tools.get_retriever_tool(context, extra)

            # disable tools if cmd is not enabled
            if not is_cmd:
                function_tools = []
                plugin_tools = []
                plugin_specs = []
                tools = []
            
            # append system prompt
            if agent_id in self.APPEND_SYSTEM_PROMPT_TO_MSG:
                if system_prompt:
                    msg = ChatMessage(
                        role=MessageRole.SYSTEM,
                        content=system_prompt,
                    )
                    history.insert(0, msg)

            agent_kwargs = {
                "context": context,
                "tools": tools,
                "function_tools": function_tools,
                "plugin_tools": plugin_tools,
                "plugin_specs": plugin_specs,
                "retriever_tool": retriever_tool,
                "llm": llm,
                "model": model,
                "chat_history": history,
                "max_iterations": max_steps,
                "verbose": verbose,
                "system_prompt": system_prompt,
                "are_commands": is_cmd,
                "workdir": workdir,
                "preset": context.preset if context else None,
            }

            if self.window.core.agents.provider.has(agent_id):
                provider = self.window.core.agents.provider.get(agent_id)
                agent = provider.get_agent(self.window, agent_kwargs)
                agent_run = provider.run
                if verbose:
                    print("Using Agent: " + str(agent_id) + ", model: " + str(model.id))
            else:
                raise Exception("Agent not found: " + str(agent_id))

            # run agent
            mode = provider.get_mode()
            kwargs = {
                "agent": agent,
                "ctx": ctx,
                "prompt": prompt,
                "signals": signals,
                "verbose": verbose,
            }

            if mode == AGENT_MODE_PLAN:
                return self.llama_plan.run(**kwargs)
            elif mode == AGENT_MODE_STEP:
                return self.llama_steps.run(**kwargs)
            elif mode == AGENT_MODE_ASSISTANT:
                return self.llama_assistant.run(**kwargs)
            elif mode == AGENT_MODE_WORKFLOW:
                kwargs["history"] = history
                kwargs["llm"] = llm
                return asyncio.run(self.llama_workflow.run(**kwargs))
            elif mode == AGENT_MODE_OPENAI:
                kwargs["run"] = agent_run  # callable
                kwargs["agent_kwargs"] = agent_kwargs  # as dict
                kwargs["stream"] = is_stream # from global
                return asyncio.run(self.openai_workflow.run(**kwargs))

        except Exception as e:
            print("Error in agent runner:", e)
            self.window.core.debug.error(e)
            self.last_error = e
            return False

    def call_once(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            signals: BridgeSignals
    ) -> Union[CtxItem, bool, None]:
        """
        Call an agent once (quick call to the agent)

        :param context: BridgeContext
        :param extra: extra data
        :param signals: BridgeSignals
        :return: CtxItem if success, True if stopped, None on error
        """
        if self.window.controller.kernel.stopped():
            return True  # abort if stopped

        agent_id = extra.get("agent_provider", "openai")
        verbose = self.window.core.config.get("agent.llama.verbose", False)

        try:
            # prepare input ctx
            ctx = context.ctx
            ctx.extra["agent_input"] = True  # mark as user input
            ctx.extra["agent_output"] = True  # mark as user input
            ctx.agent_call = True  # disables reply from plugin commands
            prompt = context.prompt

            # prepare agent
            model = context.model
            vector_store_idx = extra.get("agent_idx", None)
            system_prompt = context.system_prompt
            max_steps = self.window.core.config.get("agent.llama.steps", 10)
            is_cmd = self.window.core.command.is_cmd(inline=False)
            llm = self.window.core.idx.llm.get(model, stream=False)
            workdir = self.window.core.config.get_workdir_prefix()

            # tools
            self.window.core.agents.tools.context = context
            self.window.core.agents.tools.agent_idx = vector_store_idx

            if "agent_tools" in extra:
                tools = extra["agent_tools"]  # use tools from extra if provided
            else:
                tools = self.window.core.agents.tools.prepare(context, extra, force=True)

            if "agent_history" in extra:
                history = extra["agent_history"]
            else:
                history = self.window.core.agents.memory.prepare(context)

            # disable tools if cmd is not enabled
            if not is_cmd:
                tools = []

            # append system prompt
            if agent_id in self.APPEND_SYSTEM_PROMPT_TO_MSG:
                if system_prompt:
                    msg = ChatMessage(
                        role=MessageRole.SYSTEM,
                        content=system_prompt,
                    )
                    history.insert(0, msg)

            agent_kwargs = {
                "context": context,
                "tools": tools,
                "llm": llm,
                "model": model,
                "chat_history": history,
                "max_iterations": max_steps,
                "verbose": verbose,
                "system_prompt": system_prompt,
                "are_commands": is_cmd,
                "workdir": workdir,
                "preset": context.preset if context else None,
            }

            if self.window.core.agents.provider.has(agent_id):
                provider = self.window.core.agents.provider.get(agent_id)
                agent = provider.get_agent(self.window, agent_kwargs)
                if verbose:
                    print("Using Agent: " + str(agent_id) + ", model: " + str(model.id))
            else:
                raise Exception("Agent not found: " + str(agent_id))

            # run agent and return result
            mode = provider.get_mode()
            kwargs = {
                "agent": agent,
                "ctx": ctx,
                "prompt": prompt,
                "signals": signals,
                "verbose": verbose,
                "history": history,
                "llm": llm,
            }
            # TODO: add support for other modes
            if mode == AGENT_MODE_WORKFLOW:
                return asyncio.run(self.llama_workflow.run_once(**kwargs))

        except Exception as e:
            self.window.core.debug.error(e)
            self.last_error = e
            return None

    def get_error(self) -> Optional[Exception]:
        """
        Get last error

        :return: last exception or None if no error
        """
        return self.last_error
