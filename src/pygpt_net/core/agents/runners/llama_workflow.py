#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.14 01:00:00                  #
# ================================================== #

import re
from typing import Optional, Any, List, Union

from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import (
    ToolCall,
    ToolCallResult,
    AgentStream,
    AgentOutput,
)
from workflows.errors import WorkflowCancelledByUser

from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.provider.agents.llama_index.workflow.events import StepEvent

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

        try:
            ctx = await self.run_agent(
                agent=agent,
                ctx=agent_ctx,
                query=prompt,
                memory=memory,
                verbose=verbose,
                item_ctx=ctx,
                signals=signals,
                use_partials=self.window.core.config.get("agent.openai.response.split", True)
            )
        except WorkflowCancelledByUser:
            print("\n\n[STOP] Workflow stopped by user.")
        except Exception as e:
            self.window.core.debug.log(f"Error running agent workflow: {e}")
            ctx.extra["error"] = str(e)
            self.set_idle(signals)
            return False

        if ctx.partial:
            ctx.partial = False  # reset partial flag

        response_ctx = self.make_response(ctx)
        self.end_stream(response_ctx, signals)
        self.send_response(response_ctx, signals, KernelEvent.APPEND_DATA)  # send response

        self.set_idle(signals)
        return True

    async def run_once(
            self,
            agent: Any,
            ctx: CtxItem,
            prompt: str,
            signals: BridgeSignals,
            verbose: bool = False,
            history: List[CtxItem] = None,
            llm: Any = None,
            is_expert_call: bool = False,
    ) -> Union[CtxItem, None]:
        """
        Run agent workflow

        :param agent: Agent instance
        :param ctx: Input context
        :param prompt: input text
        :param signals: BridgeSignals
        :param verbose: verbose mode
        :param history: chat history
        :param llm: LLM instance
        :param is_expert_call: if True, run as expert call
        :return: True if success
        """
        if self.is_stopped():
            return None  # abort if stopped

        memory = self.window.core.idx.chat.get_memory_buffer(history, llm)
        agent_ctx = Context(agent)
        flush = True
        if is_expert_call:
            flush = False
        try:
            ctx = await self.run_agent(
                agent=agent,
                ctx=agent_ctx,
                query=prompt,
                memory=memory,
                verbose=verbose,
                item_ctx=ctx,
                signals=signals,
                use_partials=False,  # use partials for streaming
                flush=flush,  # flush output buffer to webview
            )
        except WorkflowCancelledByUser:
            print("\n\n[STOP] Workflow stopped by user.")
        except Exception as e:
            self.window.core.debug.log(f"Error running agent workflow: {e}")
            ctx.extra["error"] = str(e)
            return None

        if ctx.agent_final_response:
            ctx.output = ctx.agent_final_response  # set output to current context
        else:
            ctx.output = ctx.live_output

        return ctx

    def make_response(
            self,
            ctx: CtxItem
    ) -> CtxItem:
        """
        Create a response context item with the given input and output.

        :param ctx: CtxItem - the context item to use as a base
        """
        response_ctx = self.add_ctx(ctx, with_tool_outputs=True)
        response_ctx.set_input("")

        prev_output = ctx.live_output
        if prev_output:
            prev_output = self.filter_output(prev_output)  # remove all <execute>...</execute>

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

        return response_ctx

    def filter_output(self, output: str) -> str:
        """
        Filter output to remove unwanted tags

        :param output: Output string
        :return: Filtered output string
        """
        # Remove <execute>...</execute> tags
        filtered_output = re.sub(r'<execute>.*?</execute>', '', output, flags=re.DOTALL)
        return filtered_output

    async def run_agent(
            self,
            agent,
            ctx,
            query,
            memory,
            verbose=False,
            item_ctx: Optional[CtxItem] = None,
            signals: Optional[BridgeSignals] = None,
            use_partials: bool = True,
            flush: bool = True,
    ):
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
        :param use_partials: If True, use partial context items for streaming
        :param flush: If True, flush the output buffer before starting
        :return: handler for the agent workflow
        """
        handler = agent.run(
            query,
            ctx=ctx,
            memory=memory,
            verbose=verbose,
            on_stop=self.is_stopped,
        )
        if verbose:
            print(f"User:  {query}")

        begin = True
        item_ctx.live_output = ""  # to response append
        item_ctx.output = ""  # empty to prevent render
        item_ctx.stream = ""  # for stream

        print("RUN AGENT!!!!!!!!!!!!!!!!!!!!")

        async for event in handler.stream_events():
            if self.is_stopped():
                # persist current output on stop
                item_ctx.output = item_ctx.live_output
                self.window.core.ctx.update_item(item_ctx)
                if flush:
                    self.end_stream(item_ctx, signals)
                await handler.cancel_run()  # cancel, will raise WorkflowCancelledByUser
                break
            if isinstance(event, ToolCallResult):
                output = f"\n-----------\nExecution result:\n{event.tool_output}"
                if verbose:
                    print(output)
                formatted = "\n```output\n" + str(event.tool_output) + "\n```\n"
                item_ctx.live_output += formatted
                item_ctx.stream = formatted
                if item_ctx.stream_agent_output and flush:
                    self.send_stream(item_ctx, signals, begin)
            elif isinstance(event, ToolCall):
                if "code" in event.tool_kwargs:
                    output = f"\n-----------\nTool call code:\n{event.tool_kwargs['code']}"
                    if verbose:
                        print(output)
                    formatted = "\n```python\n" + str(event.tool_kwargs['code']) + "\n```\n"
                    item_ctx.live_output += formatted
                    item_ctx.stream = formatted
                    if item_ctx.stream_agent_output and flush:
                        self.send_stream(item_ctx, signals, begin)
            elif isinstance(event, StepEvent):
                self.set_busy(signals)
                if not use_partials:
                    continue
                if verbose:
                    print("\n\n-----STEP-----\n\n")
                    print(f"[{event.name}] {event.index}/{event.total} meta={event.meta}")
                if flush:
                    item_ctx = self.on_next_ctx(
                        item_ctx,
                        signals=signals,
                        begin=begin,
                        stream=True,
                    )
            elif isinstance(event, AgentStream):
                if verbose:
                    print(f"{event.delta}", end="", flush=True)
                if event.delta:
                    item_ctx.live_output += event.delta
                    item_ctx.stream = event.delta
                    if item_ctx.stream_agent_output and flush:
                        self.send_stream(item_ctx, signals, begin)  # send stream to webview
                    begin = False
            elif isinstance(event, AgentOutput):
                thought, answer = self.extract_final_response(str(event))
                if answer:
                    item_ctx.set_agent_final_response(answer)
                    if verbose:
                        print(f"\nFinal response: {answer}")

        return item_ctx

    def on_next_ctx(
            self,
            ctx: CtxItem,
            signals: BridgeSignals,
            begin: bool = False,
            stream: bool = True,
    ) -> CtxItem:
        """
        Callback for next context in cycle

        :param ctx: CtxItem
        :param signals: BridgeSignals
        :param begin: if True, flush current output to before buffer and clear current buffer
        :param stream: is streaming enabled
        :return: CtxItem - the next context item in the cycle
        """
        # finish current stream
        ctx.stream = "\n"
        ctx.extra["agent_output"] = True  # allow usage in history
        ctx.output = ctx.live_output  # set output to current context
        ctx.output = self.filter_output(ctx.output)
        self.window.core.ctx.update_item(ctx)

        if stream:
            self.send_stream(ctx, signals, begin)
            self.end_stream(ctx, signals)

        # create and return next context item
        next_ctx = self.add_next_ctx(ctx)
        next_ctx.set_input("")
        next_ctx.set_output("")
        next_ctx.partial = True
        next_ctx.extra["agent_output"] = True  # allow usage in history

        self.send_response(next_ctx, signals, KernelEvent.APPEND_DATA)
        return next_ctx