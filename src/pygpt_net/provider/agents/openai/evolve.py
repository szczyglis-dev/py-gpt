#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.26 17:00:00                  #
# ================================================== #

import copy
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Literal, Optional

from agents import (
    Agent as OpenAIAgent,
    Runner,
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
class ChooseFeedback:
    answer_number: int

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

    PROMPT_CHOOSE = (
        "I will give you a list of different answers to the given question. From the provided list, "
        "choose the best and most accurate answer and return the number of that answer to me, without any explanation, "
        "just the number of the answer."
    )

    def __init__(self, *args, **kwargs):
        super(Agent, self).__init__(*args, **kwargs)
        self.id = "openai_agent_evolve"
        self.type = AGENT_TYPE_OPENAI
        self.mode = AGENT_MODE_OPENAI
        self.name = "Evolve"

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
            "name": "Evaluator",
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

    def get_chooser(
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
            "name": "chooser",
            "instructions": instructions,
            "model": window.core.agents.provider.get_openai_model(model),
            "output_type": ChooseFeedback,
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

    def make_choose_query(
            self,
            results: dict,
    ) -> dict:
        """
        Make chooser prompt from results

        :param results: Dictionary of results from parent agents
        :return: Dictionary with content and role for the chooser agent
        """
        answers = []
        for i in range(len(results)):
            j = i + 1
            answers.append(f"Answer {j}:\n{results[j].final_output}")
        allowed_responses = [str(i + 1) for i in range(len(results))]
        content = """
            Select the number of the best answer:\n\n
            {answers}\n\n
            VERY IMPORTANT: You can only choose from the following numbers: [{allowed_responses}].
        """.format(
            answers="\n".join(answers),
            allowed_responses=", ".join(allowed_responses)
        )
        return {
            "content": content,
            "role": "user"
        }

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

        # get options
        feedback_instructions = self.get_option(preset, "feedback", "prompt")
        feedback_model = self.get_option(preset, "feedback", "model")
        feedback_allow_local_tools = self.get_option(preset, "feedback", "allow_local_tools")
        feedback_allow_remote_tools = self.get_option(preset, "feedback", "allow_remote_tools")
        chooser_instructions = self.get_option(preset, "chooser", "prompt")
        chooser_model = self.get_option(preset, "chooser", "model")
        chooser_allow_local_tools = self.get_option(preset, "chooser", "allow_local_tools")
        chooser_allow_remote_tools = self.get_option(preset, "chooser", "allow_remote_tools")

        num_parents = int(self.get_option(preset, "base", "num_parents") or 1)
        if not num_parents or num_parents < 1:
            num_parents = 1
        max_generations = int(self.get_option(preset, "base", "max_generations") or 0)

        kwargs = {
            "max_turns": int(max_steps),
        }
        if model.provider == "openai":
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

        model_chooser = window.core.models.get(chooser_model)
        chooser = self.get_chooser(
            window=window,
            model=model_chooser,
            instructions=chooser_instructions,
            preset=preset,
            tools=tools,
            allow_local_tools=chooser_allow_local_tools,
            allow_remote_tools=chooser_allow_remote_tools,
        )

        # add experts
        experts = get_experts(
            window=window,
            preset=preset,
            verbose=verbose,
            tools=tools,
        )
        if experts:
            agent_kwargs["handoffs"] = experts

        parents = {}
        results = {}
        for i in range(num_parents):
            j = i + 1
            parents[j] = self.get_agent(window, agent_kwargs)
            results[j] = None

        input_items: list[TResponseInputItem] = messages
        num_generation = 1

        if not stream:
            while True:
                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                for i in range(num_parents):
                    j = i + 1
                    parent_kwargs = copy.deepcopy(kwargs)
                    parent_kwargs["input"]: list[TResponseInputItem] = copy.deepcopy(input_items)
                    results[j] = await Runner.run(
                        parents[j],
                        **parent_kwargs
                    )

                choose_items = copy.deepcopy(input_items)
                choose_query = self.make_choose_query(results)
                choose_items.append(choose_query)

                chooser_result = await Runner.run(chooser, choose_items)
                result: ChooseFeedback = chooser_result.final_output
                choose = result.answer_number

                if choose not in results:
                    print("Invalid choice, choose default agent 1")
                    choose = 1

                print("Winner: agent ", choose)

                final_output, last_response_id = window.core.api.openai.responses.unpack_agent_response(results[choose], ctx)
                input_items = results[choose].to_input_list()

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

                if num_generation >= max_generations > 0:
                    info = f"\n\n**{trans('agent.evolve.maxgen_limit')}**\n"
                    ctx.stream = info
                    bridge.on_step(ctx, False)
                    final_output += info
                    break

                num_generation += 1
        else:
            handler = StreamHandler(window, bridge)
            begin = True
            while True:
                ctx.stream = f"\n\n\n\n**{trans('agent.evolve.generation')} {num_generation}**\n\n"
                bridge.on_step(ctx, begin)
                handler.begin = False
                begin = False

                for i in range(num_parents):
                    j = i + 1
                    parent_kwargs = copy.deepcopy(kwargs)
                    parent_kwargs["input"]: list[TResponseInputItem] = copy.deepcopy(input_items)
                    ctx.set_agent_name(f"{trans('agent.evolve.generation')} {num_generation}")
                    results[j] = Runner.run_streamed(
                        parents[j],
                        **parent_kwargs
                    )
                    ctx.stream = f"\n\n**{trans('agent.evolve.running')} {j} ...**\n\n"
                    bridge.on_step(ctx)
                    handler.reset()
                    async for event in results[j].stream_events():
                        if bridge.stopped():
                            results[j].cancel()
                            bridge.on_stop(ctx)
                            break
                        final_output, response_id = handler.handle(event, ctx, buffer=False)
                    bridge.on_next(ctx)
                
                choose_items = copy.deepcopy(input_items)
                choose_query = self.make_choose_query(results)
                choose_items.append(choose_query)

                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                chooser_result = await Runner.run(chooser, choose_items)
                result: ChooseFeedback = chooser_result.final_output
                choose = result.answer_number

                if choose not in results:
                    print("Invalid choice, choose default agent 1")
                    choose = 1

                handler.to_buffer(results[choose].final_output)
                final_output = handler.buffer
                ctx.stream = f"**{trans('agent.evolve.winner')} {result.answer_number}**\n\n"
                bridge.on_step(ctx)

                if bridge.stopped():
                    bridge.on_stop(ctx)
                    break

                window.core.api.openai.responses.unpack_agent_response(results[choose], ctx)
                input_items = results[choose].to_input_list()

                evaluator_result = await Runner.run(evaluator, input_items)
                result: EvaluationFeedback = evaluator_result.final_output

                info = f"\n___\n**{trans('agent.eval.score')}: {result.score}**\n\n"
                if result.score == "pass":
                    info += f"\n\n**{trans('agent.eval.score.good')}.**\n"
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
                else:
                    info = f"\n___\n**{trans('agent.eval.score')}: {result.score}**\n\n"

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

                if num_generation >= max_generations > 0:
                    info = f"\n\n**{trans('agent.evolve.maxgen_limit')}**\n"
                    ctx.stream = info
                    bridge.on_step(ctx, False)
                    final_output += info
                    break

                num_generation += 1

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
                    "num_parents": {
                        "type": "int",
                        "label": trans("agent.evolve.option.num_parents"),
                        "min": 1,
                        "default": 2,
                    },
                    "max_generations": {
                        "type": "int",
                        "label": trans("agent.evolve.option.max_generations"),
                        "min": 1,
                        "default": 10,
                    },
                    "prompt": {
                        "type": "textarea",
                        "label": trans("agent.option.prompt"),
                        "description": trans("agent.option.prompt.desc"),
                        "default": self.PROMPT,
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
            "chooser": {
                "label": trans("agent.option.section.chooser"),
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
                        "description": trans("agent.option.prompt.chooser.desc"),
                        "default": self.PROMPT_CHOOSE,
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


