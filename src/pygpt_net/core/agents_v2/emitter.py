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

from __future__ import annotations

import asyncio
import threading
import time
from typing import Optional

from pygpt_net.core.events import KernelEvent
from pygpt_net.core.agents_v2.tool_bridge import register, discard


class RuntimeEmitter:
    """Thread-safe UI bridge for one Agents v2 response."""

    def __init__(self, context, extra, signals):
        self.context = context
        self.extra = extra
        self.signals = signals
        self._begun = False
        self._first_chunk = True
        self._finished = False
        self.text = ""
        self.status_text = ""
        self._block_break_pending = False
        # Keep high-frequency model deltas off the Qt event queue. The Web renderer
        # already batches JS work, but without this layer every token still crossed
        # the Qt signal boundary and triggered Python-side response handling/DB work.
        self._pending_chunk = ""
        self._last_stream_emit = time.monotonic()
        self._stream_emit_interval = 0.04
        self._stream_emit_chars = 512
        self._stream_flush_handle = None

    def _emit(self, name: str, **data):
        if self.signals is None:
            return
        payload = {
            "context": self.context,
            "extra": self.extra,
            **data,
        }
        self.signals.response.emit(KernelEvent(name, payload))

    def begin(self):
        if self._begun:
            return
        self._begun = True
        self._emit(KernelEvent.AGENT_V2_BEGIN)

    def mark_block_boundary(self):
        """Start the next durable orchestrator pass in a new Markdown paragraph."""
        if self._finished or not self.text:
            return
        self._block_break_pending = True

    def _flush_stream(self):
        handle = self._stream_flush_handle
        self._stream_flush_handle = None
        if handle is not None:
            try:
                handle.cancel()
            except Exception:
                pass
        if not self._pending_chunk or self._finished:
            return
        chunk = self._pending_chunk
        self._pending_chunk = ""
        self._last_stream_emit = time.monotonic()
        self._emit(
            KernelEvent.AGENT_V2_APPEND,
            chunk=chunk,
            begin=self._first_chunk,
        )
        self._first_chunk = False

    def _schedule_stream_flush(self):
        if self._stream_flush_handle is not None:
            return
        try:
            loop = asyncio.get_running_loop()
            self._stream_flush_handle = loop.call_later(
                self._stream_emit_interval,
                self._flush_stream,
            )
        except RuntimeError:
            self._flush_stream()

    def append(self, text: Optional[str]):
        if self._finished or not text:
            return
        self.begin()
        chunk = str(text)
        if self._block_break_pending:
            # A new LLM pass after a tool/worker interaction is still part of the
            # same chat message, but should render as a separate Markdown block.
            if self.text.endswith("\n\n"):
                prefix = ""
            elif self.text.endswith("\n"):
                prefix = "\n"
            else:
                prefix = "\n\n"
            chunk = prefix + chunk
            self._block_break_pending = False
        self.text += chunk
        self._pending_chunk += chunk
        now = time.monotonic()
        if (len(self._pending_chunk) >= self._stream_emit_chars
                or now - self._last_stream_emit >= self._stream_emit_interval):
            self._flush_stream()
        else:
            self._schedule_stream_flush()

    def status(self, text: Optional[str], source: str = "orchestrator"):
        if self._finished:
            return
        self._flush_stream()
        value = (text or "").strip()
        if value == self.status_text:
            return
        self.status_text = value
        self.begin()
        self._emit(
            KernelEvent.AGENT_V2_STATUS,
            status=value,
            source=source,
        )

    def clear_status(self):
        self.status("")

    async def execute_plugin(self, tool_ctx, cmds, stopped_cb):
        """Await a PyGPT plugin without blocking the Qt GUI thread.

        Qt receives only the short command-dispatch operation. Long-running work
        is executed by the plugin's normal QRunnable. REPLY_ADD completes this
        request when the plugin has produced the result.
        """
        done = threading.Event()
        request = {
            "ctx": tool_ctx,
            "cmds": cmds,
            "done": done,
            "result": None,
            "error": None,
            "cancelled": False,
        }
        register(tool_ctx, request)
        self._emit(KernelEvent.AGENT_V2_TOOL_EXEC, request=request)
        started = time.monotonic()
        try:
            while not done.is_set():
                if stopped_cb():
                    request["cancelled"] = True
                    return "Execution cancelled."
                # Safety boundary for broken third-party plugins that neither
                # return a result nor emit a completion reply.
                if time.monotonic() - started > 1800:
                    raise TimeoutError("Agents v2 plugin tool timed out after 30 minutes.")
                await asyncio.sleep(0.025)
            if request.get("error") is not None:
                raise request["error"]
            if request.get("cancelled"):
                return "Execution cancelled."
            return request.get("result")
        finally:
            # Runtime-only synchronization state must never be stored in
            # CtxItem.extra because plugin callbacks may persist that context.
            discard(tool_ctx, request)

    def finish(self, final_answer: Optional[str] = None):
        if self._finished:
            return
        if final_answer:
            final = str(final_answer)
            # workflow_finish carries the authoritative answer. Avoid duplicating an
            # identical suffix already streamed by the orchestrator.
            if final.strip() and not self.text.rstrip().endswith(final.strip()):
                self.mark_block_boundary()
                self.append(final)
        self._flush_stream()
        self._finished = True
        self._emit(
            KernelEvent.AGENT_V2_END,
            final_answer=final_answer or "",
        )
