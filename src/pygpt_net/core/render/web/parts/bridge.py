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

"""WebView delivery, readiness queues and JavaScript mutations."""

from typing import Optional
from PySide6.QtCore import QTimer
from pygpt_net.core.render.protocol import RenderMutation, RenderOp
from pygpt_net.item.ctx import CtxItem, CtxMeta


class Bridge:
    """WebView delivery, readiness queues and JavaScript mutations.

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
    # Message mutations
    # ========================================

    def emit_mutation(self, meta: CtxMeta, mutation: RenderMutation) -> None:
        """Send one renderer mutation through the existing ordered node channel."""
        pid = self.renderer.session.get_or_create_pid(meta)
        if pid is None:
            return
        self.flush_output(pid, mutation.to_json(), replace=False)

    def replace_input(self, meta: CtxMeta, ctx: CtxItem, reason: Optional[str] = None) -> None:
        """Explicitly replace one durable user message."""
        block = self.renderer.messages.build_input_block(meta, ctx)
        if block is None:
            return
        self.emit_mutation(meta, RenderMutation(
            op=RenderOp.REPLACE_INPUT,
            msg_id=getattr(ctx, "id", None),
            block=block.to_dict(),
            reason=reason,
        ))

    def sync_output(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            replace_text: bool = False,
            reason: Optional[str] = None,
    ) -> None:
        """Synchronize one durable assistant message in place.

        By default the existing text/timeline is preserved. This is the normal
        post-stream/post-tool path and replaces the historical full-chat RELOAD.
        """
        self.renderer.agents.update_agent_working(meta, ctx)
        block = self.renderer.messages.build_output_block(meta, ctx)
        if block is None:
            return
        self.emit_mutation(meta, RenderMutation(
            op=RenderOp.SYNC_OUTPUT,
            msg_id=getattr(ctx, "id", None),
            block=block.to_dict(),
            replace_text=replace_text,
            reason=reason,
        ))

    def finalize_output(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            replace_text: bool = False,
            reason: Optional[str] = None,
    ) -> None:
        """Finalize a live assistant stream without rebuilding or replacing it."""
        input_text = self.renderer.messages.prepare_input(meta, ctx, flush=False, append=False)
        output_text = self.renderer.messages.prepare_output(meta=meta, ctx=ctx, flush=False)
        block = self.renderer.messages.build_render_block(
            meta,
            ctx,
            input_text=input_text,
            output_text=output_text,
            history_date_label=self.renderer.history.get_live_input_date_label(meta, ctx),
        )
        if block is None:
            return
        self.emit_mutation(meta, RenderMutation(
            op=RenderOp.FINALIZE_OUTPUT,
            msg_id=getattr(ctx, "id", None),
            block=block.to_dict(),
            replace_text=replace_text,
            reason=reason,
        ))

    def replace_output(self, meta: CtxMeta, ctx: CtxItem, reason: Optional[str] = None) -> None:
        """Explicitly replace assistant text when the authoritative text changed."""
        block = self.renderer.messages.build_output_block(meta, ctx)
        if block is None:
            return
        self.emit_mutation(meta, RenderMutation(
            op=RenderOp.REPLACE_OUTPUT,
            msg_id=getattr(ctx, "id", None),
            block=block.to_dict(),
            replace_text=True,
            reason=reason,
        ))

    # ========================================
    # Node delivery
    # ========================================

    def append_node(self, meta: CtxMeta, ctx: CtxItem, html: str, type: int = 1,
                    prev_ctx: Optional[CtxItem] = None, next_ctx: Optional[CtxItem] = None):
        """
        Backward compatible: when called, convert HTML-like path to RenderBlock and send JSON.

        :param meta: context meta
        :param ctx: context item
        :param html: HTML content
        :param type: NODE_INPUT or NODE_OUTPUT
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        """
        if ctx.hidden:
            return

        pid = self.renderer.session.get_or_create_pid(meta)

        # Convert to RenderBlock JSON
        input_text = html if type == self.renderer.NODE_INPUT else None
        output_text = html if type == self.renderer.NODE_OUTPUT else None
        block = self.renderer.messages.build_render_block(meta, ctx, input_text, output_text, prev_ctx=prev_ctx, next_ctx=next_ctx)
        if block:
            self.append(pid, block.to_json(wrap=True))

    def append_context_item(self, meta: CtxMeta, ctx: CtxItem,
                            prev_ctx: Optional[CtxItem] = None, next_ctx: Optional[CtxItem] = None):
        """
        Append context item as one RenderBlock with input+output (if present)

        :param meta: context meta
        :param ctx: context item
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        """
        input_text = self.renderer.messages.prepare_input(meta, ctx, flush=False, append=False)
        output_text = self.renderer.messages.prepare_output(meta, ctx, flush=False, prev_ctx=prev_ctx, next_ctx=next_ctx)
        if output_text:
            self.renderer.history.hide_previous_agent_action_icons(meta, ctx)
        block = self.renderer.messages.build_render_block(meta, ctx, input_text, output_text, prev_ctx=prev_ctx, next_ctx=next_ctx)
        if block:
            pid = self.renderer.session.get_or_create_pid(meta)
            self.append(pid, block.to_json(wrap=True))

    def append(self, pid, payload: str, flush: bool = False, replace: bool = False):
        """
        Append payload (HTML legacy or JSON string) to output.

        :param pid: context PID
        :param payload: payload to append
        :param flush: True if flush immediately (legacy HTML path)
        :param replace: True if replace whole output (legacy HTML path)
        """
        if self.state.pids[pid].loaded and not self.state.pids[pid].use_buffer:
            # A full history replacement must be one browser-side transaction.
            # Clearing input/output here uses separate runJavaScript calls and can
            # expose an empty frame before nodeReplace reaches QWebEngine, which is
            # especially visible after the first streamed turn in a new meta.
            if not replace:
                self.renderer.session.clear_chunks(pid)
            if payload:
                self.flush_output(pid, payload, replace)
            self.state.pids[pid].clear()
        else:
            if not flush:
                self.state.pids[pid].append_html(payload)

    def flush_output(self, pid: int, payload: str, replace: bool = False):
        """
        Send content via QWebChannel (JSON or HTML string).

        :param pid: context PID
        :param payload: payload to send
        :param replace: True if replace nodes list
        """
        if pid is None:
            return
        node = self.renderer.get_output_node_by_pid(pid)
        if node is None:
            return
        try:
            if pid not in self.state.bridge_ready:
                self.state.bridge_ready[pid] = False
                self.state.pending_nodes.setdefault(pid, [])
            if self.state.bridge_ready.get(pid, False):
                br = getattr(node.page(), "bridge", None)
                if br is not None:
                    if replace and hasattr(br, "nodeReplace"):
                        # nodeReplace performs the stream/input/node cleanup and
                        # replacement atomically in JS. Do not clear nodes first:
                        # that separate browser call can be painted as a blank frame.
                        br.nodeReplace.emit(payload)
                        return
                    if not replace and hasattr(br, "node"):
                        br.node.emit(payload)
                        return
            # Not ready -> queue
            self._queue_node(pid, payload, replace)
        except Exception:
            # Fallback to runJavaScript path
            try:
                if replace:
                    node.page().runJavaScript(
                        f"if (typeof window.replaceNodes !== 'undefined') replaceNodes({self.renderer.to_json(payload)});"
                    )
                else:
                    node.page().runJavaScript(
                        f"if (typeof window.appendNode !== 'undefined') appendNode({self.renderer.to_json(payload)});"
                    )
            except Exception:
                pass

    # ========================================
    # WebView readiness
    # ========================================

    def on_js_ready(self, pid: int) -> None:
        """
        Called by JS via bridge when ready

        :param pid: context PID
        """
        if pid not in self.state.bridge_ready:
            self.state.bridge_ready[pid] = False
            self.state.pending_nodes.setdefault(pid, [])
        self.state.bridge_ready[pid] = True
        self._drain_pending_nodes(pid)

    # ========================================
    # View maintenance and diagnostics
    # ========================================

    def clear_nodes(self, pid: Optional[int]):
        """
        Clear nodes list

        :param pid: context PID
        """
        try:
            self.renderer.get_output_node_by_pid(pid).page().runJavaScript(
                "if (typeof window.clearNodes !== 'undefined') clearNodes();"
            )
        except Exception:
            pass

    def remeasure_user_messages(self, pid: Optional[int]) -> None:
        """
        Re-evaluate user-message auto-collapse after a hidden WebView becomes visible.

        A chat restored while another output tab is active can be laid out with an
        invalid/transient viewport.  In that state short user messages may be
        classified as taller than the collapse threshold.  Re-run the existing
        collapse manager after two animation frames, when Chromium has the final
        visible-tab geometry.

        :param pid: chat tab PID
        """
        if pid is None:
            return
        node = self.renderer.get_output_node_by_pid(pid)
        if node is None:
            return
        script = r"""
            (() => {
                const run = () => {
                    try {
                        if (typeof runtime === 'undefined' ||
                            !runtime.nodes || !runtime.nodes._userCollapse) return;
                        const mgr = runtime.nodes._userCollapse;
                        mgr.apply(document);
                        mgr.remeasureAll();
                    } catch (_) {}
                };
                try {
                    if (typeof requestAnimationFrame === 'function') {
                        requestAnimationFrame(() => requestAnimationFrame(run));
                    } else {
                        setTimeout(run, 0);
                    }
                } catch (_) {
                    setTimeout(run, 0);
                }
            })();
        """
        try:
            node.page().runJavaScript(script)
        except Exception:
            pass

    def eval_js(self, script: str):
        """
        Evaluate arbitrary JS in the output node context.

        ``QWebEnginePage.runJavaScript`` expects the callback as the third
        argument (after ``worldId``).  Passing it as the second argument can be
        interpreted as a world ID and fail before the script is evaluated.

        Console output (console.log/warn/error/...) is delivered separately by
        ``javaScriptConsoleMessage``.  The callback below therefore reports
        only an actual expression result and skips JavaScript undefined/null
        values represented by Qt as ``None``.

        :param script: JS code to run
        """
        current = self.renderer.window.core.ctx.get_current()
        meta = self.renderer.window.core.ctx.get_meta_by_id(current)
        node = self.renderer.get_output_node(meta)
        if node is None:
            self.renderer.window.controller.debug.log("[JS] No active WebEngine output", window=True)
            return

        def callback(val):
            if val is not None:
                self.renderer.window.controller.debug.log(f"[JS] {val}", window=True)

        try:
            node.page().runJavaScript(script, 0, callback)
        except Exception as e:
            self.renderer.window.controller.debug.log(f"[JS] Error: {e}", window=True)

    def js_stream_queue_len(self, pid: int):
        """
        Ask JS side for stream queue length

        :param pid: context PID
        """
        node = self.renderer.get_output_node_by_pid(pid)
        if node is None:
            print(f"PID {pid}: node not found")
            return
        try:
            node.page().runJavaScript(
                "typeof streamQ !== 'undefined' ? streamQ.length : -1",
                lambda val: print(f"PID {pid} streamQ.length =", val)
            )
        except Exception:
            pass

    # ========================================
    # Private: pending node queue
    # ========================================

    def _queue_node(self, pid: int, payload: str, replace: bool):
        """
        Queue node payload until bridge is ready (with safe fallback)

        :param pid: context PID
        :param payload: payload to queue
        :param replace: True if replace nodes list
        """
        q = self.state.pending_nodes.setdefault(pid, [])
        q.append((replace, payload))
        if pid not in self.state.pending_timer:
            t = QTimer(self.renderer.window)
            t.setSingleShot(True)
            t.setInterval(1200)  # ms

            def on_timeout(pid=pid):
                node = self.renderer.get_output_node_by_pid(pid)
                if node:
                    while self.state.pending_nodes.get(pid):
                        rep, pl = self.state.pending_nodes[pid].pop(0)
                        try:
                            if rep:
                                node.page().runJavaScript(
                                    f"if (typeof window.replaceNodes !== 'undefined') "
                                    f"replaceNodes({self.renderer.to_json(pl)});"
                                )
                            else:
                                node.page().runJavaScript(
                                    f"if (typeof window.appendNode !== 'undefined') "
                                    f"appendNode({self.renderer.to_json(pl)});"
                                )
                        except Exception:
                            pass
                self.state.pending_timer.pop(pid, None)

            t.timeout.connect(on_timeout)
            self.state.pending_timer[pid] = t
            t.start()

    def _drain_pending_nodes(self, pid: int):
        """
        Flush queued node payloads

        :param pid: context PID
        """
        node = self.renderer.get_output_node_by_pid(pid)
        if node is None:
            return
        br = getattr(node.page(), "bridge", None)
        if br is None:
            return
        q = self.state.pending_nodes.get(pid, [])
        while q:
            replace, payload = q.pop(0)
            try:
                if replace and hasattr(br, "nodeReplace"):
                    # Keep queued full replacements atomic for the same reason as
                    # flush_output(): JS owns cleanup + replacement in one task.
                    br.nodeReplace.emit(payload)
                elif not replace and hasattr(br, "node"):
                    br.node.emit(payload)
            except Exception:
                break
        t = self.state.pending_timer.pop(pid, None)
        if t:
            try:
                t.stop()
            except Exception:
                pass

