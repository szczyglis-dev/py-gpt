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
import os
import uuid
from typing import Optional, Dict, Any, List

from pygpt_net.core.events import KernelEvent, RenderEvent
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.types import PERSIST_HIDDEN_TOOL_CALLS
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.attachment import AttachmentItem
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
        hidden_unpersisted_cmds = bool(
            not PERSIST_HIDDEN_TOOL_CALLS
            and any(
                core.command.is_tool_hidden(str(cmd.get("cmd") or ""))
                for cmd in (ctx.cmds or [])
                if isinstance(cmd, dict)
            )
        )
        structured = bool(part_tasks) or hidden_unpersisted_cmds
        pending_after = False

        if ctx.reply:
            if structured:
                responses = list(ctx.results or [])
                if not responses:
                    return []

                completed = core.ctx.complete_part_tasks(ctx, responses, part)
                hidden_unpersisted = False
                if not PERSIST_HIDDEN_TOOL_CALLS:
                    for response in responses:
                        request = response.get("request") if isinstance(response, dict) else None
                        tool_name = str(request.get("cmd") or "") if isinstance(request, dict) else ""
                        if tool_name and core.command.is_tool_hidden(tool_name):
                            hidden_unpersisted = True
                            break
                pending_after = any(
                    not (isinstance(task.extra, dict) and task.extra.get("status") == "completed")
                    for task in part_tasks
                )
                # Hidden calls may intentionally have no durable task at all.
                # Keep the reply batch open until every command in the current
                # tool round has produced its model-facing response.
                expected_replies = len(ctx.cmds or [])
                received_replies = len(responses) + sum(
                    len(batch or []) for batch in self.reply_stack
                )
                if expected_replies and received_replies < expected_replies:
                    pending_after = True

                # A repeated/late signal for an already completed task must not
                # enqueue the same tool result a second time. complete_part_tasks
                # always consumes a pending task (with request-order fallback), so
                # no completed rows here means this reply was already consumed.
                if not completed and not hidden_unpersisted:
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

    @staticmethod
    def _extract_runtime_attachments(value: Any) -> List[Dict[str, str]]:
        """Collect runtime-only attachments embedded in plugin responses."""
        out: List[Dict[str, str]] = []

        def walk(node):
            if isinstance(node, dict):
                marked = node.get("agent_runtime_attachments")
                if isinstance(marked, (list, tuple)):
                    for entry in marked:
                        if isinstance(entry, dict):
                            path = str(entry.get("path") or "").strip()
                            name = str(entry.get("name") or os.path.basename(path)) if path else ""
                        else:
                            path = str(entry or "").strip()
                            name = os.path.basename(path) if path else ""
                        if path:
                            out.append({"path": path, "name": name})
                for key, child in node.items():
                    if key != "agent_runtime_attachments":
                        walk(child)
            elif isinstance(node, (list, tuple)):
                for child in node:
                    walk(child)

        walk(value)
        unique: List[Dict[str, str]] = []
        seen = set()
        for entry in out:
            path = entry["path"]
            if path in seen:
                continue
            seen.add(path)
            unique.append(entry)
        return unique

    @staticmethod
    def _strip_runtime_attachment_markers(value: Any) -> Any:
        """Remove transport-only attachment metadata from model-visible tool JSON."""
        if isinstance(value, dict):
            return {
                key: Reply._strip_runtime_attachment_markers(child)
                for key, child in value.items()
                if key != "agent_runtime_attachments"
            }
        if isinstance(value, list):
            return [Reply._strip_runtime_attachment_markers(child) for child in value]
        if isinstance(value, tuple):
            return tuple(Reply._strip_runtime_attachment_markers(child) for child in value)
        return value

    def _build_runtime_attachments(self, value: Any) -> Dict[str, AttachmentItem]:
        """Convert plugin runtime attachment markers into ephemeral provider attachments."""
        attachments: Dict[str, AttachmentItem] = {}
        for entry in self._extract_runtime_attachments(value):
            path = entry.get("path")
            if not path or not os.path.isfile(path):
                continue
            item = AttachmentItem()
            item.id = f"runtime-{uuid.uuid4()}"
            item.name = entry.get("name") or os.path.basename(path)
            item.path = path
            item.send = True
            item.extra = {
                "runtime_tool_attachment": True,
                "append_to_ctx": False,
            }
            attachments[item.id] = item
        return attachments

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

        # Runtime attachments are transport-only. Keep the ordinary tool result in
        # the protocol transcript, but carry local files separately so the next
        # provider request can send images as real multimodal input.
        runtime_attachments = self._build_runtime_attachments(results)
        model_results = self._strip_runtime_attachment_markers(results)

        # prepare data to send as reply
        tool_data = json.dumps(model_results, ensure_ascii=False, default=str)
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

        # send reply
        context = BridgeContext()
        context.ctx = prev_ctx
        context.prompt = str(tool_data)
        context.attachments = runtime_attachments
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
