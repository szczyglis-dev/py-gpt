#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.01 19:00:00                  #
# ================================================== #

from dataclasses import dataclass
from typing import Dict, Any, Tuple, Literal

from agents import (
    Agent as OpenAIAgent,
    Runner,
    RunConfig,
    ModelSettings,
    TResponseInputItem,
)

from pygpt_net.core.agents.bridge import ConnectionContext
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import (
    AGENT_MODE_OPENAI,
    AGENT_TYPE_OPENAI,
)

from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem

from pygpt_net.provider.gpt.agents.client import get_custom_model_provider, set_openai_env
from pygpt_net.provider.gpt.agents.remote_tools import get_remote_tools, is_computer_tool, append_tools
from pygpt_net.provider.gpt.agents.response import StreamHandler

from ..base import BaseAgent

@dataclass
class EvaluationFeedback:
    feedback: str
    score: Literal["pass", "needs_improvement", "fail"]

class Agent(BaseAgent):

    PROMPT = (
        "You generate a response based on the user's input. "
        "If there is any feedback provided, use it to improve the response."
    )

    PROMPT_FEEDBACK = (
        "You evaluate a result and decide if it's good enough. "
        "If it's not good enough, you provide feedback on what needs to be improved. "
        "Never give it a pass on the first try. After 5 attempts, "
        "you can give it a pass if the result is good enough - do not go for perfection."
    )

    def __init__(self, *args, **kwargs):
        super(Agent, self).__init__(*args, **kwargs)
        self.id = "openai_agent_feedback"
        self.type = AGENT_TYPE_OPENAI
        self.mode = AGENT_MODE_OPENAI
        self.name = "Agent with feedback"

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Return Agent provider instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent provider instance
        """
        context = kwargs.get("context", BridgeContext())
        preset = context.preset
        agent_name = preset.name if preset else "Agent"
        model = kwargs.get("model", ModelItem())
        tools = kwargs.get("function_tools", [])
        kwargs = {
            "name": agent_name,
            "instructions": self.get_option(preset, "base", "prompt"),
            "model": model.id,
        }
        tool_kwargs = append_tools(
            tools=tools,
            window=window,
            model=model,
            preset=preset,
            allow_local_tools=self.get_option(preset, "base", "allow_local_tools"),
            allow_remote_tools= self.get_option(preset, "base", "allow_remote_tools"),
        )
        kwargs.update(tool_kwargs) # update kwargs with tools
        return OpenAIAgent(**kwargs)

    def get_evaluator(
            self,
            window,
            model: ModelItem,
            instructions: str,
            preset: PresetItem,
            tools: list,
            allow_local_tools: bool = False,
            allow_remote_tools: bool = False,
    ) -> OpenAIAgent:
        """
        Return Agent provider instance

        :param window: window instance
        :param model: Model item for the evaluator agent
        :param instructions: Instructions for the evaluator agent
        :param preset: Preset item for additional context
        :param tools: List of function tools to use
        :param allow_local_tools: Whether to allow local tools
        :param allow_remote_tools: Whether to allow remote tools
        :return: Agent provider instance
        """
        kwargs = {
            "name": "evaluator",
            "instructions": instructions,
            "model": model.id,
            "output_type": EvaluationFeedback,
        }
        tool_kwargs = append_tools(
            tools=tools,
            window=window,
            model=model,
            preset=preset,
            allow_local_tools=allow_local_tools,
            allow_remote_tools=allow_remote_tools,
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
    ) -> Tuple[CtxItem, str, str]:
        """
        Run agent (async)

        :param window: Window instance
        :param agent_kwargs: Additional agent parameters
        :param previous_response_id: ID of the previous response (if any)
        :param messages: Conversation messages
        :param ctx: Context item
        :param stream: Whether to stream output
        :param bridge: Connection context for handling stop and step events
        :return: Current ctx, final output, last response ID
        """
        final_output = ""
        response_id = None
        model = agent_kwargs.get("model", ModelItem())
        verbose = agent_kwargs.get("verbose", False)
        context = agent_kwargs.get("context", BridgeContext())
        max_steps = agent_kwargs.get("max_iterations", 10)
        tools = agent_kwargs.get("function_tools", [])
        preset = context.preset

        agent = self.get_agent(window, agent_kwargs)

        # get options
        feedback_instructions = self.get_option(preset, "feedback", "prompt")
        feedback_model = self.get_option(preset, "feedback", "model")
        feedback_allow_local_tools = self.get_option(preset, "feedback", "allow_local_tools")
        feedback_allow_remote_tools = self.get_option(preset, "feedback", "allow_remote_tools")

        kwargs = {
            "input": messages,
            "max_turns": int(max_steps),
        }
        if model.provider != "openai":
            custom_provider = get_custom_model_provider(window, model)
            kwargs["run_config"] = RunConfig(model_provider=custom_provider)
        else:
            set_openai_env(window)
            if previous_response_id:
                kwargs["previous_response_id"] = previous_response_id

        model_eval = window.core.models.get(feedback_model)
        evaluator = self.get_evaluator(
            window=window,
            model=model_eval,
            instructions=feedback_instructions,
            preset=preset,
            tools=tools,
            allow_local_tools=feedback_allow_local_tools,
            allow_remote_tools=feedback_allow_remote_tools,
        )
        input_items: list[TResponseInputItem] = messages
        if not stream:
            while True:
                kwargs["input"] = input_items
                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                result = await Runner.run(
                    agent,
                    **kwargs
                )
                response_id = result.last_response_id
                if verbose:
                    print("Final response:", result)

                input_items = result.to_input_list()
                final_output, last_response_id = window.core.gpt.responses.unpack_agent_response(result, ctx)

                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                evaluator_result = await Runner.run(evaluator, input_items)
                result: EvaluationFeedback = evaluator_result.final_output

                print(f"Evaluator score: {result.score}")
                if result.score == "pass":
                    print("Response is good enough, exiting.")
                    break
                print("Re-running with feedback")
                input_items.append({"content": f"Feedback: {result.feedback}", "role": "user"})
        else:
            handler = StreamHandler(window, bridge)
            while True:
                kwargs["input"] = input_items
                result = Runner.run_streamed(
                    agent,
                    **kwargs
                )
                handler.reset()
                async for event in result.stream_events():
                    if bridge.stopped():
                        bridge.on_stop(ctx)
                        break
                    final_output, response_id = handler.handle(event, ctx)

                bridge.on_next(ctx)
                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                input_items = result.to_input_list()
                evaluator_result = await Runner.run(evaluator, input_items)
                result: EvaluationFeedback = evaluator_result.final_output

                info = f"\n___\n**Evaluator score: {result.score}**\n\n"
                if result.score == "pass":
                    info += "\n\n**Response is good enough, exiting.**\n"
                    ctx.stream = info
                    bridge.on_step(ctx, False)
                    final_output += info
                    break

                info += "\n\n**Re-running with feedback**\n\n" + f"Feedback: {result.feedback}\n___\n"
                ctx.stream = info
                bridge.on_step(ctx, False)
                input_items.append({"content": f"Feedback: {result.feedback}", "role": "user"})
                handler.to_buffer(info)

        return ctx, final_output, response_id


    def get_options(self) -> Dict[str, Any]:
        """
        Return Agent options

        :return: dict of options
        """
        return {
            "base": {
                "label": "Base agent",
                "options": {
                    "prompt": {
                        "type": "textarea",
                        "label": "Prompt",
                        "description": "Prompt for base agent",
                        "default": self.PROMPT,
                    },
                    "allow_local_tools": {
                        "type": "bool",
                        "label": "Allow local tools",
                        "description": "Allow usage of local tools for this agent",
                        "default": False,
                    },
                    "allow_remote_tools": {
                        "type": "bool",
                        "label": "Allow remote tools",
                        "description": "Allow usage of remote tools for this agent",
                        "default": False,
                    },
                }
            },
            "feedback": {
                "label": "Feedback",
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
                        "description": "Prompt for feedback evaluation",
                        "default": self.PROMPT_FEEDBACK,
                    },
                    "allow_local_tools": {
                        "type": "bool",
                        "label": "Allow local tools",
                        "description": "Allow usage of local tools for this agent",
                        "default": False,
                    },
                    "allow_remote_tools": {
                        "type": "bool",
                        "label": "Allow remote tools",
                        "description": "Allow usage of remote tools for this agent",
                        "default": False,
                    },
                }
            },
        }


