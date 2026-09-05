#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import asyncio
import threading
from typing import Optional

from pygpt_net.core.events import KernelEvent


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

    def append(self, text: Optional[str]):
        if self._finished or not text:
            return
        self.begin()
        chunk = str(text)
        self.text += chunk
        self._emit(
            KernelEvent.AGENT_V2_APPEND,
            chunk=chunk,
            begin=self._first_chunk,
        )
        self._first_chunk = False

    def status(self, text: Optional[str], source: str = "orchestrator"):
        if self._finished:
            return
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
        """Proxy a local plugin call to the Qt/main thread without an executor thread."""
        done = threading.Event()
        request = {
            "ctx": tool_ctx,
            "cmds": cmds,
            "done": done,
            "result": None,
            "error": None,
            "cancelled": False,
        }
        self._emit(KernelEvent.AGENT_V2_TOOL_EXEC, request=request)
        while not done.is_set():
            if stopped_cb():
                return "Execution cancelled."
            await asyncio.sleep(0.05)
        if request.get("error") is not None:
            raise request["error"]
        if request.get("cancelled"):
            return "Execution cancelled."
        return request.get("result")

    def finish(self, final_answer: Optional[str] = None):
        if self._finished:
            return
        if final_answer:
            final = str(final_answer)
            # workflow_finish carries the authoritative answer. Avoid duplicating an
            # identical suffix already streamed by the orchestrator.
            if final.strip() and not self.text.rstrip().endswith(final.strip()):
                if self.text and not self.text.endswith(("\n", " ")):
                    self.append("\n\n")
                self.append(final)
        self._finished = True
        self._emit(
            KernelEvent.AGENT_V2_END,
            final_answer=final_answer or "",
        )
