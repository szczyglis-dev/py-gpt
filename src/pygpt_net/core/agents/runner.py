#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.02 03:00:00                  #
# ================================================== #

import asyncio
import copy
import re
from typing import Optional, Dict, Any, List, Tuple, Union

from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import (
    ToolCall,
    ToolCallResult,
    AgentStream,
    AgentOutput,
)

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.types import (
    AGENT_MODE_ASSISTANT,
    AGENT_MODE_PLAN,
    AGENT_MODE_STEP,
    AGENT_MODE_WORKFLOW,
    AGENT_MODE_OPENAI,
)
from pygpt_net.core.events import Event, KernelEvent, RenderEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans
from .bridge import ConnectionContext


class Runner:
    def __init__(self, window=None):
        """
        Agent runner

        :param window: Window instance
        """
        self.window = window
        self.signals = None  # BridgeSignals
        self.error = None  # last exception
        self.next_instruction = ""  # evaluation instruction
        self.prev_score = -1  # evaluation score

    def call(
            self,
            context: BridgeContext,
            extra: Dict[str, Any],
            signals: BridgeSignals
    ) -> bool:
        """
        Call an agent

        :param context: BridgeContext
        :param extra: extra data
        :param signals: BridgeSignals
        :return: True if success
        """
        if self.is_stopped():
            return True  # abort if stopped

        id = extra.get("agent_provider", "openai")
        verbose = self.window.core.config.get("agent.llama.verbose", False)
        try:
            # prepare input context
            ctx = context.ctx
            ctx.extra["agent_input"] = True  # mark as user input
            ctx.agent_call = True  # disables reply from plugin commands
            prompt = context.prompt

            # prepare agent
            model = context.model
            agent_idx = extra.get("agent_idx", None)
            self.window.core.agents.tools.context = context
            self.window.core.agents.tools.agent_idx = agent_idx
            system_prompt = context.system_prompt
            max_steps = self.window.core.config.get("agent.llama.steps", 10)
            tools = self.window.core.agents.tools.prepare(context, extra, force=True)
            function_tools = self.window.core.agents.tools.get_function_tools(context.ctx, extra, force=True)
            plugin_tools = self.window.core.agents.tools.get_plugin_tools(context, extra, force=True)
            plugin_specs = self.window.core.agents.tools.get_plugin_specs(context, extra, force=True)
            retriever_tool = self.window.core.agents.tools.get_retriever_tool(context, extra)
            history = self.window.core.agents.memory.prepare(context)
            llm = self.window.core.idx.llm.get(model, stream=False)
            workdir = self.window.core.config.get_user_dir('data')
            if self.window.core.plugins.get_option("cmd_code_interpreter", "sandbox_ipython"):
                workdir = "/data"

            # append system prompt
            if id not in [
                "openai_agent_base",  # openai-agents
                "openai_agent_experts",  # openai-agents
                "openai_assistant", # llama-index
                "code_act", # llama-index
            ]:
                if system_prompt:
                    msg = ChatMessage(
                        role=MessageRole.SYSTEM,
                        content=system_prompt,
                    )
                    history.insert(0, msg)

            # disable tools if cmd is not enabled
            if not self.window.core.command.is_cmd(inline=False):
                tools = []
                plugin_tools = []
                plugin_specs = []

            agent_kwargs = {
                "context": context,
                "tools": tools,
                "function_tools": function_tools,
                "plugin_tools": plugin_tools,
                "plugin_specs": plugin_specs,
                "retriever_tool": retriever_tool,
                "llm": llm,
                "model": model,
                "chat_history": history,
                "max_iterations": max_steps,
                "verbose": verbose,
                "system_prompt": system_prompt,
                "are_commands": self.window.core.config.get("cmd"),
                "workdir": workdir,
                "preset": context.preset if context else None,
            }

            if self.window.core.agents.provider.has(id):
                provider = self.window.core.agents.provider.get(id)
                agent = provider.get_agent(self.window, agent_kwargs)
                agent_run = provider.run
                if verbose:
                    print("Using Agent: " + str(id) + ", model: " + str(model.id))
            else:
                raise Exception("Agent not found: " + str(id))

            # run agent
            mode = provider.get_mode()
            kwargs = {
                "agent": agent,
                "ctx": ctx,
                "prompt": prompt,
                "signals": signals,
                "verbose": verbose,
            }

            if mode == AGENT_MODE_PLAN:
                return self.run_plan(**kwargs)
            elif mode == AGENT_MODE_STEP:
                return self.run_steps(**kwargs)
            elif mode == AGENT_MODE_ASSISTANT:
                return self.run_assistant(**kwargs)
            elif mode == AGENT_MODE_WORKFLOW:
                kwargs["history"] = history
                kwargs["llm"] = llm
                return asyncio.run(self.run_workflow(**kwargs))
            elif mode == AGENT_MODE_OPENAI:
                kwargs["run"] = agent_run  # callable
                kwargs["agent_kwargs"] = agent_kwargs  # as dict
                kwargs["stream"] = self.window.core.config.get("stream", False) # from global
                return asyncio.run(self.run_openai(**kwargs))

        except Exception as err:
            self.window.core.debug.error(err)
            self.error = err
            return False

    async def run_agent_workflow(
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

    async def run_workflow(
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
        await self.run_agent_workflow(
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

    async def run_openai(
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
                response_id: str
        ) -> CtxItem:
            """
            Callback for next context in cycle

            :param ctx: CtxItem
            :param input: input text
            :param output: output text
            :param response_id: response id for OpenAI
            :return: CtxItem - the next context item in the cycle
            """
            # finish current stream
            ctx.stream = "\n"
            self.send_stream(ctx, signals, False)
            self.end_stream(ctx, signals)

            # send current response
            # TODO: disable evaluation for now in chat response controller
            response_ctx = self.make_response(ctx, input, output, response_id)
            response_ctx.partial = True  # do not finish and evaluate yet
            self.send_response(response_ctx, signals, KernelEvent.APPEND_DATA)

            # create and return next context item
            next_ctx = self.add_next_ctx(ctx)
            next_ctx.set_input(input)
            self.window.core.ctx.set_last_item(next_ctx)
            self.window.core.ctx.add(next_ctx)
            return next_ctx

        def on_error(error: Any):
            """
            Callback for error occurred during processing

            :param error: Exception raised during processing
            """
            self.set_idle(signals)
            self.window.core.debug.error(error)
            self.error = error

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

        # prepare response
        response_ctx = self.make_response(ctx, prompt, output, response_id)

        # send response
        self.send_response(response_ctx, signals, KernelEvent.APPEND_DATA)
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

    def run_steps(
            self,
            agent: Any,
            ctx: CtxItem,
            prompt: str,
            signals: BridgeSignals,
            verbose: bool = False
    ) -> bool:
        """
        Run agent steps

        :param agent: Agent instance
        :param ctx: Input context
        :param prompt: input text
        :param signals: BridgeSignals
        :param verbose: verbose mode
        :return: True if success
        """
        if self.is_stopped():
            return True  # abort if stopped

        is_last = False
        task = agent.create_task(self.prepare_input(prompt))
        tools_output = None

        # run steps
        i = 1
        idx = 0
        while not is_last:
            if self.is_stopped():
                break  # handle force stop

            if verbose:
                print ("\n----------- BEGIN STEP {} ----------\n".format(i))

            self.set_busy(signals)
            step_output = agent.run_step(task.task_id)
            is_last = step_output.is_last

            # append each step to chat output, last step = final response, so we skip it
            tools_output = self.window.core.agents.tools.export_sources(step_output.output)

            # get only current step tool calls using idx
            if tools_output:
                # check if idx is in range
                if idx < len(tools_output):
                    tools_output = [tools_output[idx]]
                    # INFO: idx is indexed from 0
                    # because tool outputs from previous step goes to the next ctx item!

            if verbose:
                print("\n")
                print("Step: " + str(i))
                print("Is last: " + str(is_last))
                print("Tool calls: " + str(tools_output))
                print("\n")

            if not is_last:
                step_ctx = self.add_ctx(ctx)
                step_ctx.set_input(str(tools_output))
                step_ctx.set_output("`{step_label} {i}`".format(
                    step_label=trans('msg.agent.step'),
                    i=str(i)
                ))
                step_ctx.cmds = tools_output
                step_ctx.results = ctx.results  # get results from base ctx
                ctx.results = []  # reset results

                # copy extra data (output from plugins)
                if tools_output:
                    for k in ctx.extra:
                        if not k.startswith("agent_"):
                            step_ctx.extra[k] = ctx.extra[k]

                # reset input ctx
                for k in list(ctx.extra.keys()):
                    if k != "agent_input":
                        del ctx.extra[k]

                step_ctx.extra["agent_step"] = True
                self.send_response(step_ctx, signals, KernelEvent.APPEND_DATA)
            i += 1
            idx += 1

        # final response
        if is_last:
            if self.is_stopped():
                return True  # abort if stopped
            response = agent.finalize_response(task.task_id)
            response_ctx = self.add_ctx(ctx)
            response_ctx.set_input(str(tools_output))
            response_ctx.set_output(str(response))
            response_ctx.extra["agent_output"] = True  # mark as output response
            response_ctx.extra["agent_finish"] = True  # mark as finished
            self.send_response(response_ctx, signals, KernelEvent.APPEND_DATA)
        self.set_idle(signals)
        return True

    def run_steps_once(
            self,
            agent: Any,
            ctx: CtxItem,
            prompt: str,
            verbose: bool = False
    ) -> Union[CtxItem, None]:
        """
        Run agent steps

        :param agent: Agent instance
        :param ctx: Input context
        :param prompt: input text
        :param verbose: verbose mode
        :return: CtxItem with final response or True if stopped
        """
        if self.is_stopped():
            return  # abort if stopped

        is_last = False
        task = agent.create_task(self.prepare_input(prompt))
        tools_output = None

        # run steps
        i = 1
        idx = 0
        while not is_last:
            if self.is_stopped():
                break  # handle force stop

            if verbose:
                print ("\n----------- BEGIN STEP {} ----------\n".format(i))

            step_output = agent.run_step(task.task_id)
            is_last = step_output.is_last

            # append each step to chat output, last step = final response, so we skip it
            tools_output = self.window.core.agents.tools.export_sources(step_output.output)

            if verbose:
                print("\n")
                print("Step: " + str(i))
                print("Is last: " + str(is_last))
                print("Tool calls: " + str(tools_output))
                print("\n")

            if not is_last:
                step_ctx = self.add_ctx(ctx)
                step_ctx.set_input(str(tools_output))
                step_ctx.set_output("`{step_label} {i}`".format(
                    step_label=trans('msg.agent.step'),
                    i=str(i)
                ))
                step_ctx.cmds = tools_output
                step_ctx.results = ctx.results  # get results from base ctx
                ctx.results = []  # reset results

                # copy extra data (output from plugins)
                if tools_output:
                    for k in ctx.extra:
                        if not k.startswith("agent_"):
                            step_ctx.extra[k] = ctx.extra[k]

                # reset input ctx
                for k in list(ctx.extra.keys()):
                    if k != "agent_input":
                        del ctx.extra[k]

                step_ctx.extra["agent_step"] = True
            i += 1
            idx += 1

        # final response
        if is_last:
            if self.is_stopped():
                return  # abort if stopped
            response = agent.finalize_response(task.task_id)
            response_ctx = self.add_ctx(ctx)
            response_ctx.set_input(str(tools_output))
            response_ctx.set_output(str(response))
            response_ctx.extra["agent_output"] = True  # mark as output response
            response_ctx.extra["agent_finish"] = True  # mark as finished
            return response_ctx

    def run_assistant(
            self,
            agent: Any,
            ctx: CtxItem,
            prompt: str,
            signals: BridgeSignals,
            verbose: bool = False
    ) -> bool:
        """
        Run agent steps

        :param agent: Agent instance
        :param ctx: Input context
        :param prompt: input text
        :param signals: BridgeSignals
        :param verbose: verbose mode
        :return: True if success
        """
        if self.is_stopped():
            return True  # abort if stopped

        if verbose:
            print("Running OpenAI Assistant...")
            print("Assistant: " + str(agent.assistant.id))
            print("Thread: " + str(agent.thread_id))
            print("Model: " + str(agent.assistant.model))
            print("Input: " + str(ctx.input))

        thread_id = agent.thread_id
        ctx.meta.thread = thread_id
        ctx.meta.assistant = agent.assistant.id
        ctx.thread = thread_id

        if self.is_stopped():
            return True  # abort if stopped

        # final response
        self.set_busy(signals)
        response = agent.chat(self.prepare_input(prompt))
        response_ctx = self.add_ctx(ctx)
        response_ctx.thread = thread_id
        response_ctx.set_input("Assistant")
        response_ctx.set_output(str(response))
        response_ctx.extra["agent_output"] = True  # mark as output response
        response_ctx.extra["agent_finish"] = True  # mark as finished
        self.send_response(response_ctx, signals, KernelEvent.APPEND_DATA)
        return True

    def run_plan(
            self,
            agent: Any,
            ctx: CtxItem,
            prompt: str,
            signals: BridgeSignals,
            verbose: bool = False
    ) -> bool:
        """
        Run agent sub-tasks

        :param agent: Agent instance
        :param ctx: Input context
        :param prompt: input text
        :param signals: BridgeSignals
        :param verbose: verbose mode
        :return: True if success
        """
        if self.is_stopped():
            return True  # abort if stopped

        self.set_busy(signals)
        plan_id = agent.create_plan(
            self.prepare_input(prompt)
        )
        plan = agent.state.plan_dict[plan_id]
        c = len(plan.sub_tasks)

        # prepare plan description
        plan_desc = "`{current_plan}:`\n".format(
            current_plan=trans('msg.agent.plan.current')
        )
        i = 1
        for sub_task in plan.sub_tasks:
            plan_desc += "\n\n"
            plan_desc += "\n**===== {sub_task_label}: {sub_task_name} =====**".format(
                sub_task_label=trans('msg.agent.plan.subtask'),
                sub_task_name=sub_task.name,
            )
            plan_desc += "\n{expected_label}: {expected_output}".format(
                expected_label=trans('msg.agent.plan.expected'),
                expected_output=str(sub_task.expected_output),
            )
            plan_desc += "\n{deps_label}: {dependencies}".format(
                deps_label=trans('msg.agent.plan.deps'),
                dependencies=str(sub_task.dependencies),
            )
            i += 1

        if verbose:
            print(plan_desc)

        # -----------------------------------------------------------

        step_ctx = self.add_ctx(ctx)
        step_ctx.set_input("{num_subtasks_label}: {count}, {plan_label}: {plan_id}".format(
            num_subtasks_label=trans('msg.agent.plan.num_subtasks'),
            count=str(c),
            plan_label=trans('msg.agent.plan'),
            plan_id=plan_id,
        ))
        step_ctx.set_output(plan_desc)
        step_ctx.cmds = []
        self.send_response(step_ctx, signals, KernelEvent.APPEND_DATA)  # send plan description

        i = 1
        for sub_task in plan.sub_tasks:
            if self.is_stopped():
                break

            self.set_busy(signals)

            j = 1
            task = agent.state.get_task(sub_task.name)

            self.set_status(signals, trans("status.agent.reasoning"))
            step_output = agent.run_step(task.task_id)
            tools_output = self.window.core.agents.tools.export_sources(step_output.output)

            task_header = "\n"
            task_header += "\n**===== Sub Task {index}: {sub_task_name} =====**".format(
                index=str(i),
                sub_task_name=sub_task.name
            )
            task_header += "\nExpected output: {expected_output}".format(
                expected_output=str(sub_task.expected_output)
            )
            task_header += "\nDependencies: {dependencies}".format(
                dependencies=str(sub_task.dependencies)
            )

            if verbose:
                print(task_header)

            # this can be the last step in current sub-task, so send it first
            step_ctx = self.add_ctx(ctx)
            step_ctx.set_input(str(tools_output))  # TODO: tool_outputs?
            step_ctx.set_output("`{sub_task_label} {i}/{c}, {step_label} {j}`\n{task_header}".format(
                sub_task_label=trans('msg.agent.plan.subtask'),
                i=str(i),
                c=str(c),
                step_label=trans('msg.agent.step'),
                j=str(j),
                task_header=task_header
            ))
            self.copy_step_results(step_ctx, ctx, tools_output)
            step_ctx.extra["agent_step"] = True
            self.send_response(step_ctx, signals, KernelEvent.APPEND_DATA)

            # -----------------------------------------------------------

            # loop until the last step is reached, if first step is not last
            while not step_output.is_last:
                if self.is_stopped():
                    break

                self.set_busy(signals)

                step_output = agent.run_step(task.task_id)
                tools_output = self.window.core.agents.tools.export_sources(step_output.output)

                # do not send again the first step (it was sent before the loop)
                if j > 1:
                    step_ctx = self.add_ctx(ctx)
                    step_ctx.set_input(str(tools_output))
                    step_ctx.set_output("`{sub_task_label} {i}/{c}, {step_label} {j}`\n{task_header}".format(
                        sub_task_label=trans('msg.agent.plan.subtask'),
                        i=str(i),
                        c=str(c),
                        step_label=trans('msg.agent.step'),
                        j=str(j),
                        task_header=task_header
                    ))
                    self.copy_step_results(step_ctx, ctx, tools_output)
                    step_ctx.extra["agent_step"] = True
                    self.send_response(step_ctx, signals, KernelEvent.APPEND_DATA)
                j += 1

            # finalize the response and commit to memory
            extra = {}
            extra["agent_output"] = True,  # mark as output response (will be attached to ctx items on continue)

            if i == c:  # if last subtask
                extra["agent_finish"] = True

            if self.is_stopped():
                return True  # abort if stopped

            # there is no tool calls here, only final response
            if step_output.is_last:
                response = agent.finalize_response(task.task_id, step_output=step_output)
                response_ctx = self.add_ctx(ctx)
                response_ctx.set_input(str(tools_output))
                response_ctx.set_output(str(response))
                response_ctx.extra.update(extra)  # extend with `agent_output` and `agent_finish`
                self.send_response(response_ctx, signals, KernelEvent.APPEND_DATA)
            i += 1

        return True

    def run_plan_once(
            self,
            agent: Any,
            ctx: CtxItem,
            prompt: str,
            verbose: bool = False
    ) -> Union[None, CtxItem]:
        """
        Run agent sub-tasks

        :param agent: Agent instance
        :param ctx: Input context
        :param prompt: input text
        :param verbose: verbose mode
        :return: CtxItem with final response or None if stopped
        """

        verbose = True
        if self.is_stopped():
            return  # abort if stopped

        plan_id = agent.create_plan(self.prepare_input(prompt))
        plan = agent.state.plan_dict[plan_id]
        c = len(plan.sub_tasks)

        # prepare plan description
        plan_desc = "`{current_plan}:`\n".format(
            current_plan=trans('msg.agent.plan.current')
        )
        for sub_task in plan.sub_tasks:
            plan_desc += "\n\n"
            plan_desc += "\n**===== {sub_task_label}: {sub_task_name} =====**".format(
                sub_task_label=trans('msg.agent.plan.subtask'),
                sub_task_name=sub_task.name,
            )
            plan_desc += "\n{expected_label}: {expected_output}".format(
                expected_label=trans('msg.agent.plan.expected'),
                expected_output=str(sub_task.expected_output),
            )
            plan_desc += "\n{deps_label}: {dependencies}".format(
                deps_label=trans('msg.agent.plan.deps'),
                dependencies=str(sub_task.dependencies),
            )

        if verbose:
            print(plan_desc)

        plan_ctx = self.add_ctx(ctx)
        plan_ctx.set_input("{num_subtasks_label}: {count}, {plan_label}: {plan_id}".format(
            num_subtasks_label=trans('msg.agent.plan.num_subtasks'),
            count=str(c),
            plan_label=trans('msg.agent.plan'),
            plan_id=plan_id,
        ))
        plan_ctx.set_output(plan_desc)
        plan_ctx.cmds = []

        all_steps_results = []

        i = 1
        for sub_task in plan.sub_tasks:
            if self.is_stopped():
                break

            j = 1
            task = agent.state.get_task(sub_task.name)
            step_output = agent.run_step(task.task_id)
            tools_output = self.window.core.agents.tools.export_sources(step_output.output)

            task_header = "\n"
            task_header += "\n**===== Sub Task {index}: {sub_task_name} =====**".format(
                index=str(i),
                sub_task_name=sub_task.name
            )
            task_header += "\nExpected output: {expected_output}".format(
                expected_output=str(sub_task.expected_output)
            )
            task_header += "\nDependencies: {dependencies}".format(
                dependencies=str(sub_task.dependencies)
            )

            if verbose:
                print(task_header)

            step_ctx = self.add_ctx(ctx)
            step_ctx.set_input(str(tools_output))
            step_ctx.set_output("`{sub_task_label} {i}/{c}, {step_label} {j}`\n{task_header}".format(
                sub_task_label=trans('msg.agent.plan.subtask'),
                i=str(i),
                c=str(c),
                step_label=trans('msg.agent.step'),
                j=str(j),
                task_header=task_header
            ))
            self.copy_step_results(step_ctx, ctx, tools_output)
            step_ctx.extra["agent_step"] = True

            all_steps_results.append(step_ctx)

            # -----------------------------------------------------------
            while not step_output.is_last:
                if self.is_stopped():
                    break

                step_output = agent.run_step(task.task_id)
                tools_output = self.window.core.agents.tools.export_sources(step_output.output)
                j += 1
                step_ctx = self.add_ctx(ctx)
                step_ctx.set_input(str(tools_output))
                step_ctx.set_output("`{sub_task_label} {i}/{c}, {step_label} {j}`\n{task_header}".format(
                    sub_task_label=trans('msg.agent.plan.subtask'),
                    i=str(i),
                    c=str(c),
                    step_label=trans('msg.agent.step'),
                    j=str(j),
                    task_header=task_header
                ))
                self.copy_step_results(step_ctx, ctx, tools_output)
                step_ctx.extra["agent_step"] = True

                all_steps_results.append(step_ctx)

            extra = {}
            extra["agent_output"] = True
            if i == c:
                extra["agent_finish"] = True

            if self.is_stopped():
                return  # abort if stopped

            if step_output.is_last:
                response = agent.finalize_response(task.task_id, step_output=step_output)
                final_ctx = self.add_ctx(ctx)
                final_ctx.set_input(str(tools_output))
                final_ctx.set_output(str(response))
                final_ctx.extra.update(extra)
                all_steps_results.append(final_ctx)
            i += 1

        if all_steps_results:
            return all_steps_results[-1]


    def copy_step_results(
            self,
            step_ctx: CtxItem,
            ctx: CtxItem,
            tools_output: List[Dict[str, Any]]
    ):
        """
        Copy step results from base context item

        INFO: It is required to copy results from previous context item to the current one
        because tool calls store their output in the base context item, so we need to copy it

        :param step_ctx: previous context
        :param ctx: current context
        :param tools_output: tools output
        """
        step_ctx.cmds = tools_output
        step_ctx.results = ctx.results

        # copy extra data (output from plugins)
        if tools_output:
            for k in ctx.extra:
                if not k.startswith("agent_"):  # do not copy `agent_input` and etc.
                    step_ctx.extra[k] = ctx.extra[k]  # copy only plugin output

        # reset input ctx, remove outputs from plugins (tools) from previous step
        for k in list(ctx.extra.keys()):
            if k != "agent_input":
                del ctx.extra[k]

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
        return self.call(context, extra, signals)

    def add_ctx(
            self,
            from_ctx: CtxItem,
            with_tool_outputs: bool = False
    ) -> CtxItem:
        """
        Prepare response context item

        :param from_ctx: CtxItem (parent, source)
        :param with_tool_outputs: True if tool outputs should be copied
        :return: CtxItem with copied data from parent context item
        """
        ctx = CtxItem()
        ctx.meta = from_ctx.meta
        ctx.internal = True
        ctx.current = True  # mark as current context item
        ctx.mode = from_ctx.mode
        ctx.model = from_ctx.model
        ctx.prev_ctx = from_ctx
        ctx.images = from_ctx.images  # copy from parent if appended from plugins
        ctx.urls = from_ctx.urls  # copy from parent if appended from plugins
        ctx.attachments = from_ctx.attachments # copy from parent if appended from plugins
        ctx.files = from_ctx.files  # copy from parent if appended from plugins
        ctx.live = True

        if with_tool_outputs:
            # copy tool outputs from parent context item
            ctx.cmds = copy.deepcopy(from_ctx.cmds)
            ctx.results = copy.deepcopy(from_ctx.results)
            if "tool_output" in from_ctx.extra:
                ctx.extra["tool_output"] = copy.deepcopy(from_ctx.extra["tool_output"])
        return ctx

    def add_next_ctx(
            self,
            from_ctx: CtxItem,
    ) -> CtxItem:
        """
        Prepare next context item (used for new context in the cycle)

        :param from_ctx: CtxItem (parent, source)
        :return: CtxItem with copied data from parent context item
        """
        ctx = CtxItem()
        ctx.meta = from_ctx.meta
        ctx.mode = from_ctx.mode
        ctx.model = from_ctx.model
        ctx.prev_ctx = from_ctx
        # ctx.images = from_ctx.images  # copy from parent if appended from plugins
        # ctx.urls = from_ctx.urls  # copy from parent if appended from plugins
        # ctx.attachments = from_ctx.attachments # copy from parent if appended from plugins
        # ctx.files = from_ctx.files  # copy from parent if appended from plugins
        ctx.extra = from_ctx.extra.copy()  # copy extra data
        return ctx

    def send_stream(
            self,
            ctx: CtxItem,
            signals: BridgeSignals,
            begin: bool=False
    ):
        """
        Send stream chunk to chat window (BridgeSignals)

        :param ctx: CtxItem
        :param signals: BridgeSignals
        :param begin: True if it is the beginning of the text
        """
        if signals is None:
            return
        chunk = ctx.stream.replace("<execute>", "\n```python\n").replace("</execute>", "\n```\n")
        data = {
            "meta": ctx.meta,
            "ctx": ctx,
            "chunk": chunk, # use stream for live output
            "begin": begin,
        }
        event = RenderEvent(RenderEvent.STREAM_APPEND, data)
        signals.response.emit(event)

    def end_stream(self, ctx: CtxItem, signals: BridgeSignals):
        """
        End of stream in chat window (BridgeSignals)

        :param ctx: CtxItem
        :param signals: BridgeSignals
        """
        if signals is None:
            return
        data = {
            "meta": ctx.meta,
            "ctx": ctx,
        }
        event = RenderEvent(RenderEvent.STREAM_END, data)
        signals.response.emit(event)

    def next_stream(self, ctx: CtxItem, signals: BridgeSignals):
        """
        End of stream in chat window (BridgeSignals)

        :param ctx: CtxItem
        :param signals: BridgeSignals
        """
        if signals is None:
            return
        data = {
            "meta": ctx.meta,
            "ctx": ctx,
        }
        event = RenderEvent(RenderEvent.STREAM_NEXT, data)
        signals.response.emit(event)

    def send_response(
            self,
            ctx: CtxItem,
            signals: BridgeSignals,
            event_name: str,
            **kwargs
    ):
        """
        Send async response to chat window (BridgeSignals)

        :param ctx: CtxItem
        :param signals: BridgeSignals
        :param event_name: kernel event
        :param kwargs: extra data
        """
        if signals is None:
            return
        context = BridgeContext()
        context.ctx = ctx
        event = KernelEvent(event_name, {
            'context': context,
            'extra': kwargs,
        })
        signals.response.emit(event)

    def set_busy(
            self,
            signals: BridgeSignals,
            **kwargs
    ):
        """
        Set busy status

        :param signals: BridgeSignals
        :param kwargs: extra data
        """
        if signals is None:
            return
        data = {
            "id": "agent",
            "msg": trans("status.agent.reasoning"),
        }
        event = KernelEvent(KernelEvent.STATE_BUSY, data)
        data.update(kwargs)
        signals.response.emit(event)

    def set_idle(
            self,
            signals: BridgeSignals,
            **kwargs
    ):
        """
        Set idle status

        :param signals: BridgeSignals
        :param kwargs: extra data
        """
        if signals is None:
            return
        data = {
            "id": "agent",
        }
        event = KernelEvent(KernelEvent.STATE_IDLE, data)
        data.update(kwargs)
        signals.response.emit(event)

    def set_status(
            self,
            signals: BridgeSignals,
            msg: str
    ):
        """
        Set busy status

        :param signals: BridgeSignals
        :param msg: status message
        """
        if signals is None:
            return
        data = {
            "status": msg,
        }
        event = KernelEvent(KernelEvent.STATUS, data)
        signals.response.emit(event)

    def prepare_input(self, prompt: str) -> str:
        """
        Prepare input context

        :param prompt: input text
        """
        event = Event(Event.AGENT_PROMPT, {
            'value': prompt,
        })
        self.window.dispatch(event)
        return event.data['value']

    def is_stopped(self) -> bool:
        """
        Check if run is stopped

        :return: True if stopped
        """
        return self.window.controller.kernel.stopped()

    def get_error(self) -> Optional[Exception]:
        """
        Get last error

        :return: last exception or None if no error
        """
        return self.error

    def extract_final_response(self, input_text: str) -> Tuple[str, str]:
        pattern = r"\s*Thought:(.*?)Answer:(.*?)(?:$)"

        match = re.search(pattern, input_text, re.DOTALL)
        if not match:
            return "", ""

        thought = match.group(1).strip()
        answer = match.group(2).strip()
        return thought, answer
