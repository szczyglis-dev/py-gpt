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

from pygpt_net.core.ctx.reply import ReplyContext
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
        if self.window.controller.chat.common.stopped():
            return

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

            # plugins
            self.log("Preparing command reply context...")
            reply = ReplyContext()
            reply.ctx = ctx
            reply.cmds = cmds
            if self.window.core.config.get('cmd'):
                reply.type = ReplyContext.CMD_EXECUTE
            else:
                reply.type = ReplyContext.CMD_EXECUTE_INLINE

            self.window.controller.chat.reply.add(reply)  # send command execution to reply stack

    def log(self, data: any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)
