#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.15 00:00:00                  #
# ================================================== #

from pygpt_net.core.bridge import BridgeContext, BridgeSignals
from pygpt_net.item.ctx import CtxItem


class Runner:
    def __init__(self, window=None):
        """
        Agent runner

        :param window: Window instance
        """
        self.window = window
        self.signals = None  # BridgeSignals
        self.error = None  # last exception

    def call(
            self,
            context: BridgeContext,
            extra: dict,
            signals: BridgeSignals
    ) -> bool:
        """
        Call an agent

        :param context: BridgeContext
        :param extra: extra data
        :param signals: BridgeSignals
        :return: True if success
        """
        id = extra.get("agent_provider", "openai")
        verbose = self.window.core.config.get("agent.llama.verbose", False)
        try:
            # prepare input context
            ctx = context.ctx
            ctx.extra = {
                "agent_input": True,  # mark as user input
            }
            ctx.agent_call = True  # disables reply from plugin commands

            # prepare agent
            model = context.model
            max_steps = self.window.core.config.get("agent.llama.steps", 10)
            tools = self.window.core.agents.tools.prepare(context, extra)
            history = self.window.core.agents.memory.prepare(context)
            llm = self.window.core.idx.llm.get(model)

            provider = None
            agent = None
            if self.window.core.agents.provider.has(id):
                kwargs = {
                    "context": context,
                    "tools": tools,
                    "llm": llm,
                    "chat_history": history,
                    "max_iterations": max_steps,
                    "verbose": verbose,
                }
                provider = self.window.core.agents.provider.get(id)
                agent = provider.get_agent(self.window, kwargs)
                if verbose:
                    print("Using Agent: " + id + ", model: " + model.id)

            if agent is None:
                raise Exception("Agent not found: " + id)

            # run agent
            mode = provider.get_mode()
            kwargs = {
                "agent": agent,
                "ctx": ctx,
                "signals": signals,
                "verbose": verbose,
            }
            if mode == "plan":
                return self.run_plan(**kwargs)
            elif mode == "step":
                return self.run_steps(**kwargs)
            elif mode == "assistant":
                return self.run_assistant(**kwargs)

        except Exception as err:
            self.window.core.debug.error(err)
            self.error = err
            return False

    def run_steps(
            self,
            agent,
            ctx: CtxItem,
            signals: BridgeSignals,
            verbose: bool = False
    ) -> bool:
        """
        Run agent steps

        :param agent: Agent instance
        :param ctx: Input context
        :param signals: BridgeSignals
        :param verbose: verbose mode
        :return: True if success
        """
        is_last = False
        task = agent.create_task(ctx.input)
        tools_output = None

        # run steps
        i = 1
        while not is_last:
            if self.window.controller.agent.llama.is_stopped():
                break  # handle force stop
            step_output = agent.run_step(task.task_id)
            is_last = step_output.is_last
            # append each step to chat output, last step = final response, so we skip it
            tools_output = self.window.core.agents.tools.export_sources(step_output.output)
            if not is_last:
                step_ctx = self.add_ctx(ctx)
                step_ctx.set_input(str(tools_output))
                step_ctx.set_output("`Step " + str(i) + "`")
                step_ctx.cmds = tools_output
                step_ctx.extra = {
                    "agent_step": True,
                }
                signals.on_step.emit(step_ctx)
            i += 1

        # final response
        response = agent.finalize_response(task.task_id)
        response_ctx = self.add_ctx(ctx)
        response_ctx.set_input(str(tools_output))
        response_ctx.set_output(str(response))
        response_ctx.extra = {
            "agent_output": True,  # mark as output response
            "agent_finish": True,  # mark as finished
        }
        signals.on_step.emit(response_ctx)
        return True

    def run_assistant(
            self,
            agent,
            ctx: CtxItem,
            signals: BridgeSignals,
            verbose: bool = False
    ) -> bool:
        """
        Run agent steps

        :param agent: Agent instance
        :param ctx: Input context
        :param signals: BridgeSignals
        :param verbose: verbose mode
        :return: True if success
        """
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

        # final response
        response = agent.chat(ctx.input)
        response_ctx = self.add_ctx(ctx)
        response_ctx.thread = thread_id
        response_ctx.set_input("Assistant")
        response_ctx.set_output(str(response))
        response_ctx.extra = {
            "agent_output": True,  # mark as output response
            "agent_finish": True,  # mark as finished
        }
        signals.on_step.emit(response_ctx)
        return True

    def run_plan(
            self,
            agent,
            ctx: CtxItem,
            signals: BridgeSignals,
            verbose: bool = False
    ) -> bool:
        """
        Run agent sub-tasks

        :param agent: Agent instance
        :param ctx: Input context
        :param signals: BridgeSignals
        :param verbose: verbose mode
        :return: True if success
        """
        plan_id = agent.create_plan(
            ctx.input
        )
        plan = agent.state.plan_dict[plan_id]
        c = len(plan.sub_tasks)

        # send plan description
        plan_desc = "`Current plan:`\n"
        i = 1
        for sub_task in plan.sub_tasks:
            plan_desc += "\n\n"
            plan_desc += "\n**===== Sub Task "+str(i)+": " + sub_task.name + " =====**"
            plan_desc += "\nExpected output: " + str(sub_task.expected_output)
            plan_desc += "\nDependencies: " + str(sub_task.dependencies)
            i += 1

        if verbose:
            print(plan_desc)

        step_ctx = self.add_ctx(ctx)
        step_ctx.set_input("Num of subtasks: " + str(c) + ", Plan: " + plan_id)
        step_ctx.set_output(plan_desc)
        step_ctx.cmds = []
        signals.on_step.emit(step_ctx)

        i = 1
        for sub_task in plan.sub_tasks:
            j = 1
            task = agent.state.get_task(sub_task.name)
            step_output = agent.run_step(task.task_id)
            tools_output = self.window.core.agents.tools.export_sources(step_output.output)

            task_header = "\n"
            task_header += "\n**===== Sub Task: " + sub_task.name + " =====**"
            task_header += "\nExpected output: " +  str(sub_task.expected_output)
            task_header += "\nDependencies: " + str(sub_task.dependencies)

            if verbose:
                print(task_header)

            # loop until the last step is reached
            while not step_output.is_last:
                step_output = agent.run_step(task.task_id)
                step_ctx = self.add_ctx(ctx)
                step_ctx.set_input(str(tools_output))
                step_ctx.set_output("`Subtask " + str(i) + "/" + str(c) + ", Step " + str(j) + "`\n" + task_header)
                step_ctx.cmds = tools_output
                step_ctx.extra = {
                    "agent_step": True,
                }
                signals.on_step.emit(step_ctx)
                j += 1

            # finalize the response and commit to memory
            extra = {
                "agent_output": True,  # mark as output response
            }
            if i == c:  # if last subtask
                extra["agent_finish"] = True
            response = agent.finalize_response(task.task_id, step_output=step_output)
            response_ctx = self.add_ctx(ctx)
            response_ctx.set_input(str(tools_output))
            response_ctx.set_output(str(response))
            response_ctx.extra = extra
            signals.on_step.emit(response_ctx)
            i += 1

        return True

    def add_ctx(self, from_ctx: CtxItem) -> CtxItem:
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

    def get_error(self) -> Exception or None:
        """
        Get last error

        :return: last exception or None if no error
        """
        return self.error
