#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.03 14:00:00                  #
# ================================================== #

from typing import Optional, List

from llama_index.core.tools import FunctionTool

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

from .base import BaseRunner

class Loop(BaseRunner):
    def __init__(self, window=None):
        """
        Agent runner

        :param window: Window instance
        """
        super(Loop, self).__init__(window)
        self.window = window

        self.next_instruction = ""  # evaluation instruction
        self.prev_score = -1  # evaluation score

    def run_once(
            self,
            input: str,
            tools: List[FunctionTool],
            model_name: Optional[str] = None
    ) -> str:
        """
        Run agent once (quick call to ReAct agent)

        :param input: input text
        :param tools: tools
        :param model_name: model name
        :return: text response
        """
        if self.is_stopped():
            return ""  # abort if stopped

        verbose = self.window.core.config.get("agent.llama.verbose", False)
        model = self.window.core.models.get(model_name)
        llm = self.window.core.idx.llm.get(model, stream=False)
        kwargs = {
            "context": BridgeContext(),
            "tools": tools,
            "llm": llm,
            "chat_history": [],
            "max_iterations": 10,
            "verbose": verbose,
        }
        provider = self.window.core.agents.provider.get("react")
        agent = provider.get_agent(self.window, kwargs)
        return agent.chat(self.prepare_input(input))

    def run_next(
            self,
            context: BridgeContext,
            extra: dict,
            signals: BridgeSignals
    ) -> bool:
        """
        Evaluate a response and run next step

        :param context: BridgeContext
        :param extra: extra data
        :param signals: BridgeSignals
        """
        if self.is_stopped():
            return True  # abort if stopped

        ctx = context.ctx
        self.send_response(ctx, signals, KernelEvent.APPEND_BEGIN)  # lock input, show stop btn
        history = context.history
        tools = self.window.core.agents.observer.evaluation.get_tools()
        mode = self.window.core.config.get('agent.llama.loop.mode', "score")
        prompt = ""
        if mode == "score":
            prompt = self.window.core.agents.observer.evaluation.get_prompt_score(history)
        elif mode == "complete":
            prompt = self.window.core.agents.observer.evaluation.get_prompt_complete(history)

        # evaluate
        self.set_busy(signals)
        self.next_instruction = ""  # reset
        self.prev_score = -1  # reset

        # run agent once
        self.run_once(prompt, tools, ctx.model)  # tool will update evaluation
        return self.handle_evaluation(ctx, self.next_instruction, self.prev_score, signals)

    def handle_evaluation(
            self,
            ctx: CtxItem,
            instruction: str,
            score: int,
            signals: BridgeSignals
    ):
        """
        Handle evaluation

        :param ctx: CtxItem
        :param instruction: instruction
        :param score: score
        :param signals: BridgeSignals
        """
        if self.is_stopped():
            return True  # abort if stopped

        score = int(score)
        msg = "{score_label}: {score}%".format(
            score_label=trans('eval.score'),
            score=str(score)
        )
        self.set_status(signals, msg)
        if score < 0:
            self.send_response(ctx, signals, KernelEvent.APPEND_END)
            return True
        good_score = self.window.core.config.get("agent.llama.loop.score", 75)
        if score >= good_score != 0:
            msg = "{status_finished} {score_label}: {score}%".format(
                status_finished=trans('status.finished'),
                score_label=trans('eval.score'),
                score=str(score)
            )
            self.send_response(ctx, signals, KernelEvent.APPEND_END, msg=msg)
            return True

        # print("Instruction: " + instruction, "Score: " + str(score))
        step_ctx = self.add_ctx(ctx)
        step_ctx.set_input(instruction)
        step_ctx.set_output("")
        step_ctx.results = [
            {
                "loop": {
                    "score": score,
                }
            }
        ]
        step_ctx.extra = {
            "agent_input": True,
            "agent_evaluate": True,
            "footer": "Score: " + str(score) + "%",
        }
        step_ctx.internal = False  # input

        self.set_busy(signals)
        self.send_response(step_ctx, signals, KernelEvent.APPEND_DATA)

        # call next run
        context = BridgeContext()
        context.ctx = step_ctx
        context.history = self.window.core.ctx.all(meta_id=ctx.meta.id)
        context.prompt = instruction  # use instruction as prompt
        preset = self.window.controller.presets.get_current()
        extra = {
            "agent_idx": preset.idx,
            "agent_provider": preset.agent_provider,
        }
        context.model = self.window.core.models.get(self.window.core.config.get('model'))
        return self.window.core.agents.runner.call(context, extra, signals)