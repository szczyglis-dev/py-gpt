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

import json
import re
from typing import Dict, Any, Tuple, Optional

from agents import (
    Agent as OpenAIAgent,
    Runner,
    RunContextWrapper,
    SQLiteSession,
    function_tool,
)

from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import (
    AGENT_MODE_OPENAI,
    AGENT_TYPE_OPENAI,
)

from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem

from pygpt_net.provider.gpt.agents.remote_tools import append_tools
from pygpt_net.provider.gpt.agents.response import StreamHandler
from pygpt_net.provider.gpt.agents.experts import get_experts
from pygpt_net.utils import trans

from ..base import BaseAgent

JSON_RE = re.compile(r"\{[\s\S]*\}$", re.MULTILINE)

SUPERVISOR_PROMPT = """
    You are the “Supervisor” (orchestrator). You never use tools directly except the tool that runs the Worker.
    Process:
    - Decompose the user's task into actionable instructions for the Worker.
    - Do NOT pass your conversation history to the Worker. Pass ONLY a concise, self-contained instruction.
    - After each Worker result, evaluate against a clear Definition of Done (DoD). If not met, call the Worker again with a refined instruction.
    - Ask the user only if absolutely necessary. If you must, STOP and output a single JSON with:
    {"action":"ask_user","question":"...","reasoning":"..."}
    - When done, output a single JSON:
    {"action":"final","final_answer":"...","reasoning":"..."}
    - Otherwise, to run the Worker, call the run_worker tool with a short instruction.
    Respond in the user's language. Keep outputs short and precise.
    """

WORKER_PROMPT = """
You are the “Worker”. You execute Supervisor instructions strictly, using your tools.
- Keep your own memory across calls (Worker session).
- Return a concise result with key evidence/extracts from tools when applicable.
- Do not ask the user questions directly; if instruction is underspecified, clearly state what is missing.
Respond in the user's language.
"""

