#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.11 19:00:00                  #
# ================================================== #

from typing import Dict, Any, List

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem

from ..bridge import ConnectionContext
from .base import BaseRunner


class OpenAIWorkflow(BaseRunner):
    def __init__(self, window=None):
        """
        Agent runner

        :param window: Window instance
        """
        super(OpenAIWorkflow, self).__init__(window)
        self.window = window

    async def run(
            self,
            agent: Any,
            agent_kwargs: Dict[str, Any],
            run: callable,
            ctx: CtxItem,
            prompt: str,
            signals: BridgeSignals,
            verbose: bool = False,
            history: List[CtxItem] = None,
            stream: bool = False,
    ) -> bool:
        """
        Run OpenAI agents

        :param agent: Agent instance
        :param agent_kwargs: Agent kwargs
        :param run: OpenAI runner callable
        :param ctx: Input context
        :param prompt: input text
        :param signals: BridgeSignals
        :param verbose: verbose mode
        :param history: chat history
        :param stream: use streaming
        :return: True if success
        """
        if self.is_stopped():
            return True  # abort if stopped

        self.set_busy(signals)

        # append input to messages
        context = agent_kwargs.get("context", BridgeContext())
        attachments = context.attachments if context else []
        history, previous_response_id = self.window.core.agents.memory.prepare_openai(context)
        msg = self.window.core.gpt.vision.build_agent_input(prompt, attachments)  # build content with attachments
        self.window.core.gpt.vision.append_images(ctx)  # append images to ctx if provided
        history = history + msg

        # callbacks
        def on_step(
                ctx: CtxItem,
                begin: bool = False
        ):
            """
            Callback called on each step

            :param ctx: CtxItem
            :param begin: whether this is the first step
            """
            self.send_stream(ctx, signals, begin)

        def on_stop(ctx: CtxItem):
            """
            Callback for stop events

            :param ctx: CtxItem
            """
            self.set_idle(signals)
            self.end_stream(ctx, signals)

        def on_next(
                ctx: CtxItem,
                wait: bool = False
        ):
            """
            Callback for next step

            Flush current output to before buffer and clear current buffer

            :param ctx: CtxItem
            :param wait: if True, flush current output to before buffer and clear current buffer
            """
            ctx.stream = "\n"
            self.send_stream(ctx, signals, False)
            self.next_stream(ctx, signals)

        def on_next_ctx(
                ctx: CtxItem,
                input: str,
                output: str,
                response_id: str,
                finish: bool = False
        ) -> CtxItem:
            """
            Callback for next context in cycle

            :param ctx: CtxItem
            :param input: input text
            :param output: output text
            :param response_id: response id for OpenAI
            :param finish: If
            :return: CtxItem - the next context item in the cycle
            """
            # finish current stream
            ctx.stream = "\n"
            ctx.output = output  # set output to current context
            self.window.core.ctx.update_item(ctx)
            self.send_stream(ctx, signals, False)
            self.end_stream(ctx, signals)

            # create and return next context item
            next_ctx = self.add_next_ctx(ctx)
            next_ctx.set_input(input)
            next_ctx.partial = True
            if finish:
                next_ctx.extra["agent_finish"] = True

            self.send_response(next_ctx, signals, KernelEvent.APPEND_DATA)
            return next_ctx

        def on_error(error: Any):
            """
            Callback for error occurred during processing

            :param error: Exception raised during processing
            """
            self.set_idle(signals)
            self.set_error(error)

        # callbacks
        bridge = ConnectionContext(
            stopped=self.is_stopped,
            on_step=on_step,
            on_stop=on_stop,
            on_error=on_error,
            on_next=on_next,
            on_next_ctx=on_next_ctx,
        )
        run_kwargs = {
            "window": self.window,
            "agent_kwargs": agent_kwargs,
            "previous_response_id": previous_response_id,
            "messages": history,
            "ctx": ctx,
            "stream": stream,
            "bridge": bridge,
        }
        if previous_response_id:
            run_kwargs["previous_response_id"] = previous_response_id

        # run agent
        ctx, output, response_id = await run(**run_kwargs)

        if not ctx.partial:
            response_ctx = self.make_response(ctx, prompt, output, response_id)
            self.send_response(response_ctx, signals, KernelEvent.APPEND_DATA)
        else:
            ctx.partial = False  # last part, not partial anymore
            # already handled in next_ctx(), so do not return response

        self.set_idle(signals)
        return True

    def make_response(
            self,
            ctx: CtxItem,
            input: str,
            output: str,
            response_id: str
    ) -> CtxItem:
        """
        Create a response context item with the given input and output.

        :param ctx: CtxItem - the context item to use as a base
        :param input: Input text for the response
        :param output: Output text for the response
        :param response_id: Response ID for OpenAI
        :return: CtxItem - the response context item with input, output, and extra data
        """
        response_ctx = self.add_ctx(ctx, with_tool_outputs=True)
        response_ctx.set_input(input)
        response_ctx.set_output(output)
        response_ctx.set_agent_final_response(output)  # always set to further use
        response_ctx.extra["agent_output"] = True  # mark as output response
        response_ctx.extra["agent_finish"] = True  # mark as finished
        response_ctx.msg_id = response_id  # set response id for OpenAI

        if ctx.agent_final_response:  # only if not empty
            response_ctx.extra["output"] = ctx.agent_final_response

        # if there are tool outputs, img, files, append it to the response context
        if ctx.use_agent_final_response:
            self.window.core.agents.tools.append_tool_outputs(response_ctx)
        else:
            self.window.core.agents.tools.extract_tool_outputs(response_ctx)

        return response_ctx