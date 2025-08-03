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

from typing import Any, Union

from pygpt_net.core.bridge.worker import BridgeSignals
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans

from .base import BaseRunner


class LlamaSteps(BaseRunner):
    def __init__(self, window=None):
        """
        Agent runner

        :param window: Window instance
        """
        super(LlamaSteps, self).__init__(window)
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

    def run_once(
            self,
            agent: Any,
            ctx: CtxItem,
            prompt: str,
            verbose: bool = False
    ) -> Union[CtxItem, None]:
        """
        Run agent steps once

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