class Agent(BaseAgent):

    def __init__(self, *args, **kwargs):
        super(Agent, self).__init__(*args, **kwargs)
        self.id = "openai_agent_supervisor"
        self.type = AGENT_TYPE_OPENAI
        self.mode = AGENT_MODE_OPENAI
        self.name = "Supervisor + worker"

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Return Agent supervisor instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent instance
        """
        context = kwargs.get("context", BridgeContext())
        preset = context.preset
        agent_name = preset.name if preset else "Supervisor"
        model = kwargs.get("model", ModelItem())
        worker_tool = kwargs.get("worker_tool", None)
        kwargs = {
            "name": agent_name,
            "instructions": self.get_option(preset, "supervisor", "prompt"),
            "model": window.core.agents.provider.get_openai_model(model)
        }
        if worker_tool:
            kwargs["tools"] = [worker_tool]
        return OpenAIAgent(**kwargs)

    def get_worker(self, window, kwargs: Dict[str, Any]):
        """
        Return Agent worker instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent instance
        """
        context = kwargs.get("context", BridgeContext())
        preset = context.preset
        agent_name = "Worker"  # Default worker name
        tools = kwargs.get("function_tools", [])
        model = window.core.models.get(
            self.get_option(preset, "worker", "model")
        )
        handoffs = kwargs.get("handoffs", [])
        kwargs = {
            "name": agent_name,
            "instructions": self.get_option(preset, "worker", "prompt"),
            "model": window.core.agents.provider.get_openai_model(model)
        }
        if handoffs:
            kwargs["handoffs"] = handoffs

        tool_kwargs = append_tools(
            tools=tools,
            window=window,
            model=model,
            preset=preset,
            allow_local_tools=self.get_option(preset, "worker", "allow_local_tools"),
            allow_remote_tools= self.get_option(preset, "worker", "allow_remote_tools"),
        )
        kwargs.update(tool_kwargs) # update kwargs with tools
        return OpenAIAgent(**kwargs)

    async def run(
            self,
            window: Any = None,
            agent_kwargs: Dict[str, Any] = None,
            previous_response_id: str = None,
            messages: list = None,
            ctx: CtxItem = None,
            stream: bool = False,
            bridge: ConnectionContext = None,
            use_partial_ctx: Optional[bool] = False,
    ) -> Tuple[CtxItem, str, str]:
        """
        Run agent (async)

        :param window: Window instance
        :param agent_kwargs: Additional agent parameters
        :param previous_response_id: ID of the previous response (if any)
        :param messages: Conversation messages
        :param ctx: Context item
        :param stream: Whether to stream output
        :param bridge: Connection context for agent operations
        :param use_partial_ctx: Use partial ctx per cycle
        :return: Current ctx, final output, last response ID
        """
        final_output = ""
        response_id = None
        model = agent_kwargs.get("model", ModelItem())
        verbose = agent_kwargs.get("verbose", False)
        tools = agent_kwargs.get("function_tools", [])
        context = agent_kwargs.get("context", BridgeContext())
        preset = context.preset if context else None

        # add experts
        experts = get_experts(
            window=window,
            preset=preset,
            verbose=verbose,
            tools=tools,
        )
        if experts:
            agent_kwargs["handoffs"] = experts

        worker = self.get_worker(window, agent_kwargs)
        max_steps = agent_kwargs.get("max_iterations", 10)
        kwargs = {
            "input": messages,
            "max_turns": int(max_steps),
        }
        if model.provider == "openai":
            if previous_response_id:
                kwargs["previous_response_id"] = previous_response_id

        # temp worker memory
        worker_session_id = f"worker_session_{ctx.meta.id}" if ctx.meta else "worker_session_default"
        worker_session = SQLiteSession(worker_session_id)

        handler = StreamHandler(window, bridge)
        item_ctx = ctx

        # tool to run Worker
        @function_tool(name_override="run_worker")
        async def run_worker(ctx: RunContextWrapper[Any], instruction: str) -> str:
            """
            Run the Worker with an instruction from the Supervisor and return its output.

            :param ctx: Run context wrapper
            :param instruction: Instruction for the Worker
            :return: Output from the Worker
            """
            item_ctx.stream = f"\n\n**{trans('agent.name.supervisor')} --> {trans('agent.name.worker')}:** {instruction}\n\n"
            bridge.on_step(item_ctx, True)
            handler.begin = False
            result = await Runner.run(
                worker,
                input=instruction,
                session=worker_session,
                max_turns=max_steps,
            )
            item_ctx.stream = f"\n\n{result.final_output}\n\n"
            bridge.on_step(item_ctx, False)
            return str(result.final_output)

        agent_kwargs["worker_tool"] = run_worker
        agent = self.get_agent(window, agent_kwargs)

        if not stream:
            result = await Runner.run(
                agent,
                **kwargs
            )
            final_output, last_response_id = window.core.gpt.responses.unpack_agent_response(result, ctx)
            response_id = result.last_response_id
            if verbose:
                print("Final response:", result)
        else:
            result = Runner.run_streamed(
                agent,
                **kwargs
            )
            async for event in result.stream_events():
                if bridge.stopped():
                    result.cancel()
                    bridge.on_stop(ctx)
                    break
                final_output, response_id = handler.handle(event, ctx)

        # extract final output from JSON
        if final_output:
            final_output = self.extract_final_response(final_output)
            if verbose:
                print("Final output after extraction:", final_output)

        return ctx, final_output, response_id

    def extract_final_response(self, output: str) -> str:
        """
        Extract final response from the output string.

        :param output: Output string from the agent
        :return: Final response string
        """
        if not output:
            return ""

        fence = re.search(r"```json\s*([\s\S]*?)\s*```", output, re.IGNORECASE)
        if fence:
            try:
                # Try to parse the fenced JSON
                json_text = fence.group(1).strip()
                json_response = json.loads(json_text)
                return self.response_from_json(json_response)
            except Exception:
                pass

        tail = JSON_RE.findall(output)
        for candidate in tail[::-1]:
            try:
                # Try to parse the JSON from the tail
                json_response = json.loads(candidate)
                return self.response_from_json(json_response)
            except Exception:
                continue

        if output.startswith("{") and output.endswith("}"):
            try:
                # Try to parse the entire output as JSON
                response = json.loads(output)
                return self.response_from_json(response)
            except Exception as e:
                print(f"Error parsing JSON: {e}")
                return output

        return output.strip()

    def response_from_json(self, response: dict) -> str:
        """
        Extract response from JSON format

        :param response: JSON response from the agent
        :return: str: Formatted response string
        """
        action = response.get("action", "")
        if action == "ask_user":
            question = response.get("question", "")
            reasoning = response.get("reasoning", "")
            return f"**{trans('agent.name.supervisor')}:** {reasoning}\n\n{question}"
        elif action == "final":
            final_answer = response.get("final_answer", "")
            reasoning = response.get("reasoning", "")
            return f"**{trans('agent.name.supervisor')}:** {reasoning}\n\n{final_answer}\n\n"
        else:
            return response.get("final_answer", "")

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




