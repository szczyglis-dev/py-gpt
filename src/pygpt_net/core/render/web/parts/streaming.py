#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 00:00:00                  #
# ================================================== #

"""Main and partial response streams, batching and begin/end barriers."""

import json
from typing import Optional
from time import monotonic
from PySide6.QtCore import QTimer
from pygpt_net.item.ctx import CtxItem, CtxMeta
from .buffer import AppendBuffer


class Streaming:
    """Main and partial response streams, batching and begin/end barriers.

    The renderer supplies session services and the shared session state.
    Collaborators are called explicitly through their component APIs.
    """

    # ========================================
    # Initialization
    # ========================================

    def __init__(self, renderer):
        self.renderer = renderer
        self.state = renderer.state

    # ========================================
    # Response lifecycle
    # ========================================

    def stream_begin(self, meta: CtxMeta, ctx: CtxItem):
        """
        Render stream begin.

        STREAM_BEGIN and the first STREAM_APPEND(begin=True) describe the same
        logical response. They are intentionally accepted in either order. The
        first one that reaches the renderer owns initialization; the duplicate
        begin for the same CtxItem becomes a no-op instead of resetting buffers
        or the browser stream a second time.

        :param meta: context meta
        :param ctx: context item
        """
        pid = self.renderer.session.get_or_create_pid(meta)
        if pid is None or ctx is None:
            return

        session_key = id(ctx)
        if self.state.stream_session_ctx.get(pid) == session_key:
            # The first text delta may have reached the renderer before the
            # separately queued STREAM_BEGIN (notably in Realtime + audio). A
            # second begin here would clear the Python micro-batch and call
            # beginStream() again, dropping exactly that first provider delta.
            # Ownership can still become durable after the response object was
            # created, so refresh only the owner hint without resetting anything.
            owner_id = str(getattr(getattr(ctx, "turn_parent", None) or ctx, "id", "") or "")
            if owner_id and self.state.stream_owner_id.get(pid, "") != owner_id:
                try:
                    owner_json = json.dumps(owner_id, ensure_ascii=False)
                    node = self.renderer.get_output_node(meta)
                    if node is not None:
                        node.page().runJavaScript(
                            "if (typeof window.bindStreamOwner !== 'undefined') "
                            f"bindStreamOwner({owner_json});"
                        )
                    self.state.stream_owner_id[pid] = owner_id
                except Exception:
                    pass
            return

        self.state.stream_session_ctx[pid] = session_key
        pctx = self.state.pids[pid]
        pctx.clear()
        self.stream_reset(pid)
        self.state.stream_owner_id[pid] = str(getattr(ctx, "id", "") or "")
        self.state.prev_chunk_replace = False

        # A provider continuation starts after a tool result has been returned to
        # the model. Its animated ``Tools: ...`` row can still live in the
        # provisional stream box when STREAM_BEGIN arrives. Generic beginStream()
        # clears that box immediately, which used to leave only the global spinner
        # visible until the first response token arrived. Rebind the durable parent
        # and replay the UI-only workflow rows in the same JS turn so the waiting
        # status remains visible for the whole provider TTFT window.
        #
        # beginStream() is sent through runJavaScript(), while text deltas use
        # QWebChannel. The transport barrier below keeps all text on the Python
        # side until that reset has executed. The response-level session guard
        # above additionally prevents a duplicate/late begin from resetting a
        # stream that its first delta has already initialized.
        parent_ctx = getattr(ctx, "turn_parent", None)
        try:
            stream_owner = parent_ctx if parent_ctx is not None else ctx
            stream_owner_id = json.dumps(
                str(getattr(stream_owner, "id", "") or ""), ensure_ascii=False
            )
            script = ""
            if parent_ctx is not None:
                header = self.renderer.messages.get_name_header(ctx, stream=True)
                parent_id = json.dumps(
                    str(getattr(parent_ctx, "id", "") or ""), ensure_ascii=False
                )
                header_json = json.dumps(header or "", ensure_ascii=False)
                status_records = self.renderer.agents.workflow_status_records(
                    parent_ctx,
                    compact=self.renderer.agents.workflow_single_status_live(),
                    live_ids=self.renderer.agents.workflow_single_status_live(),
                )
                records_json = json.dumps(
                    status_records,
                    ensure_ascii=False,
                    default=str,
                )
                script = (
                    f"if (typeof window.beginStream !== 'undefined') beginStream(false, {stream_owner_id});"
                )
                if status_records:
                    script += (
                        "if (typeof window.bindWorkflowStream !== 'undefined') "
                        f"bindWorkflowStream({parent_id}, {header_json}, {records_json});"
                    )
            else:
                script = (
                    f"if (typeof window.beginStream !== 'undefined') beginStream(false, {stream_owner_id});"
                )

            node = self.renderer.get_output_node(meta)
            if node is not None:
                self._run_stream_begin_js(pid, node, script)
        except Exception:
            self.stream_begin_release(pid, self.state.stream_begin_seq.get(pid, 0))

        try:
            self.state.pids[pid].header = self.renderer.messages.get_name_header(ctx, stream=True)
        except Exception:
            self.state.pids[pid].header = ""
        self.renderer.view.update_names(meta, ctx)

    def stream_end(self, meta: CtxMeta, ctx: CtxItem):
        """
        Render stream end.

        If beginStream() is still executing in WebEngine, postpone finalization
        until its callback opens the QWebChannel barrier. This covers extremely
        short realtime responses where TURN_END can arrive before the browser
        has processed STREAM_BEGIN.

        :param meta: context meta
        :param ctx: context item
        """
        pid = self.renderer.session.get_or_create_pid(meta)
        if pid is None:
            return
        if pid in self.state.stream_begin_pending:
            self.state.stream_end_pending[pid] = (meta, ctx)
            return
        self._stream_end_finish(meta, ctx, pid)

    def next_chunk(self, meta: CtxMeta, ctx: CtxItem):
        """
        Flush current stream and start with new chunks

        :param meta: context meta
        :param ctx: context item
        """
        pid = self.renderer.session.get_or_create_pid(meta)
        self.stream_flush(pid, force=True)
        self.state.pids[pid].item = ctx
        self.state.pids[pid].buffer = ""
        self.renderer.view.update_names(meta, ctx)
        self.state.prev_chunk_replace = False
        self.state.prev_chunk_newline = False
        try:
            self.renderer.get_output_node(meta).page().runJavaScript(
                "if (typeof window.nextStream !== 'undefined') nextStream();"
            )
        except Exception:
            pass
        try:
            self.state.pids[pid].header = self.renderer.messages.get_name_header(ctx, stream=True)
        except Exception:
            self.state.pids[pid].header = ""

    # ========================================
    # Main response streaming
    # ========================================

    def append_chunk(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text_chunk: str,
            begin: bool = False,
            part_key: Optional[object] = None,
    ):
        """
        Append streamed Markdown chunk to JS with micro-batching and typed chunk support.

        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk to append
        :param begin: True if begin of stream
        :param part_key: durable partial UUID/ID owning this chunk (optional)
        """
        pid = self.renderer.session.get_or_create_pid(meta)
        if pid is None:
            return

        pctx = self.state.pids[pid]
        previous_item = pctx.item
        previous_id = getattr(previous_item, "id", None)
        current_id = getattr(ctx, "id", None)
        current_owner = str(current_id or "")
        if current_owner and self.state.stream_owner_id.get(pid, "") != current_owner:
            try:
                owner_json = json.dumps(current_owner, ensure_ascii=False)
                self.renderer.get_output_node(meta).page().runJavaScript(
                    "if (typeof window.bindStreamOwner !== 'undefined') "
                    f"bindStreamOwner({owner_json});"
                )
                self.state.stream_owner_id[pid] = current_owner
            except Exception:
                pass
        is_new_item = previous_item is not ctx and (
            previous_id is None or current_id is None or previous_id != current_id
        )
        if is_new_item:
            self.renderer.history.hide_previous_agent_action_icons(meta, ctx)

        # STREAM_BEGIN and STREAM_APPEND(begin=True) are two announcements of the
        # same response lifecycle. Whichever arrives first performs the reset.
        # The other must not clear buffers or call beginStream() again. This is
        # critical for realtime, where Qt queued delivery can let the first text
        # delta overtake RT_OUTPUT_READY/STREAM_BEGIN.
        session_key = id(ctx)
        stream_already_started = self.state.stream_session_ctx.get(pid) == session_key
        begin_stream_here = bool(begin and not stream_already_started)
        if begin_stream_here:
            self.state.stream_session_ctx[pid] = session_key

        pctx.item = ctx
        if begin_stream_here:
            pctx.buffer = ""
        if text_chunk:
            pctx.append_buffer(str(text_chunk))

        if begin_stream_here:
            # Clear the previous turn's batching/reasoning state before looking
            # at the first chunk of the new stream.
            self.stream_reset(pid)

        has_response_activity = False
        if text_chunk:
            has_response_activity = self.renderer.loading.chunk_has_response_activity(
                ("main", pid),
                str(text_chunk),
            )
        if has_response_activity:
            self.renderer.loading.hide_loading_on_activity(
                meta,
                pid=pid,
                reserve_space=False,
            )

        if begin_stream_here:
            # JS beginStream() recreates the transient stream container. Pass
            # true only when this first chunk is actually visible activity; a
            # hidden <think> stream must not dismiss the request spinner.
            # Rebind it to the durable ctx id and replay UI-only workflow rows
            # immediately afterwards, otherwise a status shown before the first
            # token disappears or is later reattached below message controls.
            pctx.header = self.renderer.messages.get_name_header(ctx, stream=True)
            parent_id = str(getattr(ctx, "id", "") or "")
            self.renderer.agents.workflow_status_freeze(meta, ctx)
            status_records = self.renderer.agents.workflow_status_records(
                ctx,
                compact=self.renderer.agents.workflow_single_status_live(),
                live_ids=self.renderer.agents.workflow_single_status_live(),
            )
            try:
                stream_part_key = str(part_key or "")
                if stream_part_key:
                    agent_name = self.renderer.agents.legacy_agent_name_prefix(ctx, part_key=stream_part_key)
                else:
                    active_part = ctx.get_active_part()
                    stream_part_key = str(
                        getattr(active_part, "uuid", "")
                        or getattr(active_part, "id", "")
                        or ""
                    )
                    agent_name = self.renderer.agents.legacy_agent_name_prefix(ctx, part=active_part)
                parent_json = json.dumps(parent_id, ensure_ascii=False)
                header_json = json.dumps(pctx.header or "", ensure_ascii=False)
                records_json = json.dumps(status_records, ensure_ascii=False, default=str)
                part_key_json = json.dumps(stream_part_key, ensure_ascii=False)
                agent_name_json = json.dumps(agent_name, ensure_ascii=False)
                chunk_js = "true" if has_response_activity else "false"
                script = (
                    "if (typeof window.freezeWorkflowStatus !== 'undefined') "
                    f"freezeWorkflowStatus({parent_json});"
                    "if (typeof window.beginStream !== 'undefined') "
                    f"beginStream({chunk_js}, {parent_json});"
                    "if (typeof window.bindWorkflowStream !== 'undefined') "
                    f"bindWorkflowStream({parent_json}, {header_json}, {records_json},"
                    f"{part_key_json}, {agent_name_json});"
                )
                node = self.renderer.get_output_node(meta)
                if node is not None:
                    self._run_stream_begin_js(pid, node, script)
            except Exception:
                # Never strand queued text if the WebView is already going away.
                self.stream_begin_release(pid, self.state.stream_begin_seq.get(pid, 0))
            self.renderer.view.update_names(meta, ctx)

        if not text_chunk:
            return

        if not begin_stream_here and part_key:
            # STREAM_BEGIN can precede the runtime's first named partial.
            # Refresh its identity when the UUID-bearing delta arrives, without
            # resetting the stream or replaying workflow statuses.
            agent_name = self.renderer.agents.legacy_agent_name_prefix(ctx, part_key=part_key)
            if agent_name:
                node = self.renderer.get_output_node(meta)
                if node is not None:
                    node.page().runJavaScript(
                        "if (typeof window.bindWorkflowStream !== 'undefined') "
                        f"bindWorkflowStream({json.dumps(str(ctx.id or ''), ensure_ascii=False)},"
                        f"{json.dumps(pctx.header or '', ensure_ascii=False)},[],"
                        f"{json.dumps(str(part_key), ensure_ascii=False)},"
                        f"{json.dumps(agent_name, ensure_ascii=False)});"
                    )

        self.stream_push(pid, pctx.header or "", str(text_chunk))

    def stream_push(self, pid: int, header: str, chunk: str):
        """
        Push chunk into buffer and schedule flush

        :param pid: context PID
        :param header: optional header (first chunk only)
        :param chunk: chunk to append
        """
        if not chunk:
            return

        buf, timer = self._stream_get(pid)
        if header and not self.state.stream_header.get(pid):
            self.state.stream_header[pid] = header

        buf.append(chunk)

        # Keep every delta on the Python side while beginStream() is still
        # pending. QWebChannel must never overtake the JS reset and put data into
        # streamQ just before that reset clears it.
        if pid in self.state.stream_begin_pending:
            return

        pending_size = getattr(buf, "_size", 0)
        if pending_size >= self.state.stream_emergency_bytes:
            self.stream_flush(pid, force=True)
            return
        if pending_size >= self.state.stream_max_bytes:
            self.stream_flush(pid, force=True)
            return
        if not timer.isActive():
            try:
                timer.start()
            except Exception:
                self.stream_flush(pid, force=True)

    def stream_flush(self, pid: int, force: bool = False):
        """
        Flush buffered chunks via QWebChannel (bridge.chunk.emit(name, chunk, type))

        :param pid: context PID
        :param force: True if force flush ignoring interval
        """
        # The matching runJavaScript callback will call us again after the
        # latest begin/reset has actually executed in WebEngine.
        if pid in self.state.stream_begin_pending:
            return

        buf = self.state.stream_acc.get(pid)
        if buf is None or buf.is_empty():
            t = self.state.stream_timer.get(pid)
            if t and t.isActive():
                try:
                    t.stop()
                except Exception:
                    pass
            return

        node = self.renderer.get_output_node_by_pid(pid)
        if node is None:
            buf.clear()
            return

        t = self.state.stream_timer.get(pid)
        if t and t.isActive():
            try:
                t.stop()
            except Exception:
                pass

        data = buf.get_and_clear()
        name = self.state.stream_header.get(pid, "") or ""

        node.page().bridge.chunk.emit(name, data, "text_delta")

        try:
            del data
            # auto GC cleanup after some time
            now = monotonic()
            last = self.state.stream_last_cleanup
            if now - last > 120.0:
                self.renderer.auto_cleanup_soft()
                self.state.stream_last_cleanup = now
        except Exception:
            pass

        self.state.stream_last_flush[pid] = monotonic()

    def stream_reset(self, pid: Optional[int]):
        """
        Reset micro-batch state for PID

        :param pid: context PID
        """
        if pid is None:
            return
        buf = self.state.stream_acc.get(pid)
        if buf:
            buf.clear()
        t = self.state.stream_timer.get(pid)
        if t and t.isActive():
            try:
                t.stop()
            except Exception:
                pass
        self.state.stream_header[pid] = ""
        self.state.stream_last_flush[pid] = 0.0
        self.state.reasoning_activity_state.pop(("main", pid), None)

    # ========================================
    # Begin barriers
    # ========================================

    def stream_begin_arm(self, pid: int) -> int:
        """Arm/replace the WebEngine begin barrier for one stream PID."""
        seq = int(self.state.stream_begin_seq.get(pid, 0)) + 1
        self.state.stream_begin_seq[pid] = seq
        self.state.stream_begin_pending.add(pid)
        return seq

    def stream_begin_release(self, pid: int, seq: int) -> None:
        """Release buffered text after the matching beginStream JS completed."""
        if self.state.stream_begin_seq.get(pid) != seq:
            # A newer begin/reset superseded this callback. Only the newest JS
            # reset is allowed to open the text transport.
            return
        self.state.stream_begin_pending.discard(pid)
        if pid not in self.state.pids:
            return
        buf = self.state.stream_acc.get(pid)
        if buf is not None and not buf.is_empty():
            self.stream_flush(pid, force=True)

        pending_end = self.state.stream_end_pending.pop(pid, None)
        if pending_end is not None:
            meta, ctx = pending_end
            self._stream_end_finish(meta, ctx, pid)

    # ========================================
    # Partial response streaming
    # ========================================

    def append_part_chunk(
            self,
            meta: CtxMeta,
            parent_ctx: CtxItem,
            part_key: object,
            text_chunk: str,
            begin: bool = False,
    ):
        """Stream a chronological partial inside one existing bot message.

        This is used after a tool boundary. The durable parent CtxItem has
        already been materialized/synchronized; the new text is appended as a
        ``.msg-part`` under ``msg-bot-<parent id>``. No additional CtxItem /
        msg-box is created. Finalization keeps this streamed DOM and synchronizes
        only structural metadata around it.
        """
        pid = self.renderer.session.get_or_create_pid(meta)
        parent_id = getattr(parent_ctx, "id", None)
        if pid is None or parent_id is None:
            # Defensive fallback for not-yet-persisted turns.
            self.append_chunk(meta, parent_ctx, text_chunk, begin)
            return

        if begin:
            self.renderer.agents.update_agent_working(meta, parent_ctx)
        pctx = self.state.pids[pid]
        pctx.item = parent_ctx
        key = (pid, str(parent_id), str(part_key or "live"))

        if begin:
            # A new text partial follows the status/tool that was visible just
            # before it. Keep that row in the chronological timeline; only stop
            # its active shimmer. Removing it here made the workflow jump and
            # caused the following text to appear as if the tool never happened.
            self.partial_stream_reset(pid)
            self.renderer.agents.workflow_status_freeze(meta, parent_ctx)
            try:
                parent_id_json = json.dumps(str(parent_id), ensure_ascii=False)
                self.renderer.get_output_node(meta).page().runJavaScript(
                    "if (typeof window.freezeWorkflowStatus !== 'undefined') "
                    f"freezeWorkflowStatus({parent_id_json});"
                )
            except Exception:
                pass
            self.state.partial_stream_started.discard(key)

        has_response_activity = False
        if text_chunk:
            has_response_activity = self.renderer.loading.chunk_has_response_activity(
                ("partial",) + key,
                str(text_chunk),
            )
        if has_response_activity:
            self.renderer.loading.hide_loading_on_activity(meta, pid=pid)

        if not text_chunk:
            return

        buf, timer = self._partial_stream_get(key)
        buf.append(str(text_chunk))
        pending_size = getattr(buf, "_size", 0)
        if pending_size >= self.state.stream_emergency_bytes or pending_size >= self.state.stream_max_bytes:
            self._partial_stream_flush(key, force=True)
            return
        if not timer.isActive():
            try:
                timer.start()
            except Exception:
                self._partial_stream_flush(key, force=True)

    def flush_part_streams(self, meta: Optional[CtxMeta] = None):
        """Flush active inline partial buffers before stream completion."""
        pid = self.renderer.get_pid(meta) if meta is not None else None
        for key in list(self.state.partial_stream_acc):
            if pid is None or key[0] == pid:
                self._partial_stream_flush(key, force=True)

    def discard_part_streams(self, meta: Optional[CtxMeta] = None):
        """Discard transient inline buffers before a durable sync boundary."""
        pid = self.renderer.get_pid(meta) if meta is not None else None
        self.partial_stream_reset(pid)

    def partial_stream_reset(self, pid: Optional[int] = None, keep: Optional[tuple] = None):
        """Stop/discard Python buffers for transient inline partials.

        The durable CtxItemPart is authoritative across structural boundaries,
        therefore pending inline chunks must never fire afterwards and recreate stale UI.
        """
        keys = set(self.state.partial_stream_acc) | set(self.state.partial_stream_timer) | set(self.state.partial_stream_started)
        for key in list(keys):
            if pid is not None and key[0] != pid:
                continue
            if keep is not None and key == keep:
                continue
            timer = self.state.partial_stream_timer.pop(key, None)
            if timer and timer.isActive():
                try:
                    timer.stop()
                except Exception:
                    pass
            buf = self.state.partial_stream_acc.pop(key, None)
            if buf is not None:
                buf.clear()
            self.state.partial_stream_started.discard(key)

        for state_key in list(self.state.reasoning_activity_state):
            if not state_key or state_key[0] != "partial":
                continue
            if pid is not None and len(state_key) > 1 and state_key[1] != pid:
                continue
            raw_key = tuple(state_key[1:])
            if keep is not None and raw_key == keep:
                continue
            self.state.reasoning_activity_state.pop(state_key, None)

    # ========================================
    # Input and live messages
    # ========================================

    def append_chunk_input(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text_chunk: str,
            begin: bool = False,
            date_label: Optional[str] = None,
    ):
        """
        Append user input payload to the live input area (legacy bridge path)

        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk to append
        :param begin: True if begin of stream
        :param date_label: optional day separator rendered before the user row
        """
        if not text_chunk:
            return
        if ctx.hidden:
            return
        try:
            payload = "__PYGPT_INPUT_V1__" + json.dumps({
                "text": self.renderer.sanitize_html(text_chunk),
                "date_label": date_label,
                "msg_id": getattr(ctx, "id", None),
                "user_attachments": self.renderer.messages.input_attachment_snapshot(
                    ctx, self.renderer.session.get_or_create_pid(meta)),
            }, ensure_ascii=False, separators=(",", ":"))
            self.renderer.get_output_node(meta).page().bridge.nodeInput.emit(
                payload
            )
        except Exception:
            pass

    def append_live(self, meta: CtxMeta, ctx: CtxItem, text_chunk: str, begin: bool = False):
        """
        Append live output chunk to output (legacy live preview)

        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk to append
        :param begin: True if begin of stream
        """
        pid = self.renderer.session.get_or_create_pid(meta)
        previous_item = self.state.pids[pid].item
        previous_id = getattr(previous_item, "id", None)
        current_id = getattr(ctx, "id", None)
        if previous_item is not ctx and (
                previous_id is None or current_id is None or previous_id != current_id):
            self.renderer.history.hide_previous_agent_action_icons(meta, ctx)
        self.state.pids[pid].item = ctx
        if text_chunk is None or text_chunk == "":
            if begin:
                self.state.pids[pid].live_buffer = ""
            return

        self.renderer.view.update_names(meta, ctx)
        raw_chunk = str(text_chunk).translate({ord('<'): '&lt;', ord('>'): '&gt;'})
        if begin:
            debug = ""
            if self.renderer.is_debug():
                debug = self.renderer.append_debug(ctx, pid, "stream")
            if debug:
                raw_chunk = debug + raw_chunk
            self.state.pids[pid].live_buffer = ""
            self.state.pids[pid].is_cmd = False
            self.clear_live(meta, ctx)
        self.state.pids[pid].append_live_buffer(raw_chunk)

        try:
            self.renderer.get_output_node(meta).page().runJavaScript(
                f"""replaceLive({self.renderer.to_json(
                    self.renderer.sanitize_html(
                        self.state.pids[pid].live_buffer
                    )
                )});"""
            )
        except Exception:
            pass

    def clear_live(self, meta: CtxMeta, ctx: CtxItem):
        """
        Clear live output

        :param meta: context meta
        :param ctx: context item
        """
        if meta is None:
            return
        pid = self.renderer.session.get_or_create_pid(meta)
        try:
            self.renderer.get_output_node_by_pid(pid).page().runJavaScript(
                "if (typeof window.clearLive !== 'undefined') clearLive();"
            )
        except Exception:
            pass

    # ========================================
    # Private: response finalization
    # ========================================

    def _stream_end_finish(self, meta: CtxMeta, ctx: CtxItem, pid: int) -> None:
        """Finalize a stream after the begin/reset transport barrier is open."""
        self.state.prev_chunk_replace = False

        self.stream_flush(pid, force=True)
        # Flush the last inline partial delta before teardown. The durable parent
        # is authoritative, but the streamed DOM itself is preserved; flushing
        # here guarantees the final tail is present before STREAM_END promotes it.
        self.flush_part_streams(meta)
        self.partial_stream_reset(pid)
        # Stream finalization is mode-agnostic. Historical agent modes used to
        # append a newly rendered CtxItem here, which discarded the DOM that had
        # just received the stream. Always promote/synchronize the existing live
        # node instead; producers that truly changed authoritative text must emit
        # REPLACE_OUTPUT explicitly.
        # Promote the exact DOM node that received the stream into durable history.
        # Do not replace its text at normal stream completion. Any exceptional
        # correction must be requested explicitly via REPLACE_OUTPUT/SYNC_OUTPUT.
        self.renderer.bridge.finalize_output(meta, ctx, replace_text=False, reason="stream_end")
        self.state.pids[pid].clear()
        self.state.stream_owner_id.pop(pid, None)
        self.state.stream_session_ctx.pop(pid, None)
        self.stream_reset(pid)
        self.partial_stream_reset(pid)
        self.renderer.auto_cleanup(meta)

    # ========================================
    # Private: main stream buffers and WebView initialization
    # ========================================

    def _stream_get(self, pid: int) -> tuple[AppendBuffer, QTimer]:
        """
        Get/create per-PID append buffer and timer

        :param pid: context PID
        :return: (buffer, timer)
        """
        buf = self.state.stream_acc.get(pid)
        if buf is None:
            buf = AppendBuffer()
            self.state.stream_acc[pid] = buf

        t = self.state.stream_timer.get(pid)
        if t is None:
            t = QTimer(self.renderer.window)
            t.setSingleShot(True)
            t.setInterval(self.state.stream_interval_ms)

            def on_timeout(pid=pid):
                self.stream_flush(pid, force=False)

            t.timeout.connect(on_timeout)
            self.state.stream_timer[pid] = t

        return buf, t

    def _run_stream_begin_js(self, pid: int, node, script: str) -> None:
        """Run begin/reset JS and open QWebChannel streaming only afterwards."""
        seq = self.stream_begin_arm(pid)

        def ready(_value=None, pid=pid, seq=seq):
            self.stream_begin_release(pid, seq)

        try:
            # PySide6 overload: script, worldId, resultCallback.
            node.page().runJavaScript(script, 0, ready)
        except Exception:
            # Preserve the old best-effort behavior when the page is being
            # destroyed, but never leave the Python stream permanently gated.
            self.stream_begin_release(pid, seq)

    # ========================================
    # Private: partial stream buffers
    # ========================================

    def _partial_stream_get(self, key: tuple) -> tuple[AppendBuffer, QTimer]:
        buf = self.state.partial_stream_acc.get(key)
        if buf is None:
            buf = AppendBuffer()
            self.state.partial_stream_acc[key] = buf

        timer = self.state.partial_stream_timer.get(key)
        if timer is None:
            timer = QTimer(self.renderer.window)
            timer.setSingleShot(True)
            timer.setInterval(self.state.stream_interval_ms)

            def on_timeout(key=key):
                self._partial_stream_flush(key, force=False)

            timer.timeout.connect(on_timeout)
            self.state.partial_stream_timer[key] = timer
        return buf, timer

    def _partial_stream_flush(self, key: tuple, force: bool = False):
        buf = self.state.partial_stream_acc.get(key)
        if buf is None or buf.is_empty():
            timer = self.state.partial_stream_timer.get(key)
            if timer and timer.isActive():
                try:
                    timer.stop()
                except Exception:
                    pass
            return

        pid, parent_id, part_key = key
        node = self.renderer.get_output_node_by_pid(pid)
        if node is None:
            buf.clear()
            return

        timer = self.state.partial_stream_timer.get(key)
        if timer and timer.isActive():
            try:
                timer.stop()
            except Exception:
                pass

        data = buf.get_and_clear()
        begin = key not in self.state.partial_stream_started
        self.state.partial_stream_started.add(key)
        try:
            parent_ctx = self.state.pids.get(pid).item if pid in self.state.pids else None
            agent_name = self.renderer.agents.legacy_agent_name_prefix(parent_ctx, part_key=part_key)
            node.page().runJavaScript(
                "if (typeof window.appendPartialStream !== 'undefined') "
                f"appendPartialStream({json.dumps(parent_id, ensure_ascii=False)},"
                f"{json.dumps(part_key, ensure_ascii=False)},"
                f"{json.dumps(data, ensure_ascii=False)},"
                f"{'true' if begin else 'false'},"
                f"{json.dumps(agent_name, ensure_ascii=False)});"
            )
        except Exception:
            pass

