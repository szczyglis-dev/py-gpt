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

import re
from typing import Optional, Any, List

from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import (
    ToolCall,
    ToolCallResult,
    AgentStream,
    AgentOutput,
)
from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem

from .base import BaseRunner


class LlamaWorkflow(BaseRunner):
    def __init__(self, window=None):
        """
        Agent runner

        :param window: Window instance
        """
        super(LlamaWorkflow, self).__init__(window)
        self.window = window

    async def run(
            self,
            agent: Any,
            ctx: CtxItem,
            prompt: str,
            signals: BridgeSignals,
            verbose: bool = False,
            history: List[CtxItem] = None,
            llm: Any = None,
    ) -> bool:
        """
        Run agent workflow

        :param agent: Agent instance
        :param ctx: Input context
        :param prompt: input text
        :param signals: BridgeSignals
        :param verbose: verbose mode
        :param history: chat history
        :param llm: LLM instance
        :return: True if success
        """
        if self.is_stopped():
            return True  # abort if stopped

        agent_ctx = Context(agent)
        memory = self.window.core.idx.chat.get_memory_buffer(history, llm)
        self.set_busy(signals)
        await self.run_agent(
            agent=agent,
            ctx=agent_ctx,
            query=prompt,
            memory=memory,
            verbose=verbose,
            item_ctx=ctx,
            signals=signals,
        )
        response_ctx = self.add_ctx(ctx, with_tool_outputs=True)
        response_ctx.set_input("inp")

        prev_output = ctx.live_output
        # remove all <execute>...</execute>
        if prev_output:
            prev_output = re.sub(r'<execute>.*?</execute>', '', prev_output, flags=re.DOTALL)

        response_ctx.set_agent_final_response(ctx.agent_final_response)  # always set to further use
        response_ctx.set_output(prev_output)  # append from stream
        response_ctx.extra["agent_output"] = True  # mark as output response
        response_ctx.extra["agent_finish"] = True  # mark as finished

        if ctx.agent_final_response:  # only if not empty
            response_ctx.extra["output"] = ctx.agent_final_response

        # if there are tool outputs, img, files, append it to the response context
        if ctx.use_agent_final_response:
            self.window.core.agents.tools.append_tool_outputs(response_ctx)
        else:
            self.window.core.agents.tools.extract_tool_outputs(response_ctx)
        self.end_stream(response_ctx, signals)

        # send response
        self.send_response(response_ctx, signals, KernelEvent.APPEND_DATA)
        self.set_idle(signals)
        return True

    async def run_agent(
            self,
            agent,
            ctx,
            query,
            memory,
            verbose=False,
            item_ctx: Optional[CtxItem] = None,
            signals: Optional[BridgeSignals] = None):
        """
        Run agent workflow
        This method runs the agent's workflow, processes tool calls, and streams events.

        :param agent: Agent instance
        :param ctx: Context
        :param query: Input query string
        :param memory: Memory buffer for the agent
        :param verbose: Verbose mode (default: False)
        :param item_ctx: Optional CtxItem for additional context
        :param signals: Optional BridgeSignals for communication
        :return: handler for the agent workflow
        """
        handler = agent.run(query, ctx=ctx, memory=memory, verbose=verbose)
        if verbose:
            print(f"User:  {query}")

        begin = True
        item_ctx.live_output = ""  # to response append
        item_ctx.output = ""  # empty to prevent render
        item_ctx.stream = ""  # for stream

        async for event in handler.stream_events():
            if self.is_stopped():
                self.end_stream(item_ctx, signals)
                break
            if isinstance(event, ToolCallResult):
                output = f"\n-----------\nExecution result:\n{event.tool_output}"
                if verbose:
                    print(output)
                formatted = "\n```output\n" + str(event.tool_output) + "\n```\n"
                item_ctx.live_output += formatted
                item_ctx.stream = formatted
                if item_ctx.stream_agent_output:
                    self.send_stream(item_ctx, signals, begin)
            elif isinstance(event, ToolCall):
                if "code" in event.tool_kwargs:
                    output = f"\n-----------\nTool call code:\n{event.tool_kwargs['code']}"
                    if verbose:
                        print(output)
                    formatted = "\n```python\n" + str(event.tool_kwargs['code']) + "\n```\n"
                    item_ctx.live_output += formatted
                    item_ctx.stream = formatted
                    if item_ctx.stream_agent_output:
                        self.send_stream(item_ctx, signals, begin)
            elif isinstance(event, AgentStream):
                if verbose:
                    print(f"{event.delta}", end="", flush=True)
                if event.delta:
                    item_ctx.live_output += event.delta
                    item_ctx.stream = event.delta
                    if item_ctx.stream_agent_output:
                        self.send_stream(item_ctx, signals, begin)  # send stream to webview
                    begin = False
            elif isinstance(event, AgentOutput):
                thought, answer = self.extract_final_response(str(event))
                if answer:
                    item_ctx.set_agent_final_response(answer)
                    if verbose:
                        print(f"\nFinal response: {answer}")

        return await handler