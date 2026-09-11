#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 17:20:00                  #
# ================================================== #

from __future__ import annotations

import asyncio
import re
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
        self._pending_part_uuid = None
        self._last_emitted_part_uuid = None
        self.final_started = False
        # A status may request a short UI-only minimum visibility window. Newer
        # statuses are coalesced and emitted after that window instead of replacing
        # the current row immediately. This never delays agent/tool execution.
        self._status_hold_until = 0.0
        self._status_hold_handle = None
        self._pending_status = None
        # Keep high-frequency model deltas off the Qt event queue. The Web renderer
        # already batches JS work, but without this layer every token still crossed
        # the Qt signal boundary and triggered Python-side response handling/DB work.
        self._pending_chunk = ""
        self._last_stream_emit = time.monotonic()
        self._stream_emit_interval = 0.04
        self._stream_emit_chars = 512
        self._stream_flush_handle = None
        # Fallback finalization may receive an already-materialized final answer
        # (for example when a provider does not expose usable stream deltas).
        # When UI streaming is enabled, replay that authoritative text through
        # AGENT_V2_APPEND in small chunks instead of one monolithic append.
        self._final_stream_enabled = bool(getattr(context, "stream", False))
        self._final_stream_chunk_chars = 24
        self._final_stream_delay = 0.015

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
        """Flush the current pass before a tool/result boundary.

        Partial boundaries are owned by AgentsV2Runtime and are identified by the
        durable part UUID supplied to append(). Tool events themselves must never
        create/arm a new partial because tool-only LLM passes stay on the current
        partial by design.
        """
        if self._finished:
            return
        # Flush the previous pass so a later append carrying another part UUID
        # can never be batched together with it.
        self._flush_stream()

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
        part_uuid = self._pending_part_uuid
        self._pending_chunk = ""
        self._pending_part_uuid = None
        self._last_stream_emit = time.monotonic()
        part_begin = bool(
            part_uuid
            and self._last_emitted_part_uuid
            and part_uuid != self._last_emitted_part_uuid
        )
        self._emit(
            KernelEvent.AGENT_V2_APPEND,
            chunk=chunk,
            begin=self._first_chunk,
            part_begin=part_begin,
            part_uuid=part_uuid,
        )
        if part_uuid:
            self._last_emitted_part_uuid = part_uuid
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

    def append(self, text: Optional[str], part_uuid: Optional[str] = None):
        if self._finished or not text:
            return
        self.begin()
        value_part_uuid = str(part_uuid) if part_uuid else None
        if (self._pending_chunk and self._pending_part_uuid
                and value_part_uuid and self._pending_part_uuid != value_part_uuid):
            self._flush_stream()
        if value_part_uuid:
            self._pending_part_uuid = value_part_uuid
        chunk = str(text)
        self.text += chunk
        self._pending_chunk += chunk
        now = time.monotonic()
        if (len(self._pending_chunk) >= self._stream_emit_chars
                or now - self._last_stream_emit >= self._stream_emit_interval):
            self._flush_stream()
        else:
            self._schedule_stream_flush()

    async def append_streamed(
            self,
            text: Optional[str],
            part_uuid: Optional[str] = None,
            ensure_incremental: bool = False,
    ):
        """Append a provider stream delta, with a fallback for materialized chunks.

        Normal provider token deltas keep the low-overhead batching used by
        append(). After a tool roundtrip some providers/LlamaIndex wrappers can
        surface the next assistant pass as one large ``AgentStream.delta``. When
        ``ensure_incremental`` is enabled, split only such multi-chunk deltas and
        push them through the same Markdown-safe cadence used for fallback final
        answers. Small/native deltas are left untouched.
        """
        if self._finished or not text:
            return
        value = str(text)
        if not ensure_incremental or not self._final_stream_enabled:
            self.append(value, part_uuid=part_uuid)
            return

        chunks = self._final_chunks(value)
        if len(chunks) <= 1:
            self.append(value, part_uuid=part_uuid)
            return

        for index, chunk in enumerate(chunks):
            if self._finished:
                break
            self.append(chunk, part_uuid=part_uuid)
            # A large provider delta is already fully materialized. Force each
            # synthetic chunk over the Qt boundary or normal batching would merge
            # it back into one visually instantaneous response.
            self._flush_stream()
            if index + 1 < len(chunks):
                await asyncio.sleep(self._final_stream_delay)

    def _begin_final(self, text: Optional[str]) -> str:
        """Reset the live working draft and return normalized final text."""
        if self._finished:
            return ""
        final = str(text or "").strip()
        if not final:
            return ""
        self._flush_stream()
        self.clear_status()
        self.begin()
        self._pending_chunk = ""
        self._pending_part_uuid = None
        self._last_emitted_part_uuid = None
        self.text = ""
        self.final_started = True

        # Explicit UI barrier: clear the working Primary Agent draft and all
        # transient status rows before any final-answer text is emitted. The
        # corresponding main-thread handler also drops renderer micro-buffers.
        self._emit(getattr(KernelEvent, "AGENT_V2_FINAL_BEGIN", "kernel.agent_v2.final_begin"))
        # The first authoritative final chunk is a new live stream segment. Keep
        # begin=True so the renderer performs a second, token-adjacent transient
        # status cleanup immediately before the first final token is painted.
        self._first_chunk = True
        return final

    def _final_chunks(self, text: str):
        """Split final Markdown on word/whitespace boundaries without rewriting it."""
        pieces = re.findall(r"\S+\s*|\s+", str(text or ""))
        if not pieces:
            return []
        chunks = []
        current = ""
        limit = max(1, int(self._final_stream_chunk_chars or 24))
        for piece in pieces:
            # Keep long Markdown/URL tokens intact instead of slicing through
            # syntax. Ordinary prose is grouped into small stream-sized chunks.
            if current and len(current) + len(piece) > limit:
                chunks.append(current)
                current = ""
            if len(piece) > limit and not current:
                chunks.append(piece)
            else:
                current += piece
        if current:
            chunks.append(current)
        return chunks

    def start_final(self, text: Optional[str], part_uuid: Optional[str] = None):
        """Start final output immediately (non-stream/fallback path)."""
        final = self._begin_final(text)
        if not final:
            return
        self.append(final, part_uuid=part_uuid)
        self._flush_stream()

    async def stream_final(self, text: Optional[str], part_uuid: Optional[str] = None):
        """Emit the authoritative final answer incrementally when streaming is enabled.

        This is the fallback path for an already-materialized authoritative final
        answer. It keeps the user-facing Agents v2 contract consistent with Chat
        streaming by forwarding the text through the same live append pipeline in
        ordered Markdown-safe chunks.
        """
        final = self._begin_final(text)
        if not final:
            return
        if not self._final_stream_enabled:
            self.append(final, part_uuid=part_uuid)
            self._flush_stream()
            return

        chunks = self._final_chunks(final)
        for index, chunk in enumerate(chunks):
            if self._finished:
                break
            self.append(chunk, part_uuid=part_uuid)
            # Force each chunk across the Qt boundary instead of letting the
            # emitter's normal 512-char batching collapse the final into one event.
            self._flush_stream()
            if index + 1 < len(chunks):
                await asyncio.sleep(self._final_stream_delay)

    def accept_streamed_final(self):
        """Treat the already-streamed current part as the final answer.

        Used when the agent handler's terminal result is the same prose that was
        already emitted through AgentStream. Replaying it through start_final()
        would create a duplicate final partial/output.
        """
        if self._finished:
            return
        self._flush_stream()
        self.clear_status()
        self.final_started = True

    def _cancel_status_hold(self, drop_pending: bool = True):
        handle = self._status_hold_handle
        self._status_hold_handle = None
        if handle is not None:
            try:
                handle.cancel()
            except Exception:
                pass
        self._status_hold_until = 0.0
        if drop_pending:
            self._pending_status = None

    def _emit_status_now(self, value: str, source: str, hold_for: float = 0.0):
        if value == self.status_text:
            # Repeated aggregate refreshes do not need another Qt/JS event, but
            # they may renew the requested UI hold window.
            if value and hold_for > 0:
                self._status_hold_until = max(
                    self._status_hold_until,
                    time.monotonic() + float(hold_for),
                )
            return
        self.status_text = value
        self.begin()
        self._emit(
            KernelEvent.AGENT_V2_STATUS,
            status=value,
            source=source,
        )
        if value and hold_for > 0:
            self._status_hold_until = time.monotonic() + float(hold_for)

    def _flush_held_status(self):
        self._status_hold_handle = None
        if self._finished or self.final_started:
            self._pending_status = None
            self._status_hold_until = 0.0
            return
        now = time.monotonic()
        if self._status_hold_until > now:
            self._schedule_status_hold_flush()
            return
        pending = self._pending_status
        self._pending_status = None
        self._status_hold_until = 0.0
        if pending is not None:
            value, source, hold_for = pending
            self._emit_status_now(value, source, hold_for)

    def _schedule_status_hold_flush(self):
        if self._status_hold_handle is not None:
            return
        delay = max(0.0, self._status_hold_until - time.monotonic())
        try:
            loop = asyncio.get_running_loop()
            self._status_hold_handle = loop.call_later(
                delay,
                self._flush_held_status,
            )
        except RuntimeError:
            # Isolated/unit callers may not own an asyncio loop. Do not block them
            # just to preserve a visual hold; emit the newest pending status now.
            pending = self._pending_status
            self._pending_status = None
            self._status_hold_until = 0.0
            if pending is not None:
                value, source, hold_for = pending
                self._emit_status_now(value, source, hold_for)

    def status(
            self,
            text: Optional[str],
            source: str = "orchestrator",
            hold_for: float = 0.0,
    ):
        if self._finished:
            return
        self._flush_stream()
        value = (text or "").strip()
        # Once the authoritative final answer starts, transient workflow/tool
        # statuses are no longer allowed to reappear. Events emitted before the
        # final barrier may still be queued on the Qt side; the Web runtime has
        # the same final-mode guard as a second line of defence.
        if self.final_started and value:
            return

        # Empty status is an authoritative cleanup barrier (final begin, stop, end).
        # Never make final output wait for a visual minimum-duration status.
        if not value:
            self._cancel_status_hold(drop_pending=True)
            self._emit_status_now("", source, 0.0)
            return

        now = time.monotonic()
        if self._status_hold_until > now:
            # Coalesce rapid status churn while the current row is guaranteed to
            # remain visible. Only the newest pending value matters for the UI.
            self._pending_status = (value, source, max(0.0, float(hold_for or 0.0)))
            self._schedule_status_hold_flush()
            return

        # The hold expired before its timer ran; the newest incoming status wins.
        self._cancel_status_hold(drop_pending=True)
        self._emit_status_now(value, source, max(0.0, float(hold_for or 0.0)))

    def clear_status(self):
        self.status("")

    def show_loading(self):
        """Show the neutral request spinner while waiting for the next agent event.

        This is intentionally separate from workflow statuses: after a tool result
        the model may be preparing the final answer (or another pass), and showing
        a semantic status such as ``Planning task...`` is misleading. The renderer
        hides this spinner automatically on the next real text/tool/status activity.
        """
        if self._finished or self.final_started or self.signals is None:
            return
        self.clear_status()
        data = {"id": "chat"}
        ctx = getattr(self.context, "ctx", None)
        meta = getattr(ctx, "meta", None)
        if meta is not None:
            data["meta"] = meta
        self.signals.response.emit(KernelEvent(KernelEvent.STATE_BUSY, data))

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

    def finish(self, final_answer: Optional[str] = None, part_uuid: Optional[str] = None):
        if self._finished:
            return
        if final_answer and not self.final_started:
            self.start_final(final_answer, part_uuid=part_uuid)
        self._flush_stream()
        self._cancel_status_hold(drop_pending=True)
        self._finished = True
        self._emit(
            KernelEvent.AGENT_V2_END,
            final_answer=final_answer or "",
        )
