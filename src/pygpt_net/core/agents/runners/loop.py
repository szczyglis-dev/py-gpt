#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.26 19:00:00                  #
# ================================================== #

from typing import Optional, List

from llama_index.core.tools import FunctionTool

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.ctx.reply import ReplyContext
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

        model = self.window.core.models.get(model_name)
        ctx = CtxItem()
        bridge_context = BridgeContext(
            ctx=ctx,
            history=[],
            model=model,
            prompt=self.prepare_input(input),
            stream=False,
        )
        extra = {
            "agent_provider": "react",  # use React workflow provider
            "agent_tools": tools,
        }
        response_ctx = self.window.core.agents.runner.call_once(
            context=bridge_context,
            extra=extra,
            signals=None,
        )
        if response_ctx:
            return str(response_ctx.output)
        else:
            return "No response from evaluator."

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

        # select evaluation model
        eval_model = ctx.model
        custom_model = self.window.core.config.get('agent.llama.eval_model', None)
        if custom_model and custom_model != "_":
            eval_model = custom_model

        if self.is_verbose():
            print("[Evaluation] Prompt:", prompt)
            print("[Evaluation] Running with model:", eval_model)

        # run agent once
        self.run_once(prompt, tools, eval_model)  # tool will update evaluation
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
        if score < 0:
            self.send_response(ctx, signals, KernelEvent.APPEND_END)
            self.set_idle(signals)
            return True

        msg = "{score_label}: {score}%".format(
            score_label=trans('eval.score'),
            score=str(score)
        )
        self.set_status(signals, msg)

        if self.is_verbose():
            print("[Evaluation] Score:", score)

        good_score = self.window.core.config.get("agent.llama.loop.score", 75)
        if self.is_verbose():
            print("[Evaluation] Score needed:", good_score)
        if score >= good_score != 0:
            msg = "{status_finished} {score_label}: {score}%".format(
                status_finished=trans('status.finished'),
                score_label=trans('eval.score'),
                score=str(score)
            )
            ctx.extra["agent_eval_finish"] = True
            if self.is_verbose():
                print("[Evaluation] Stopping. Finish with score:", score)
            self.send_response(ctx, signals, KernelEvent.APPEND_END, msg=msg)
            self.set_idle(signals)
            return True

        # Continue inside the same durable CtxItem. The evaluator feedback is UI
        # metadata on the next partial, not a synthetic user CtxItem between
        # workflow passes. This keeps the whole legacy agent run inside one
        # Processed-for timeline, exactly like Autonomous continuations.
        reply = ReplyContext()
        reply.type = ReplyContext.AGENT_CONTINUE
        reply.ctx = ctx
        reply.input = instruction
        reply.extra["inline_message"] = {
            "type": "evaluation",
            "text": f"{trans('eval.score')}: {score}%\n\n{instruction}",
        }

        self.set_busy(signals)
        context = BridgeContext(ctx=ctx)
        context.reply_context = reply
        self.window.dispatch(KernelEvent(KernelEvent.AGENT_CONTINUE, {
            "context": context,
            "extra": {},
        }))
        # Evaluation is completed after the ordinary output lifecycle has
        # already drained its reply stack, so execute this newly queued
        # continuation explicitly.
        self.window.controller.kernel.stack.handle()

        if self.is_verbose():
            print("[Evaluation] Instruction:", instruction)
            print("[Evaluation] Running next step in the same ctx...")
        return True

    def is_verbose(self) -> bool:
        """
        Check if verbose mode is enabled

        :return: True if verbose mode is enabled
        """
        return self.window.core.config.get("agent.llama.verbose", False)