#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 21:00:00                  #
# ================================================== #

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Llama:
    def __init__(self, window=None):
        """
        Agents (Llama-index) controller

        :param window: Window instance
        """
        self.window = window
        self.iteration = 0
        self.eval_step = 0

    def reset_eval_step(self):
        """Reset evaluation step"""
        self.eval_step = 0

    def eval_step_next(self):
        """Next evaluation step"""
        self.eval_step += 1

    def get_eval_step(self) -> int:
        """
        Get evaluation step

        :return: evaluation step
        """
        return self.eval_step

    def flow_begin(self):
        """Run begin"""
        self.iteration = 0  # reset iteration
        self.window.controller.agent.flow.stop = False  # reset stop flag
        self.update()  # update status

    def flow_end(self):
        """End of run"""
        # self.update()  # update status
        self.iteration = 0  # reset iteration
        self.eval_step = 0  # reset evaluation step
        self.window.controller.agent.flow.stop = False  # reset stop flag
        if self.window.core.config.get("agent.goal.notify"):
            self.window.ui.tray.show_msg(
                trans("notify.agent.goal.title"),
                trans("notify.agent.goal.content"),
            )

    def on_finish(self, ctx: CtxItem):
        """
        Finish agent run

        :param ctx: CtxItem
        """
        if not self.window.core.config.get("agent.llama.loop.enabled"):
            self.flow_end()
            return  # abort if loop is disabled

        # check if not stopped
        if self.is_stopped():
            self.flow_end()
            return

        # check max steps
        max_steps = int(self.window.core.config.get("agent.llama.max_eval"))
        if max_steps != 0 and self.get_eval_step() >= max_steps:
            self.flow_end()
            return  # abort if max steps reached

        # eval step++
        self.eval_step_next()

        context = BridgeContext()
        context.ctx = ctx
        context.history = self.window.core.ctx.all(meta_id=ctx.meta.id)
        self.window.update_status(trans('status.evaluating'))  # show info
        event = KernelEvent(KernelEvent.REQUEST_NEXT, {
            'context': context,
            'extra': {},
        })
        self.window.dispatch(event)

    def update(self):
        """Update agent status"""
        # get iterations
        iterations = int(self.window.core.config.get("agent.iterations"))
        if iterations == 0:
            iterations_str = "∞"  # infinity loop
        else:
            iterations_str = str(iterations)

        status = str(self.iteration) + " / " + iterations_str
        self.window.ui.nodes['status.agent'].setText(status)
        self.window.controller.agent.common.toggle_status()

    def is_stopped(self) -> bool:
        """
        Check if run is stopped

        :return: True if stopped
        """
        return self.window.controller.agent.flow.stop