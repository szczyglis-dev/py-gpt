#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.06 00:00:00                  #
# ================================================== #

import json
from typing import Optional, Dict, Any, List

from pygpt_net.core.events import KernelEvent, RenderEvent
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import MODE_LLAMA_INDEX
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.agents_v2.tool_bridge import pop as pop_agent_v2_request

class Reply:
    def __init__(self, window=None):
        """
        Reply handler (response from plugins, tools, etc.)

        :param window: Window instance
        """
        self.window = window
        self.reply_stack = []
        self.reply_ctx = None
        self.last_result = None
        self.reply_idx = -1

    def add(
            self,
            context: BridgeContext,
            extra: Dict[str, Any] = None
    ) -> List[Dict]:
        """
        Send reply from plugins to model

        :param context: bridge context
        :param extra: extra data
        :return: list of results
        """
        flush = extra.get("flush", False) if isinstance(extra, dict) else False
        ctx = context.ctx
        if ctx is None:
            return []

        core = self.window.core
        self.last_result = ctx.results
        self.on_post_response(ctx, extra)

        if ctx.agent_call:
            # Agents v2 awaits plugin completion inside its own coroutine. Keep
            # request/future state in the process-only bridge registry; CtxItem.extra
            # is persisted by several plugins (notably image generation) and must
            # remain JSON-serializable.
            request = pop_agent_v2_request(ctx)
            if isinstance(request, dict):
                request["pending"] = False
                request["result"] = list(ctx.results or [])
                done = request.get("done")
                if done is not None:
                    done.set()
            return ctx.results

        core.debug.info("Reply...")
        if core.debug.enabled() and self.is_log():
            core.debug.debug("CTX REPLY: " + str(ctx))

        # In the partial-item flow a durable CtxItem can execute many tool rounds.
        # The old reply_idx/pid de-duplication assumed that every tool result
        # created a new CtxItem, so using it here can drop a perfectly valid
        # result from a later tool cycle (and leave the task permanently pending).
        # Structured tasks are therefore de-duplicated by their own completion
        # state instead of by the parent CtxItem pid.
        part = ctx.get_active_part()
        part_tasks = list(getattr(part, "tasks", None) or []) if part is not None else []
        structured = bool(part_tasks)
        pending_after = False

        if ctx.reply:
            if structured:
                responses = list(ctx.results or [])
                if not responses:
                    return []

                completed = core.ctx.complete_part_tasks(ctx, responses, part)
                pending_after = any(
                    not (isinstance(task.extra, dict) and task.extra.get("status") == "completed")
                    for task in part_tasks
                )

                # A repeated/late signal for an already completed task must not
                # enqueue the same tool result a second time. complete_part_tasks
                # always consumes a pending task (with request-order fallback), so
                # no completed rows here means this reply was already consumed.
                if not completed:
                    core.debug.info("Reply ignored: no pending partial task matched plugin result.")
                    ctx.results = []
                    return []

                self.append(ctx)
            else:
                # Legacy contexts keep the old pid-based guard for backward
                # compatibility with flows which do not use partial tasks.
                if self.reply_idx >= ctx.pid:
                    return []
                self.reply_idx = ctx.pid
                self.append(ctx)

        # Synchronous plugin execution is flushed by controller.command.dispatch
        # after all enabled plugins were visited. Async execution has no such
        # trailing flush, therefore flush here once every task in the current
        # partial has completed. This also correctly waits for parallel tool
        # calls handled by different plugins.
        if flush or (self.window.controller.kernel.async_allowed(ctx) and not pending_after):
            self.flush()

        return ctx.results

    def append(self, ctx: CtxItem):
        """
        Add reply to stack

        :param ctx: context item
        """
        self.window.core.debug.info("Reply stack (add)...")
        self.reply_stack.append(ctx.results)
        self.reply_ctx = ctx
        self.reply_ctx.results = []  # clear results

    def flush(self):
        """Flush reply stack"""
        if self.reply_ctx is None or len(self.reply_stack) == 0:
            return

        core = self.window.core
        dispatch = self.window.dispatch
        core.debug.info("Reply stack (flush)...")

        results = []
        for responses in self.reply_stack:
            for result in responses:
                results.append(result)

        self.window.update_status("")  # clear status
        self.window.controller.agent.on_reply(self.reply_ctx)  # handle reply in agent

        # Preserve the lineage of this tool call before creating the synthetic
        # internal reply. The active UI column/mode may change while an async
        # plugin is running, but the result must return to the mode/model that
        # issued the call.
        reply_mode = getattr(self.reply_ctx, "mode", None)
        reply_model = getattr(self.reply_ctx, "model", None)
        root_ctx = self.reply_ctx
        completed_part = root_ctx.get_active_part()

        # Structured rows are already completed from the exact current plugin
        # replies in add(). Do not rebuild from every task in completed_part here:
        # one partial may now contain several sequential tool rounds, and replaying
        # all older outputs would resend previous function results to the model.

        # prepare data to send as reply
        tool_data = json.dumps(results, ensure_ascii=False, default=str)
        if (len(self.reply_stack) < 2
                and self.reply_ctx.extra_ctx
                and core.config.get("ctx.use_extra")):
            tool_data = self.reply_ctx.extra_ctx  # if extra content is set, use it as data to send

        # Keep the old provider-facing lineage object, but make it explicitly
        # ephemeral. Text.send() will use it only for protocol history and will
        # attach the next model response to root_ctx instead of inserting a new
        # ctx_item row.
        prev_ctx = core.ctx.as_previous(root_ctx)
        prev_ctx.mode = reply_mode
        prev_ctx.model = reply_model
        prev_ctx.turn_parent = root_ctx
        prev_ctx.turn_previous_part = completed_part
        prev_ctx.turn_continuation = True
        core.ctx.update_item(root_ctx)
        self.window.update_status('...')

        if root_ctx.tool_calls:
            prev_ctx.extra["prev_tool_calls"] = list(root_ctx.tool_calls)

        # Do not expose a finished button yet. The waiting status is cleared and
        # the task is promoted to UI-ready only after the model consumes this
        # result and returns its next response.
        self.clear()

        # disable reply if the originating LlamaIndex request used ReAct.
        # Do not inspect the currently focused mode here.
        mode = reply_mode or core.config.get("mode")
        if mode == MODE_LLAMA_INDEX and core.config.get("llama.idx.react", False):
            return

        # send reply
        context = BridgeContext()
        context.ctx = prev_ctx
        context.prompt = str(tool_data)
        dispatch(KernelEvent(KernelEvent.REPLY_RETURN, {
            'context': context,
            'extra': {
                "force": True,
                "reply": True,
                "internal": True,
            },
        }))

    def on_post_response(
            self,
            ctx: CtxItem,
            extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Run post-response operations

        :param ctx: context (CtxItem)
        :param extra_data: extra data
        """
        if isinstance(extra_data, dict):
            if (ctx is None or not ctx.agent_call) or not self.window.controller.kernel.is_threaded():
                if "post_update" in extra_data and isinstance(extra_data["post_update"], list):
                    if "file_explorer" in extra_data["post_update"]:
                        self.window.controller.files.update_explorer()  # update file explorer view

    def clear(self):
        """Clear reply stack"""
        self.window.core.debug.info("Reply stack (clear)...")
        self.reply_ctx = None
        self.reply_stack = []

    def is_log(self) -> bool:
        """
        Check if event can be logged

        :return: true if can be logged
        """
        return self.window.core.config.get("log.events", False)
