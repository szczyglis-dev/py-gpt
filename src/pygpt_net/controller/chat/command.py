#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.25 06:00:00                  #
# ================================================== #

import copy
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

    def handle(self, ctx: CtxItem, internal: bool = False) -> Any:
        """
        Handle commands and expert mentions

        :param ctx: CtxItem
        :param internal: Internal flag, if True then skip some checks
        """
        if self.window.controller.kernel.stopped():
            return

        mode = self.window.core.config.get('mode')

        # extract commands
        cmds = ctx.cmds_before  # from llama index tool calls pre-handler
        if not cmds:  # if no commands in context (from llama index tool calls)
            cmds = self.window.core.command.extract_cmds(ctx.output)

        if len(cmds) > 0:
            all_cmds = copy.deepcopy(cmds)
            # check if commands are enabled, leave only enabled commands
            for cmd in list(cmds):
                if "cmd" not in cmd:
                    self.log("[cmd] Command without 'cmd' key: " + str(cmd))
                    cmds.remove(cmd)
                    continue
                cmd_id = str(cmd["cmd"])
                if not self.window.core.command.is_enabled(cmd_id):
                    self.log("[cmd] Command not allowed: " + cmd_id)
                    cmds.remove(cmd)  # remove command from execution list

            # agent mode
            if mode == MODE_AGENT:
                commands = self.window.core.command.from_commands(cmds)  # pack to execution list
                self.window.controller.agent.legacy.on_cmd(
                    ctx,
                    commands,
                    all_cmds,
                )

            if len(cmds) == 0:
                return  # abort if no commands

            ctx.cmds = cmds  # append commands to ctx
            self.log("[cmd] Command call received...")

            # plugins
            self.log("[cmd] Preparing command reply context...")

            reply = ReplyContext()
            reply.ctx = ctx
            reply.cmds = cmds
            reply.internal = internal
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

            if internal:
                ctx.agent_call = True
                if reply.type == ReplyContext.CMD_EXECUTE:
                    self.window.controller.plugins.apply_cmds(
                        reply.ctx,
                        reply.cmds,
                    )
                elif reply.type == ReplyContext.CMD_EXECUTE_INLINE:
                    self.window.controller.plugins.apply_cmds_inline(
                        reply.ctx,
                        reply.cmds,
                    )
                return ctx.results
            else:
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
