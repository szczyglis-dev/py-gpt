#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.11 19:00:00                  #
# ================================================== #

import asyncio
from typing import Optional, Dict, Any, List

from llama_index.core.tools import FunctionTool
from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import (
    ToolCall,
    ToolCallResult,
    AgentStream,
)

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.events import Event, KernelEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


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
            tools = self.window.core.agents.tools.prepare(context, extra)
            plugin_tools = self.window.core.agents.tools.get_plugin_tools(context, extra)
            plugin_specs = self.window.core.agents.tools.get_plugin_specs(context, extra)
            retriever_tool = self.window.core.agents.tools.get_retriever_tool(context, extra)
            history = self.window.core.agents.memory.prepare(context)
            llm = self.window.core.idx.llm.get(model, stream=False)
            workdir = self.window.core.config.get_user_dir('data')
            if self.window.core.plugins.get_option("cmd_code_interpreter", "sandbox_ipython"):
                workdir = "/data"

            provider = None
            agent = None
            if self.window.core.agents.provider.has(id):
                kwargs = {
                    "context": context,
                    "tools": tools,
                    "plugin_tools": plugin_tools,
                    "plugin_specs": plugin_specs,
                    "retriever_tool": retriever_tool,
                    "llm": llm,
                    "chat_history": history,
                    "max_iterations": max_steps,
                    "verbose": verbose,
                    "system_prompt": system_prompt,
                    "are_commands": self.window.core.config.get("cmd"),
                    "workdir": workdir,
                }
                provider = self.window.core.agents.provider.get(id)
                agent = provider.get_agent(self.window, kwargs)
                if verbose:
                    print("Using Agent: " + str(id) + ", model: " + str(model.id))

            if agent is None:
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
            if mode == "plan":
                return self.run_plan(**kwargs)
            elif mode == "step":
                return self.run_steps(**kwargs)
            elif mode == "assistant":
                return self.run_assistant(**kwargs)
            elif mode == "workflow":
                kwargs["history"] = history
                kwargs["llm"] = llm
                return asyncio.run(self.run_workflow(**kwargs))

        except Exception as err:
            self.window.core.debug.error(err)
            self.error = err
            return False

    async def run_agent_workflow(self, agent, ctx, query, memory, verbose=False):
        """
        Run agent workflow
        This method runs the agent's workflow, processes tool calls, and streams events.

        :param agent: Agent instance
        :param ctx: Context
        :param query: Input query string
        :param memory: Memory buffer for the agent
        :param verbose: Verbose mode (default: False)
        :return: handler for the agent workflow
        """
        handler = agent.run(query, ctx=ctx, memory=memory, verbose=verbose)
        print(f"User:  {query}")
        async for event in handler.stream_events():
            if self.is_stopped():
                break
            if isinstance(event, ToolCallResult):
                print(
                    f"\n-----------\nCode execution result:\n{event.tool_output}"
                )
            elif isinstance(event, ToolCall):
                if "code" in event.tool_kwargs:
                    print(f"\n-----------\nParsed code:\n{event.tool_kwargs['code']}")
            elif isinstance(event, AgentStream):
                print(f"{event.delta}", end="", flush=True)
                # TODO: send stream to webview

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
        response = await self.run_agent_workflow(
            agent=agent,
            ctx=agent_ctx,
            query=prompt,
            memory=memory,
            verbose=verbose,
        )
        response_ctx = self.add_ctx(ctx)
        response_ctx.set_input("inp")
        response_ctx.set_output(str(response))
        response_ctx.extra["agent_output"] = True  # mark as output response
        response_ctx.extra["agent_finish"] = True  # mark as finished

        # if there are tool outputs, img, files, append it to the response context
        self.window.core.agents.tools.append_tool_outputs(response_ctx)

        # send response
        self.send_response(response_ctx, signals, KernelEvent.APPEND_DATA)
        self.set_idle(signals)
        return True

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
            step_ctx.set_input(str(tools_output)) # TODO: tool_outputs?
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

            # the is no tool calls here, only final response
            if step_output.is_last:
                response = agent.finalize_response(task.task_id, step_output=step_output)
                response_ctx = self.add_ctx(ctx)
                response_ctx.set_input(str(tools_output))
                response_ctx.set_output(str(response))
                response_ctx.extra.update(extra)  # extend with `agent_output` and `agent_finish`
                self.send_response(response_ctx, signals, KernelEvent.APPEND_DATA)
            i += 1

        return True

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
        prompt = self.window.core.agents.observer.evaluation.get_prompt(history)
        tools = self.window.core.agents.observer.evaluation.get_tools()

        # evaluate
        self.set_busy(signals)
        self.next_instruction = ""  # reset
        self.prev_score = -1  # reset
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
        preset = self.window.controller.presets.get_current()
        extra = {
            "agent_idx": preset.idx,
            "agent_provider": preset.agent_provider,
        }
        context.model = self.window.core.models.get(self.window.core.config.get('model'))
        return self.call(context, extra, signals)

    def add_ctx(
            self,
            from_ctx: CtxItem
    ) -> CtxItem:
        """
        Add context item

        :param from_ctx: CtxItem (parent, source)
        :return: CtxItem
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
        ctx.live = True
        return ctx

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
