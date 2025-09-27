# core/agents/runners/llama_workflow.py

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.27 06:00:00                  #
# ================================================== #

import re
from typing import Optional, Any, List, Union

from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import (
    ToolCall,
    ToolCallResult,
    AgentStream,
    AgentOutput,
    # AgentInput,  # not needed currently
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
        self.last_response_id = None

    async def run(
            self,
            agent: Any,
            ctx: CtxItem,
            prompt: str,
            signals: BridgeSignals,
            verbose: bool = False,
            history: List[CtxItem] = None,
            llm: Any = None,
            schema: Optional[List] = None,
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
        :param schema: custom agent flow schema
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

        use_current = False
        if ctx.partial:
            use_current = True  # use current item as response if partial item (do not create new one)
            ctx.partial = False  # reset partial flag

        response_ctx = self.make_response(ctx, use_current=use_current)
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
            ctx: CtxItem,
            use_current: bool = False
    ) -> CtxItem:
        """
        Create a response context item with the given input and output.

        :param ctx: CtxItem - the context item to use as a base
        :param use_current: If True, use the current context item instead of creating a new one
        """
        if use_current:
            response_ctx = ctx  # use current context item
        else:
            response_ctx = self.add_ctx(ctx, with_tool_outputs=True)

        response_ctx.set_input("")

        prev_output = ctx.live_output
        if prev_output:
            prev_output = self.filter_output(prev_output)  # remove all [!exec]...[/!exec]

        response_ctx.set_agent_final_response(ctx.agent_final_response)  # always set to further use
        response_ctx.set_output(prev_output)  # append from stream
        response_ctx.extra["agent_output"] = True  # mark as output response
        response_ctx.extra["agent_finish"] = True  # mark as finished
        response_ctx.set_agent_name(ctx.get_agent_name()) # store last agent name

        if "agent_input" in response_ctx.extra:
            del response_ctx.extra["agent_input"]  # remove agent input from extra

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
        if output is None:
            return ""

        # Remove <execute>...</execute> tags
        filtered_output = re.sub(r'<execute>.*?</execute>', '', output, flags=re.DOTALL)
        return filtered_output.strip()

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

        # Keep last known agent name to avoid redundant ctx updates.
        last_agent_name: Optional[str] = None

        # Track whether current block has already produced user-visible tokens.
        # This prevents creating empty DB items and preserves order.
        content_written: bool = False
        block_open: bool = False  # logical "block" opened after first StepEvent

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
                content_written = True
                if item_ctx.stream_agent_output and flush:
                    self.send_stream(item_ctx, signals, begin)
                begin = False

            elif isinstance(event, ToolCall):
                if "code" in event.tool_kwargs:
                    output = f"\n-----------\nTool call code:\n{event.tool_kwargs['code']}"
                    if verbose:
                        print(output)
                    formatted = "\n```python\n" + str(event.tool_kwargs['code']) + "\n```\n"
                    item_ctx.live_output += formatted
                    item_ctx.stream = formatted
                    content_written = True
                    if item_ctx.stream_agent_output and flush:
                        self.send_stream(item_ctx, signals, begin)
                    begin = False

            elif isinstance(event, StepEvent):
                # UI splitting strategy aligned with OpenAI flow:
                # - do NOT start a new DB item at the first StepEvent
                # - only finalize the previous item if it already produced content
                #   (prevents empty items and ordering glitches)
                self.set_busy(signals)
                if not use_partials:
                    # We still want to propagate the name early if provided.
                    try:
                        meta = getattr(event, "meta", {}) or {}
                        next_name = meta.get("agent_name")
                        if next_name:
                            last_agent_name = self._apply_agent_name_to_ctx(item_ctx, next_name, last_agent_name)
                    except Exception:
                        pass
                    begin = True
                    continue

                if verbose:
                    print("\n\n-----STEP-----\n\n")
                    print(f"[{event.name}] {event.index}/{event.total} meta={event.meta}")

                # If there was an open block with content -> finalize it to a new DB item.
                if block_open and content_written:
                    if flush:
                        item_ctx = self.on_next_ctx(
                            item_ctx,
                            signals=signals,
                            begin=begin,
                            stream=True,
                        )
                    # Apply next agent name on the fresh ctx (so UI header is correct from token #1).
                    try:
                        meta = getattr(event, "meta", {}) or {}
                        next_name = meta.get("agent_name")
                        if next_name:
                            last_agent_name = self._apply_agent_name_to_ctx(item_ctx, next_name, last_agent_name)
                    except Exception:
                        pass
                else:
                    # First step or previous step had no visible content: just propagate the name.
                    try:
                        meta = getattr(event, "meta", {}) or {}
                        next_name = meta.get("agent_name")
                        if next_name:
                            last_agent_name = self._apply_agent_name_to_ctx(item_ctx, next_name, last_agent_name)
                    except Exception:
                        pass

                # Prepare for the upcoming tokens (new block begins).
                block_open = True
                content_written = False
                begin = True
                continue

            elif isinstance(event, AgentStream):
                # Update agent name from event if present; fallback to header parsing.
                name = getattr(event, "current_agent_name", None)
                if not name:
                    name = self._guess_agent_name_from_text(getattr(event, "delta", "") or "")
                if name:
                    last_agent_name = self._apply_agent_name_to_ctx(item_ctx, name, last_agent_name)

                if verbose:
                    print(f"{event.delta}", end="", flush=True)
                if event.delta:
                    item_ctx.live_output += event.delta
                    item_ctx.stream = event.delta
                    content_written = True
                    if item_ctx.stream_agent_output and flush:
                        self.send_stream(item_ctx, signals, begin)  # send stream to webview
                    begin = False

            elif isinstance(event, AgentOutput):
                # Ensure final agent name is applied as well.
                name = getattr(event, "current_agent_name", None)
                if name:
                    last_agent_name = self._apply_agent_name_to_ctx(item_ctx, name, last_agent_name)
                thought, answer = self.extract_final_response(str(event))
                if answer:
                    item_ctx.set_agent_final_response(answer)
                    if verbose:
                        print(f"\nFinal response: {answer}")
                # Do not split the block here – we will either:
                # - split on the next StepEvent, or
                # - finalize once at the end (make_response), just like OpenAI flow does.

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
        next_ctx.set_agent_name(ctx.get_agent_name())  # propagate agent name
        self.send_response(next_ctx, signals, KernelEvent.APPEND_DATA)

        return next_ctx

    # ===== helpers for agent name propagation =====

    def _apply_agent_name_to_ctx(self, ctx: CtxItem, name: str, last_known: Optional[str]) -> str:
        """
        Apply agent name to your context, avoiding redundant updates.
        Falls back to ctx.extra['agent_name'] if set_agent_name is unavailable.
        """
        if not name:
            return last_known or ""
        if last_known and last_known == name:
            return last_known
        try:
            if hasattr(ctx, "set_agent_name") and callable(getattr(ctx, "set_agent_name")):
                ctx.set_agent_name(name)
            # Always mirror into extra for downstream consumers
            ctx.extra["agent_name"] = name
        except Exception:
            ctx.extra["agent_name"] = name
        return name

    def _guess_agent_name_from_text(self, text: str) -> Optional[str]:
        """
        Try to infer agent name from header like '**Name**' which our workflow emits
        before each agent block.
        """
        if not text:
            return None
        # Look for the first bold segment – keep it lenient
        m = re.search(r"\*\*([^*]+?)\*\*", text)
        if m:
            return m.group(1).strip()
        return None