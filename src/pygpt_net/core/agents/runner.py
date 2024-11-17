#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 03:00:00                  #
# ================================================== #

from pygpt_net.core.bridge import BridgeContext, BridgeSignals
from pygpt_net.core.dispatcher import Event
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
        if self.is_stopped():
            return True  # abort if stopped

        id = extra.get("agent_provider", "openai")
        verbose = self.window.core.config.get("agent.llama.verbose", False)
        try:
            # prepare input context
            ctx = context.ctx
            if type(ctx.extra) == dict:
                ctx.extra["agent_input"] = True  # only append, do not overwrite
            else:
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
        if self.is_stopped():
            return True  # abort if stopped

        is_last = False
        task = agent.create_task(self.prepare_input(ctx.input))
        tools_output = None

        # run steps
        i = 1
        while not is_last:
            if self.is_stopped():
                break  # handle force stop

            step_output = agent.run_step(task.task_id)
            is_last = step_output.is_last
            # append each step to chat output, last step = final response, so we skip it
            tools_output = self.window.core.agents.tools.export_sources(step_output.output)
            if not is_last:
                step_ctx = self.add_ctx(ctx)
                step_ctx.set_input(str(tools_output))
                step_ctx.set_output("`{step_label} {i}`".format(
                    step_label=trans('msg.agent.step'),
                    i=str(i)
                ))
                step_ctx.cmds = tools_output
                step_ctx.extra = {
                    "agent_step": True,
                }
                signals.on_step.emit(step_ctx)
            i += 1

        # final response
        if is_last:
            if self.is_stopped():
                return True  # abort if stopped
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
        response = agent.chat(self.prepare_input(ctx.input))
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
        if self.is_stopped():
            return True  # abort if stopped

        plan_id = agent.create_plan(
            self.prepare_input(ctx.input)
        )
        plan = agent.state.plan_dict[plan_id]
        c = len(plan.sub_tasks)

        # send plan description
        plan_desc = "`{current_plan}:`\n".format(
            current_plan=trans('msg.agent.plan.current')
        )
        i = 1
        for sub_task in plan.sub_tasks:
            plan_desc += "\n\n"
            plan_desc += "\n**===== {sub_task_label}: {sub_task_name} =====**".format(
                sub_task_label=trans('msg.agent.plan.sub_task'),
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

        step_ctx = self.add_ctx(ctx)
        step_ctx.set_input("{num_subtasks_label}: {count}, {plan_label}: {plan_id}".format(
            num_subtasks_label=trans('msg.agent.plan.num_subtasks'),
            count=str(c),
            plan_label=trans('msg.agent.plan'),
            plan_id=plan_id,
        ))
        step_ctx.set_output(plan_desc)
        step_ctx.cmds = []
        signals.on_step.emit(step_ctx)

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

            # loop until the last step is reached
            while not step_output.is_last:
                if self.is_stopped():
                    break

                step_output = agent.run_step(task.task_id)
                step_ctx = self.add_ctx(ctx)
                step_ctx.set_input(str(tools_output))
                step_ctx.set_output("`{sub_task_label} {i}/{c}, {step_label} {j}`\n{task_header}".format(
                    sub_task_label=trans('msg.agent.plan.sub_task'),
                    i=str(i),
                    c=str(c),
                    step_label=trans('msg.agent.step'),
                    j=str(j),
                    task_header=task_header
                ))
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

            if self.is_stopped():
                return True  # abort if stopped

            if step_output.is_last:
                response = agent.finalize_response(task.task_id, step_output=step_output)
                response_ctx = self.add_ctx(ctx)
                response_ctx.set_input(str(tools_output))
                response_ctx.set_output(str(response))
                response_ctx.extra = extra
                signals.on_step.emit(response_ctx)
            i += 1

        return True

    def run_once(self, input: str, tools: list, model_name) -> str:
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
        llm = self.window.core.idx.llm.get(model)
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

    def run_next(self, context: BridgeContext, extra: dict, signals: BridgeSignals) -> bool:
        """
        Evaluate a response and run next step

        :param context: BridgeContext
        :param extra: extra data
        :param signals: BridgeSignals
        """
        if self.is_stopped():
            return True  # abort if stopped

        ctx = context.ctx
        signals.on_begin.emit(ctx, "")  # lock input, show stop btn
        history = context.history
        prompt = self.window.core.agents.observer.evaluation.get_prompt(history)
        tools = self.window.core.agents.observer.evaluation.get_tools()

        # evaluate
        self.next_instruction = ""  # reset
        self.prev_score = -1  # reset
        self.run_once(prompt, tools, ctx.model)  # tool will update evaluation
        return self.handle_evaluation(ctx, self.next_instruction, self.prev_score, signals)

    def handle_evaluation(self, ctx: CtxItem, instruction: str, score: int, signals: BridgeSignals):
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
        signals.on_evaluate.emit("{score_label}: {score}%".format(
            score_label=trans('eval.score'),
            score=str(score)
        ))

        if score < 0:
            signals.on_end.emit(ctx)
            return True
        good_score = self.window.core.config.get("agent.llama.loop.score", 75)
        if score >= good_score != 0:
            signals.on_end.emit(ctx, "{status_finished} {score_label}: {score}%".format(
                status_finished=trans('status.finished'),
                score_label=trans('eval.score'),
                score=str(score)
            ))
            return True

        #print("Instruction: " + instruction, "Score: " + str(score))
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
        signals.on_step.emit(step_ctx)

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

    def prepare_input(self, prompt: str) -> str:
        """
        Prepare input context

        :param prompt: input text
        """
        event = Event(Event.AGENT_PROMPT, {
            'value': prompt,
        })
        self.window.core.dispatcher.dispatch(event)
        return event.data['value']

    def is_stopped(self) -> bool:
        """
        Check if run is stopped

        :return: True if stopped
        """
        return self.window.controller.chat.input.stop or self.window.controller.agent.flow.stop

    def get_error(self) -> Exception or None:
        """
        Get last error

        :return: last exception or None if no error
        """
        return self.error
