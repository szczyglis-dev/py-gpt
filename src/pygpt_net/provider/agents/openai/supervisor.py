#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.27 20:25:00                  #
# ================================================== #
from __future__ import annotations
import json
import re
from typing import Dict, Any, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agents import RunContextWrapper

from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import (
    AGENT_MODE_OPENAI,
    AGENT_TYPE_OPENAI,
)

from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem

from pygpt_net.utils import trans

from ..base import BaseAgent

# OpenAI response event types (used by StreamHandler)

JSON_RE = re.compile(r"\{[\s\S]*\}$", re.MULTILINE)

SUPERVISOR_PROMPT = """
    You are the “Supervisor” (orchestrator). You may use your own enabled tools when useful, and you can delegate execution to the Worker through the run_worker tool.
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




__all__ = ["Agent", "SupervisorStreamHandler"]

class Agent(BaseAgent):

    def __init__(self, *args, **kwargs):
        super(Agent, self).__init__(*args, **kwargs)
        self.id = "openai_agent_supervisor"
        self.type = AGENT_TYPE_OPENAI
        self.mode = AGENT_MODE_OPENAI
        self.name = "Supervisor"  # use clean name in UI headers

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Return Agent supervisor instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent instance
        """
        from agents import Agent as OpenAIAgent
        from pygpt_net.provider.api.openai.agents.client import append_reasoning_model_settings
        from pygpt_net.provider.api.openai.agents.remote_tools import append_tools

        context = kwargs.get("context", BridgeContext())
        preset = context.preset
        model = kwargs.get("model", ModelItem())

        # Enforce a stable, clean display name for the Supervisor regardless of preset name.
        agent_name = "Supervisor"  # hard-coded UI name

        worker_tool = kwargs.get("worker_tool", None)
        tools = kwargs.get("function_tools", [])
        instructions = self.append_system_prompt_extra(
            self.get_option(preset, "supervisor", "prompt"),
            kwargs,
        )
        kwargs = {
            "name": agent_name,
            "instructions": instructions,
            "model": window.core.agents.provider.get_openai_model(model)
        }

        # Supervisor may optionally use the same local/provider-native tools as
        # other agents. The internal run_worker tool is orchestration plumbing,
        # not a user tool, so it is always appended independently of these flags.
        tool_kwargs = append_tools(
            tools=tools,
            window=window,
            model=model,
            preset=preset,
            allow_local_tools=bool(self.get_option(preset, "supervisor", "allow_local_tools")),
            allow_remote_tools=bool(self.get_option(preset, "supervisor", "allow_remote_tools")),
        )
        kwargs.update(tool_kwargs)
        if worker_tool:
            kwargs.setdefault("tools", [])
            kwargs["tools"] = list(kwargs["tools"]) + [worker_tool]

        append_reasoning_model_settings(kwargs, window, model)
        return OpenAIAgent(**kwargs)

    def get_worker(self, window, kwargs: Dict[str, Any]):
        """
        Return Agent worker instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent instance
        """
        from agents import Agent as OpenAIAgent
        from pygpt_net.provider.api.openai.agents.client import append_reasoning_model_settings
        from pygpt_net.provider.api.openai.agents.remote_tools import append_tools

        context = kwargs.get("context", BridgeContext())
        preset = context.preset
        agent_name = "Worker"  # Default worker name
        tools = kwargs.get("function_tools", [])
        model = self.resolve_model_option(
            window,
            preset,
            "worker",
            kwargs.get("model"),
        )

        if model is None or not getattr(model, "id", None):
            current_model_id = window.core.config.get("model")
            model = window.core.models.get(current_model_id) if current_model_id else None

        handoffs = kwargs.get("handoffs", [])
        instructions = self.append_system_prompt_extra(
            self.get_option(preset, "worker", "prompt"),
            kwargs,
        )
        kwargs = {
            "name": agent_name,
            "instructions": instructions,
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
        append_reasoning_model_settings(kwargs, window, model)
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
        from agents import Runner, RunContextWrapper, SQLiteSession, function_tool
        from pygpt_net.provider.api.openai.agents.experts import get_experts
        from .supervisor_stream import SupervisorStreamHandler

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
            system_prompt_extra=self.get_system_prompt_extra(agent_kwargs),
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

        # Use JSON-filtering handler for Supervisor streaming
        handler = SupervisorStreamHandler(
            window,
            bridge,
            json_to_text=self.response_from_json,
        )
        item_ctx = ctx  # will reassign on splits

        supervisor_display_name = None  # set after agent is created

        # tool to run Worker
        async def run_worker(fn_ctx, instruction: str) -> str:
            """
            Run the Worker with an instruction from the Supervisor and return its output.

            - Appends the instruction to the current Supervisor block.
            - Finalizes the Supervisor block and opens a new Worker block.
            - Runs the Worker and streams its result into the Worker block.
            - Finalizes the Worker block, then opens a fresh block for the Supervisor to continue.
            """
            nonlocal item_ctx, supervisor_display_name

            info = f"\n\n**{trans('agent.name.supervisor')} → {trans('agent.name.worker')}:** {instruction}\n\n"
            item_ctx.stream = info
            bridge.on_step(item_ctx, True)
            handler.to_buffer(info)

            if use_partial_ctx:
                item_ctx = bridge.on_next_ctx(
                    ctx=item_ctx,
                    input="",
                    output=handler.buffer,  # finalize current Supervisor content
                    response_id=handler.response_id or "",
                    stream=True,
                )
                handler.new()  # reset handler buffer for next block

            try:
                item_ctx.set_agent_name(worker.name)
            except Exception:
                pass

            result = await Runner.run(
                worker,
                input=instruction,
                session=worker_session,
                max_turns=max_steps,
            )

            worker_text = str(result.final_output or "")
            if worker_text:
                item_ctx.stream = f"{worker_text}\n"
                bridge.on_step(item_ctx, True)

            if use_partial_ctx:
                item_ctx = bridge.on_next_ctx(
                    ctx=item_ctx,
                    input="",
                    output=worker_text,  # finalize worker output
                    response_id="",      # worker has no OpenAI response id here
                    stream=True,
                )
                try:
                    if supervisor_display_name:
                        item_ctx.set_agent_name(supervisor_display_name)
                except Exception:
                    pass

            return worker_text

        # ``function_tool`` resolves annotations with typing.get_type_hints(),
        # which only sees function globals. RunContextWrapper is intentionally
        # imported locally so the Agents SDK remains optional at module import
        # time; attach the concrete annotation before decorating the callback.
        run_worker.__annotations__["fn_ctx"] = RunContextWrapper[Any]
        run_worker = function_tool(name_override="run_worker")(run_worker)

        agent_kwargs["worker_tool"] = run_worker
        agent = self.get_agent(window, agent_kwargs)
        supervisor_display_name = agent.name  # "Supervisor"

        if not stream:
            item_ctx.set_agent_name(agent.name)
            result = await Runner.run(agent, **kwargs)
            final_output, last_response_id = window.core.api.openai.responses.unpack_agent_response(result, item_ctx)
            response_id = result.last_response_id
            if verbose:
                print("Final response:", result)
        else:
            item_ctx.set_agent_name(agent.name)
            result = Runner.run_streamed(agent, **kwargs)
            async for event in result.stream_events():
                if bridge.stopped():
                    result.cancel()
                    bridge.on_stop(item_ctx)
                    break
                # Write into current item_ctx (it changes when we split)
                final_output, response_id = handler.handle(event, item_ctx)

        # extract final output from JSON (Supervisor's last block)
        if final_output:
            final_output = self.extract_final_response(final_output)
            if verbose:
                print("Final output after extraction:", final_output)

        # Properly finalize last block
        if use_partial_ctx:
            item_ctx = bridge.on_next_ctx(
                ctx=item_ctx,
                input=final_output or "",
                output=final_output or "",
                response_id=response_id or "",
                finish=True,
                stream=stream,
            )

        return item_ctx, final_output, response_id

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
                json_text = fence.group(1).strip()
                json_response = json.loads(json_text)
                return self.response_from_json(json_response)
            except Exception:
                pass

        tail = JSON_RE.findall(output)
        for candidate in tail[::-1]:
            try:
                json_response = json.loads(candidate)
                return self.response_from_json(json_response)
            except Exception:
                continue

        if output.startswith("{") and output.endswith("}"):
            try:
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

def __getattr__(name):
    # Backward-compatible lazy export; avoids importing the Agents SDK at startup.
    if name == "SupervisorStreamHandler":
        from .supervisor_stream import SupervisorStreamHandler
        return SupervisorStreamHandler
    raise AttributeError(name)

