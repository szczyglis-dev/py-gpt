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

from dataclasses import dataclass
from typing import Dict, Any, Tuple, Literal, Optional

from agents import (
    Agent as OpenAIAgent,
    Runner,
    RunConfig,
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

from pygpt_net.provider.api.openai.agents.client import get_custom_model_provider, set_openai_env
from pygpt_net.provider.api.openai.agents.remote_tools import append_tools
from pygpt_net.provider.api.openai.agents.response import StreamHandler
from pygpt_net.provider.api.openai.agents.experts import get_experts
from pygpt_net.utils import trans

from ..base import BaseAgent

@dataclass
class EvaluationFeedback:
    feedback: str
    score: Literal["pass", "needs_improvement", "fail"]

@dataclass
class StructuredPlan:
    plan: str

class Agent(BaseAgent):

    PROMPT_PLANNER = """
        Make a plan of task execution for the query by dividing a task into smaller steps. 
        Do not provide any solutions here. The plan should only contain a list of steps as instructions 
        for someone else to follow. 
        Prepare a plan in the language in which the query was made. 
        Format the plan using markdown.
        
        Example:
        --------
                
        **Sub-task 1: <name 1>**
        
        - Description: <subtask description 1>
        - Expected output: <expected output 1>
        - Dependencies: []
        - Required Tools: []
        
        **Sub-task 2: <name 2>**
        
        - Description: <subtask description 2>
        - Expected output: <expected output 2>
        - Dependencies: [<name 1>]
        - Required Tools: [WebSearch]
        
        ...
    """

    PROMPT = (
        "Prepare a comprehensive and detailed response to the question based on the action plan. "
        "Follow each step outlined in the plan. "
        "If any feedback is provided, use it to improve the response."
    )

    PROMPT_FEEDBACK = (
        "You evaluate a result and decide if it's good enough. "
        "If it's not good enough, you provide feedback on what needs to be improved. "
        "Never give it a pass on the first try. After 5 attempts, "
        "you can give it a pass if the result is good enough - do not go for perfection, "
        "but ensure all tasks are completed."
    )

    def __init__(self, *args, **kwargs):
        super(Agent, self).__init__(*args, **kwargs)
        self.id = "openai_agent_planner"
        self.type = AGENT_TYPE_OPENAI
        self.mode = AGENT_MODE_OPENAI
        self.name = "Planner"

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
        handoffs = kwargs.get("handoffs", [])
        kwargs = {
            "name": agent_name,
            "instructions": self.get_option(preset, "base", "prompt"),
            "model": window.core.agents.provider.get_openai_model(model),
        }
        if handoffs:
            kwargs["handoffs"] = handoffs

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
            "model": window.core.agents.provider.get_openai_model(model),
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

    def get_planner(
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
            "name": "StructuredPlanner",
            "instructions": instructions,
            "model": window.core.agents.provider.get_openai_model(model),
            "output_type": StructuredPlan,
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
        :param bridge: Connection context for handling stop and step events
        :param use_partial_ctx: Use partial ctx per cycle
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

        # add experts
        experts = get_experts(
            window=window,
            preset=preset,
            verbose=verbose,
            tools=tools,
        )
        if experts:
            agent_kwargs["handoffs"] = experts

        agent = self.get_agent(window, agent_kwargs)

        # get options
        planner_instructions = self.get_option(preset, "planner", "prompt")
        planner_model = self.get_option(preset, "planner", "model")
        planner_allow_local_tools = self.get_option(preset, "planner", "allow_local_tools")
        planner_allow_remote_tools = self.get_option(preset, "planner", "allow_remote_tools")

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

        model_planner = window.core.models.get(planner_model)
        planner = self.get_planner(
            window=window,
            model=model_planner,
            instructions=planner_instructions,
            preset=preset,
            tools=tools,
            allow_local_tools=planner_allow_local_tools,
            allow_remote_tools=planner_allow_remote_tools,
        )

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
        query = messages[-1]["content"] if messages else ""
        messages[-1]["content"] = f"Query: {query}\n\n"

        # run planner first
        planner_result = await Runner.run(planner, input_items)
        result: StructuredPlan = planner_result.final_output

        ctx.stream = f"**Plan:**\n {result.plan}\n\n"
        bridge.on_step(ctx, True)

        input_items.append({"content": f"Query: {query}\n\nPlan: {result.plan}", "role": "user"})

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
                    if use_partial_ctx:
                        ctx = bridge.on_next_ctx(
                            ctx=ctx,
                            input=result.feedback,  # new ctx: input
                            output=final_output,  # prev ctx: output
                            response_id=response_id,
                            finish=True,
                            stream=False,
                        )
                    else:
                        print("Response is good enough, exiting.")
                    break

                print("Re-running with feedback")
                input_items.append({"content": f"Feedback: {result.feedback}", "role": "user"})

                if use_partial_ctx:
                    ctx = bridge.on_next_ctx(
                        ctx=ctx,
                        input=result.feedback,  # new ctx: input
                        output=final_output,  # prev ctx: output
                        response_id=response_id,
                        stream=False,
                    )
        else:
            final_output = result.plan + "\n___\n"
            handler = StreamHandler(window, bridge, final_output)
            while True:
                kwargs["input"] = input_items
                result = Runner.run_streamed(
                    agent,
                    **kwargs
                )
                handler.reset()
                async for event in result.stream_events():
                    if bridge.stopped():
                        result.cancel()
                        bridge.on_stop(ctx)
                        break
                    final_output, response_id = handler.handle(event, ctx)

                if not use_partial_ctx:
                    bridge.on_next(ctx)

                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                input_items = result.to_input_list()
                evaluator_result = await Runner.run(evaluator, input_items)
                result: EvaluationFeedback = evaluator_result.final_output

                info = f"\n___\n**{trans('agent.eval.score')}: {result.score}**\n\n"
                if result.score == "pass":
                    info += f"\n\n**{trans('agent.eval.score.good')}**\n"
                    if use_partial_ctx:
                        ctx = bridge.on_next_ctx(
                            ctx=ctx,
                            input=result.feedback,  # new ctx: input
                            output=final_output,  # prev ctx: output
                            response_id=response_id,
                            finish=True,
                            stream=True,
                        )
                    else:
                        ctx.stream = info
                        bridge.on_step(ctx, False)
                        final_output += info
                    break

                info += f"\n\n**{trans('agent.eval.next')}**\n\nFeedback: {result.feedback}\n___\n"
                input_items.append({"content": f"Feedback: {result.feedback}", "role": "user"})

                if use_partial_ctx:
                    ctx = bridge.on_next_ctx(
                        ctx=ctx,
                        input=result.feedback,  # new ctx: input
                        output=final_output,  # prev ctx: output
                        response_id=response_id,
                        stream=True,
                    )
                    handler.new()
                else:
                    ctx.stream = info
                    bridge.on_step(ctx, False)
                    handler.to_buffer(info)

        return ctx, final_output, response_id


    def get_options(self) -> Dict[str, Any]:
        """
        Return Agent options

        :return: dict of options
        """
        return {
            "base": {
                "label": trans("agent.option.section.base"),
                "options": {
                    "prompt": {
                        "type": "textarea",
                        "label": trans("agent.option.prompt"),
                        "description": trans("agent.option.prompt.base.desc"),
                        "default": self.PROMPT,
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
            "planner": {
                "label": trans("agent.option.section.planner"),
                "options": {
                    "model": {
                        "label": trans("agent.option.model"),
                        "type": "combo",
                        "use": "models",
                        "default": "o3-mini-low",
                    },
                    "prompt": {
                        "type": "textarea",
                        "label": trans("agent.option.prompt"),
                        "description": trans("agent.option.prompt.planner.desc"),
                        "default": self.PROMPT_PLANNER,
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
            "feedback": {
                "label": trans("agent.option.section.feedback"),
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
                        "description": trans("agent.option.prompt.feedback.desc"),
                        "default": self.PROMPT_FEEDBACK,
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
        }


