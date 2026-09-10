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

from PySide6.QtCore import QObject, Signal, Slot

from pygpt_net.core.types import (
    MODE_AGENT,
)
from pygpt_net.core.events import KernelEvent, RenderEvent, Event
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.ctx.reply import ReplyContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Command(QObject):
    INTERNAL_COMPUTER_COMMANDS = {"computer_unimplemented"}
    SAFETY_CONFIRM_TYPE = "computer.safety"
    safety_pause = Signal(object, object)

    def __init__(self, window=None):
        """
        Command controller

        :param window: Window instance
        """
        super().__init__()
        self.window = window
        self.pending_safety_ctx = None
        self.pending_safety_resume = None
        self.safety_pause.connect(self._apply_safety_pause)

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

    def pause_for_safety_confirmation(self, ctx: CtxItem, resume_callback=None):
        """Pause a provider-flagged Computer Use operation before executing local actions."""
        if not self.window.controller.kernel.is_main_thread():
            # Computer Use continuations for Chat with Files/Agents v2 can run in
            # bridge threads. Queue all Qt/UI state changes onto Command's main
            # thread instead of touching widgets from the provider coroutine.
            self.safety_pause.emit(ctx, resume_callback)
            return
        self._apply_safety_pause(ctx, resume_callback)

    @Slot(object, object)
    def _apply_safety_pause(self, ctx: CtxItem, resume_callback=None):
        """Show the Computer Use confirmation dialog on the Qt/main thread."""
        if self.window.controller.kernel.stopped():
            if callable(resume_callback):
                resume_callback()
            return

        # Do not open a second dialog for the same pending round. A callback may
        # arrive slightly later than the first pause request, so keep it if needed.
        if self.pending_safety_ctx is ctx:
            if self.pending_safety_resume is None and callable(resume_callback):
                self.pending_safety_resume = resume_callback
            return

        if self.pending_safety_ctx is not None:
            self.cancel_pending_safety_confirmation()

        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        ctx.extra["computer_safety_waiting"] = True
        ctx.extra.pop("computer_safety_rejected", None)
        self.pending_safety_ctx = ctx
        self.pending_safety_resume = resume_callback

        warning = self._get_safety_warning(ctx)
        self.window.dispatch(RenderEvent(RenderEvent.TOOL_UPDATE, {
            "meta": ctx.meta,
            "tool_data": warning,
        }))
        self.window.update_status("")

        # Keep the request active and the normal chat input locked. Approval is
        # performed exclusively by the Yes/No dialog; STOP/ESC remains available.
        self.window.controller.chat.input.generating = True
        self.window.controller.chat.common.lock_input()
        self.window.ui.dialogs.confirm(
            type=self.SAFETY_CONFIRM_TYPE,
            id=ctx,
            msg=warning,
            modal=True,
        )
        self.log("[computer] Potentially unsafe operation paused; waiting for dialog confirmation.")

    def _take_pending_safety_confirmation(self, ctx: CtxItem = None):
        """Detach and return the current pending safety context and resume callback."""
        pending = self.pending_safety_ctx
        if pending is None or (ctx is not None and pending is not ctx):
            return None, None

        callback = self.pending_safety_resume
        self.pending_safety_ctx = None
        self.pending_safety_resume = None
        try:
            if isinstance(getattr(pending, "extra", None), dict):
                pending.extra["computer_safety_waiting"] = False
        except Exception:
            pass
        return pending, callback

    def _hide_safety_dialog(self) -> None:
        """Hide the shared confirmation dialog without firing another decision."""
        try:
            dialog = self.window.ui.dialog.get("confirm")
            if dialog is not None and getattr(dialog, "type", None) == self.SAFETY_CONFIRM_TYPE:
                dialog.hide()
        except Exception:
            pass

    def confirm_pending_safety_confirmation(self, ctx: CtxItem = None) -> bool:
        """Approve and resume the pending Computer Use operation."""
        pending, callback = self._take_pending_safety_confirmation(ctx)
        if pending is None:
            return False

        self._hide_safety_dialog()
        self.window.core.security.mark_computer_safety_confirmed(pending)
        self.log("[computer] Potentially unsafe operation explicitly confirmed by user.")

        # The original request is still active. Keep ordinary input locked while
        # either the command dispatcher or provider continuation resumes.
        self.window.controller.chat.common.lock_input()
        if callable(callback):
            callback()
        else:
            self.handle(pending)
        return True

    def reject_pending_safety_confirmation(self, ctx: CtxItem = None) -> bool:
        """Reject the pending Computer Use operation and resume its waiter as denied."""
        pending, callback = self._take_pending_safety_confirmation(ctx)
        if pending is None:
            return False

        self._hide_safety_dialog()
        if not isinstance(getattr(pending, "extra", None), dict):
            pending.extra = {}
        pending.extra["computer_safety_rejected"] = True
        self.log("[computer] Potentially unsafe operation rejected by user.")

        # A rejected safety prompt is equivalent to stopping the current request:
        # no action may execute and all chat/tool/runtime state must be released.
        # Do the regular STOP cleanup before waking a provider coroutine so it
        # observes the stopped kernel immediately.
        self.window.controller.chat.common.stop()
        if callable(callback):
            callback()
        return True

    def cancel_pending_safety_confirmation(self, ctx: CtxItem = None) -> bool:
        """Cancel a pending confirmation and wake any provider loop (STOP/ESC path)."""
        pending, callback = self._take_pending_safety_confirmation(ctx)
        if pending is None:
            return False
        self._hide_safety_dialog()
        if callable(callback):
            callback()
        self.log("[computer] Pending safety confirmation cancelled.")
        return True

    def _is_internal_computer_command(self, ctx: CtxItem, cmd_id: str) -> bool:
        """Allow provider-created internal Computer Use error calls without advertising them as tools."""
        if cmd_id not in self.INTERNAL_COMPUTER_COMMANDS:
            return False
        for tool_call in getattr(ctx, "tool_calls", None) or []:
            if isinstance(tool_call, dict) and tool_call.get("type") == "computer_call":
                return True
        return False

    def handle(self, ctx: CtxItem, internal: bool = False) -> Any:
        """
        Handle commands and expert mentions

        :param ctx: CtxItem
        :param internal: Internal flag, if True then skip some checks
        """
        if self.window.controller.kernel.stopped():
            return

        mode = getattr(ctx, "mode", None) or self.window.core.config.get('mode')

        # extract commands
        cmds = ctx.cmds_before  # native/llama tool calls are prepared before rendering
        if not cmds and ctx.tool_calls:
            cmds = self.window.core.command.tool_calls_to_cmds(ctx.tool_calls)
        if not cmds:
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
                if (not self.window.core.command.is_enabled(cmd_id)
                        and not ctx.force_call
                        and not self._is_internal_computer_command(ctx, cmd_id)):
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
            if (not internal
                    and self.window.core.security.should_halt_computer(ctx)):
                self.pause_for_safety_confirmation(ctx)
                return True

            # Persist the request before execution. Native tool calls retain provider
            # call IDs; legacy inline commands receive stable task UUID-based IDs.
            if ctx.tool_calls:
                tool_calls = ctx.tool_calls
            else:
                tool_calls = []
                for cmd in cmds:
                    tool_calls.append({
                        "function": {"name": cmd.get("cmd", "tool"), "arguments": cmd.get("params", {})}
                    })
            self.window.core.ctx.record_tool_calls(ctx, tool_calls)

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

            # Rebuild the current durable item before showing the waiting row.
            # This removes streamed legacy <tool> markup and, because the freshly
            # persisted tasks are not ui_ready yet, cannot expose a Tool button
            # prematurely. The pending status is attached after the reload.
            self.window.dispatch(RenderEvent(RenderEvent.RELOAD, {"meta": ctx.meta, "ctx": ctx}))
            data = {
                "meta": ctx.meta,
                "ctx": ctx,
                "tool_names": [str(cmd.get("cmd") or "tool") for cmd in cmds],
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
                return True
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
                return True

        return False

    def log(self, data: Any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)