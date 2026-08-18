#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.20 09:00:00                  #
# ================================================== #

import copy
from typing import Any

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_COMPUTER,
)
from pygpt_net.core.events import KernelEvent, RenderEvent, Event
from pygpt_net.core.bridge import BridgeContext
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
        self.pending_safety_ctx = None

    def has_pending_safety_confirmation(self) -> bool:
        """Return True when a Computer Use operation is paused for user confirmation."""
        return self.pending_safety_ctx is not None

    def _get_safety_warning(self, ctx: CtxItem) -> str:
        """Build localized warning text with optional provider details."""
        warning = trans("computer.safety.warning")
        details = self.window.core.security.get_computer_safety_messages(ctx)
        if details:
            warning += "\n\n" + "\n".join(details)
        return warning

    def _pause_for_safety_confirmation(self, ctx: CtxItem):
        """Pause a provider-flagged Computer Use operation before executing local actions."""
        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        ctx.extra["computer_safety_waiting"] = True
        self.pending_safety_ctx = ctx
        warning = self._get_safety_warning(ctx)
        self.window.dispatch(RenderEvent(RenderEvent.TOOL_UPDATE, {
            "meta": ctx.meta,
            "tool_data": warning,
        }))
        self.window.update_status("")
        self.window.controller.chat.common.unlock_input()
        self.log("[computer] Potentially unsafe operation paused; waiting for user confirmation.")

    def handle_pending_safety_input(self, text: str) -> bool:
        """Consume chat input while a Computer Use safety confirmation is pending."""
        ctx = self.pending_safety_ctx
        if ctx is None:
            return False

        # Do not keep a stale confirmation gate after leaving Computer Use mode.
        if self.window.core.config.get("mode") != MODE_COMPUTER:
            self.pending_safety_ctx = None
            return False

        value = str(text or "").strip().lower()
        if value != "continue":
            self.window.dispatch(RenderEvent(RenderEvent.TOOL_UPDATE, {
                "meta": ctx.meta,
                "tool_data": self._get_safety_warning(ctx),
            }))
            return True

        self.pending_safety_ctx = None
        self.window.core.security.mark_computer_safety_confirmed(ctx)
        self.log("[computer] Potentially unsafe operation explicitly confirmed by user.")
        self.handle(ctx)
        return True

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
                    self.log(f"[cmd] Command without 'cmd' key: {cmd}")
                    cmds.remove(cmd)
                    continue
                cmd_id = str(cmd["cmd"])
                if not self.window.core.command.is_enabled(cmd_id) and not ctx.force_call:
                    self.log(f"[cmd] Command not allowed: {cmd_id}")
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
                self.window.controller.chat.common.unlock_input()  # unlock input
                return  # abort if no commands

            ctx.cmds = cmds  # append commands to ctx
            self.log("[cmd] Command call received...")

            # Computer Use provider safety checks: pause before executing the action.
            if (mode == MODE_COMPUTER
                    and not internal
                    and self.window.core.security.should_halt_computer(ctx)):
                self._pause_for_safety_confirmation(ctx)
                return

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

            # force call (experts, internal, etc.)
            if internal and ctx.force_call:
                reply.type = ReplyContext.CMD_EXECUTE

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
                    if ctx.force_call:
                        # force call, execute all commands
                        self.window.controller.plugins.apply_cmds(
                            reply.ctx,
                            reply.cmds,
                            all=True,
                            execute_only=True,
                        )
                    else:
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
                # force call
                if ctx.force_call:
                    self.window.controller.plugins.apply_cmds(
                        reply.ctx,
                        reply.cmds,
                        all=True,
                        execute_only=True,
                    )
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