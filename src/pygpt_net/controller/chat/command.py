#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.28 16:00:00                  #
# ================================================== #

from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Command:
    def __init__(self, window=None):
        """
        Command controller

        :param window: Window instance
        """
        self.window = window

    def handle(self, ctx: CtxItem):
        """
        Handle commands and expert mentions

        :param ctx: CtxItem
        """
        mode = self.window.core.config.get('mode')

        # extract commands
        cmds = self.window.core.command.extract_cmds(ctx.output)
        if len(cmds) > 0:
            ctx.cmds = cmds  # append commands to ctx
            self.log("Command call received...")
            # agent mode
            if mode == 'agent':
                commands = self.window.core.command.from_commands(cmds)  # pack to execution list
                self.window.controller.agent.flow.on_cmd(
                    ctx,
                    commands,
                )
                # check if agent flow is not finished
                if self.window.controller.agent.flow.finished:
                    pass
                    # allow to continue commands execution if agent flow is finished
                    # return

            # don't change status if only goal update command
            change_status = True
            if mode == 'agent':
                if len(cmds) == 1 and cmds[0]["cmd"] == "goal_update":
                    change_status = False

            # plugins
            if self.window.core.config.get('cmd'):
                if change_status:
                    self.log("Executing plugin commands...")
                    self.window.ui.status(trans('status.cmd.wait'))
                self.window.controller.plugins.apply_cmds(
                    ctx,
                    cmds,
                )
            else:
                self.window.controller.plugins.apply_cmds_inline(
                    ctx,
                    cmds,
                )
    def log(self, data: any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)
