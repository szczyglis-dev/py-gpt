#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.28 16:00:00                  #
# ================================================== #

from typing import Any

from pygpt_net.core.types import (
    MODE_AGENT,
)
from pygpt_net.core.events import KernelEvent, RenderEvent, Event
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.ctx.reply import ReplyContext
from pygpt_net.item.ctx import CtxItem


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
        if self.window.controller.kernel.stopped():
            return

        mode = self.window.core.config.get('mode')

        # extract commands
        cmds = ctx.cmds_before  # from llama index tool calls pre-handler
        if not cmds:  # if no commands in context (from llama index tool calls)
            cmds = self.window.core.command.extract_cmds(ctx.output)

        if len(cmds) > 0:
            # check if commands are enabled, leave only enabled commands
            for cmd in cmds:
                cmd_id = str(cmd["cmd"])
                if not self.window.core.command.is_enabled(cmd_id):
                    self.log("[cmd] Command not allowed: " + cmd_id)
                    cmds.remove(cmd)  # remove command from execution list
            if len(cmds) == 0:
                return  # abort if no commands

            ctx.cmds = cmds  # append commands to ctx
            self.log("[cmd] Command call received...")

            # agent mode
            if mode == MODE_AGENT:
                commands = self.window.core.command.from_commands(cmds)  # pack to execution list
                self.window.controller.agent.legacy.on_cmd(
                    ctx,
                    commands,
                )

            # plugins
            self.log("[cmd] Preparing command reply context...")

            reply = ReplyContext()
            reply.ctx = ctx
            reply.cmds = cmds
            if self.window.core.config.get('cmd'):
                reply.type = ReplyContext.CMD_EXECUTE
            else:
                reply.type = ReplyContext.CMD_EXECUTE_INLINE

            data = {
                "meta": ctx.meta,
            }
            event = RenderEvent(RenderEvent.TOOL_BEGIN, data)
            self.window.dispatch(event)  # show waiting
            context = BridgeContext()
            context.ctx = ctx
            context.reply_context = reply
            event = KernelEvent(KernelEvent.TOOL_CALL, {
                'context': context,
                'extra': {},
            })
            self.window.dispatch(event)

    def log(self, data: Any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)
