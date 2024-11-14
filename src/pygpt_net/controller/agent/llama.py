#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.14 01:00:00                  #
# ================================================== #

from pygpt_net.core.ctx.reply import ReplyContext
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

    def flow_begin(self):
        """Run begin"""
        self.iteration = 0  # reset iteration
        self.window.controller.agent.flow.stop = False  # reset stop flag
        self.update()  # update status

    def flow_continue(self, ctx: CtxItem):
        """
        Handle run continue

        :param ctx: CtxItem
        """
        if type(ctx.extra) == dict and ctx.extra.get("agent_finish", False):
            self.flow_end()  # end of run
            """
            # TODO: implement agent continue in future
            if self.window.core.config.get("agent.continue.always"):
                if self.window.controller.agent.flow.stop:
                    self.flow_end()  # end of run
                    return  # abort if stop flag is set
                max_iterations = self.window.core.config.get("agent.iterations", 3)
                if max_iterations != 0:
                    if self.iteration >= max_iterations:
                        self.flow_end()  # end of run
                        return  # abort if max iterations reached
                reply = ReplyContext()
                reply.type = ReplyContext.AGENT_CONTINUE
                reply.ctx = ctx
                reply.input = self.window.core.config.get("prompt.agent.continue.llama")
                self.iteration += 1
                self.update()  # update status
                self.window.controller.chat.reply.add(reply)  # add to reply stack
                self.window.controller.chat.reply.handle()  # send reply
            else:
                self.flow_end()  # end of run
            """

    def flow_end(self):
        """End of run"""
        # self.update()  # update status
        self.iteration = 0  # reset iteration
        self.window.controller.agent.flow.stop = False  # reset stop flag
        self.window.ui.status(trans('status.finished'))  # show info
        if self.window.core.config.get("agent.goal.notify"):
            self.window.ui.tray.show_msg(
                trans("notify.agent.goal.title"),
                trans("notify.agent.goal.content"),
            )

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