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

from typing import Dict, Any, List, Union

from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

from .base import BaseRunner


class LlamaPlan(BaseRunner):
    def __init__(self, window=None):
        """
        Agent runner

        :param window: Window instance
        """
        super(LlamaPlan, self).__init__(window)
        self.window = window

    def run(
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

    def run_once(
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