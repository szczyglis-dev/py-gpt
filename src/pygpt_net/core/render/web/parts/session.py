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

"""Chat session lifecycle, WebView loading and per-PID teardown."""

from typing import Optional
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.ui.widget.textarea.web import ChatWebOutput
from pygpt_net.core.tabs.tab import Tab
from ..pid import PidData


class Session:
    """Chat session lifecycle, WebView loading and per-PID teardown.

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
    # Session and PID lifecycle
    # ========================================

    def prepare(self):
        """Prepare renderer"""
        self.state.pids = {}
        self.state.loading_visible = {}
        self.state.loading_reserved = {}
        self.state.loading_show_options = {}
        self.state.reasoning_activity_state = {}
        self.state.workflow_statuses = {}
        self.state.workflow_status_seq = 0
        self.state.stream_begin_seq = {}
        self.state.stream_begin_pending = set()
        self.state.stream_end_pending = {}
        self.state.stream_session_ctx = {}

    def get_or_create_pid(self, meta: CtxMeta) -> Optional[int]:
        """
        Get PID for context meta and create PID data (if not exists).

        Keep the WebView bound to the same meta before its first ``setHtml``.
        This matters when the application starts in plain-text mode: the web
        renderer does not receive ON_LOAD then, so ChatWebOutput.meta is still
        unset when the user switches to WebEngine. Without binding it here,
        loadFinished emits ON_PAGE_LOAD with ``meta=None`` and the buffered
        context is never flushed until the conversation is loaded again.

        :param meta: context meta
        :return: PID or None
        """
        if meta is None:
            return None

        pid = self.renderer.get_pid(meta)
        if pid is None:
            return None

        if pid not in self.state.pids:
            self.pid_create(pid, meta)
        else:
            self.state.pids[pid].meta = meta

        node = self.renderer.get_output_node_by_pid(pid)
        if node is not None:
            node.set_meta(meta)

        return pid

    def pid_create(
            self,
            pid: Optional[int],
            meta: CtxMeta
    ):
        """
        Create PID data

        :param pid: PID
        :param meta: context meta
        """
        if pid is not None:
            self.state.pids[pid] = PidData(pid, meta)

    def get_pid_data(self, pid: int) -> Optional[PidData]:
        """
        Get PID data for given PID

        :param pid: PID
        :return: PidData or None
        """
        if pid in self.state.pids:
            return self.state.pids[pid]

    def init(self, pid: Optional[int]):
        """
        Initialize renderer

        :param pid: context PID
        """
        if pid in self.state.pids and not self.state.pids[pid].initialized:
            self.flush(pid)
            self.state.pids[pid].initialized = True
        else:
            self.clear_chunks(pid)

    def remove_pid(self, pid: int):
        """
        Remove PID and clean resources

        :param pid: context PID
        """
        if pid in self.state.pids:
            del self.state.pids[pid]
        self.renderer.agents.workflow_status_drop_pid(pid)
        self.renderer.streaming.stream_reset(pid)
        t = self.state.stream_timer.pop(pid, None)
        if t:
            try:
                t.stop()
            except Exception:
                pass
        self.state.stream_acc.pop(pid, None)
        self.state.stream_header.pop(pid, None)
        self.state.stream_begin_pending.discard(pid)
        self.state.stream_begin_seq.pop(pid, None)
        self.state.stream_end_pending.pop(pid, None)
        self.state.stream_last_flush.pop(pid, None)
        self.state.loading_visible.pop(pid, None)
        self.state.loading_reserved.pop(pid, None)
        self.state.loading_show_options.pop(pid, None)

        # All transport resources belong to the removed PID, including inline
        # partials and nodes that were waiting for the JavaScript bridge.
        self.renderer.streaming.partial_stream_reset(pid)
        timer = self.state.pending_timer.pop(pid, None)
        if timer is not None:
            try:
                timer.stop()
            except Exception:
                pass
        self.state.pending_nodes.pop(pid, None)
        self.state.bridge_ready.pop(pid, None)
        self.state.stream_session_ctx.pop(pid, None)
        self.state.stream_owner_id.pop(pid, None)

    # ========================================
    # Page loading and delivery
    # ========================================

    def on_load(self, meta: CtxMeta = None):
        """
        On load (meta) event

        :param meta: context meta
        """
        node = self.renderer.get_output_node(meta)
        if not node:
            return
        node.set_meta(meta)
        self.reset(meta)
        try:
            node.page().runJavaScript("if (typeof window.prepare !== 'undefined') prepare();")
        except Exception:
            pass

    def on_page_loaded(
            self,
            meta: Optional[CtxMeta] = None,
            tab: Optional[Tab] = None
    ):
        """
        On page loaded callback from WebEngine widget

        :param meta: context meta
        :param tab: Tab
        """
        if meta is None or tab is None:
            return
        pid = tab.pid
        if pid is None or pid not in self.state.pids:
            return

        node = self.renderer.get_output_node_by_pid(pid)
        if node:
            if pid not in self.state.bridge_ready:
                self.state.bridge_ready[pid] = False
                self.state.pending_nodes.setdefault(pid, [])

        self.state.pids[pid].loaded = True
        if self.state.pids[pid].html != "" and not self.state.pids[pid].use_buffer:
            self.clear_chunks_input(pid)
            self.clear_chunks_output(pid)
            self.renderer.bridge.clear_nodes(pid)
            self.renderer.bridge.append(pid, self.state.pids[pid].html, flush=True)
            self.state.pids[pid].html = ""

        # Reloading the WebView recreates the loader as hidden.  If the last
        # renderer state for this chat is still BUSY (for example while an
        # OpenAI Supervisor is waiting for a Worker), restore the spinner after
        # the new page is ready.  If a real response chunk arrived during the
        # reload, append_chunk(begin=True) has already cleared this flag and we
        # intentionally leave the spinner hidden.
        if self.state.loading_visible.get(pid, False):
            try:
                delay_ms, wait_for_input = self.state.loading_show_options.get(pid, (0, False))
                wait_js = "true" if wait_for_input else "false"
                node.page().runJavaScript(
                    "if (typeof window.showLoading !== 'undefined') "
                    f"showLoading({int(delay_ms)}, {wait_js});"
                )
            except Exception:
                pass
        elif self.state.loading_reserved.get(pid, False):
            try:
                node.page().runJavaScript(
                    "if (typeof window.hideLoading !== 'undefined') hideLoading(true);"
                )
            except Exception:
                pass

    def flush(self, pid: Optional[int]):
        """
        Flush output page HTML (initial)

        :param pid: context PID
        """
        if self.state.pids[pid].loaded:
            return

        html = self.renderer.body.get_html(pid)
        node = self.renderer.get_output_node_by_pid(pid)
        if node is not None:
            try:
                node.setHtml(html, baseUrl="file://")
            except Exception as e:
                print("[Renderer] flush error:", e)

    # ========================================
    # Page reload and recycling
    # ========================================

    def reload(self, meta: Optional[CtxMeta] = None):
        """Reload output, called externally only on theme change to redraw content"""
        self.renderer.window.controller.ctx.refresh_output(meta)

    def fresh(self, meta: Optional[CtxMeta] = None, force: bool = False):
        """
        Reset page / unload old renderer from memory

        :param meta: context meta
        :param force: True if force even when not needed
        """
        plain = self.renderer.window.core.config.get('render.plain')
        if plain:
            return

        pid = self.get_or_create_pid(meta)
        if pid is None:
            return
        node = self.renderer.get_output_node_by_pid(pid)
        if node is not None:
            t = self.state.pending_timer.pop(pid, None)
            if t:
                try:
                    t.stop()
                except Exception:
                    pass
            self.state.bridge_ready[pid] = False
            self.state.pending_nodes[pid] = []
            node.unload()  # unload web page
            self.renderer.streaming.stream_reset(pid)
            self.state.stream_session_ctx.pop(pid, None)
            self.state.stream_owner_id.pop(pid, None)
            self.state.stream_begin_pending.discard(pid)
            self.state.stream_begin_seq.pop(pid, None)
            self.state.stream_end_pending.pop(pid, None)
            self.renderer.streaming.partial_stream_reset(pid)
            self.state.pids[pid].clear(all=True)
            self.state.pids[pid].loaded = False
            self.recycle(node, meta)
            self.flush(pid)

    def recycle(self, node: ChatWebOutput, meta: Optional[CtxMeta] = None):
        """
        Recycle renderer to avoid leaks

        :param node: output node to recycle
        :param meta: context meta
        """
        tab = node.get_tab()
        if tab is None:
            return
        layout = tab.child.layout()

        # Remove the old view from the public registry *before* cleanup.  Widget
        # cleanup may schedule Qt events/timers, and no re-entrant renderer call
        # may be allowed to resolve a view that is already being destroyed.
        outputs = self.renderer.window.ui.nodes['output']
        if outputs.get(tab.pid) is node:
            outputs.pop(tab.pid, None)
        tab.unwrap(node)

        view = ChatWebOutput(self.renderer.window)
        view.set_tab(tab)
        view.set_meta(meta)
        view.signals.save_as.connect(self.renderer.window.controller.chat.render.handle_save_as)
        view.signals.audio_read.connect(self.renderer.window.controller.chat.render.handle_audio_read)

        layout.addWidget(view)  # tab body layout
        tab.add_ref(view)
        view.setVisible(True)
        outputs[tab.pid] = view
        self.renderer.auto_cleanup_soft(meta)

    # ========================================
    # Context reset
    # ========================================

    def reset(self, meta: Optional[CtxMeta] = None, clear_nodes: bool = True):
        """
        Reset current output

        :param meta: context meta
        :param clear_nodes: True if clear nodes list
        """
        pid = self.renderer.get_pid(meta)
        if pid is not None and pid in self.state.pids:
            self.reset_by_pid(pid, clear_nodes=clear_nodes)
        else:
            if meta is not None:
                pid = self.get_or_create_pid(meta)
                self.reset_by_pid(pid, clear_nodes=clear_nodes)
        self.renderer.streaming.clear_live(meta, CtxItem())

    def reset_by_pid(self, pid: Optional[int], clear_nodes: bool = True):
        """
        Reset by PID

        :param pid: context PID
        :param clear_nodes: True if clear nodes list
        """
        self.state.pids[pid].item = None
        self.state.pids[pid].html = ""
        if clear_nodes:
            self.renderer.bridge.clear_nodes(pid)
            self.clear_chunks(pid)
        self.state.pids[pid].images_appended = []
        self.state.pids[pid].urls_appended = []
        self.state.pids[pid].files_appended = []
        node = self.renderer.get_output_node_by_pid(pid)
        if node is not None:
            node.reset_current_content()
        self.renderer.view.reset_names_by_pid(pid)
        self.state.prev_chunk_replace = False
        self.renderer.streaming.stream_reset(pid)
        self.state.stream_begin_pending.discard(pid)
        self.state.stream_begin_seq.pop(pid, None)
        self.state.stream_end_pending.pop(pid, None)
        self.state.stream_session_ctx.pop(pid, None)
        self.state.stream_owner_id.pop(pid, None)
        self.renderer.streaming.partial_stream_reset(pid)

    def clear_output(self, meta: Optional[CtxMeta] = None):
        """
        Clear output

        :param meta: context meta
        """
        self.state.prev_chunk_replace = False
        self.reset(meta)

    # ========================================
    # Chunk buffers
    # ========================================

    def clear_chunks(self, pid: Optional[int]):
        """
        Clear current chunks

        :param pid: context PID
        """
        if pid is None:
            return
        self.clear_chunks_input(pid)
        self.clear_chunks_output(pid)

    def clear_chunks_input(self, pid: Optional[int]):
        """
        Clear chunks from input

        :param pid: context PID
        """
        if pid is None:
            return
        try:
            self.renderer.get_output_node_by_pid(pid).page().runJavaScript(
                "if (typeof window.clearInput !== 'undefined') clearInput();"
            )
        except Exception:
            pass

    def clear_chunks_output(self, pid: Optional[int]):
        """
        Clear chunks from output

        :param pid: context PID
        """
        self.state.prev_chunk_replace = False
        try:
            self.renderer.get_output_node_by_pid(pid).page().runJavaScript(
                "if (typeof window.clearOutput !== 'undefined') clearOutput();"
            )
        except Exception:
            pass
        self.renderer.streaming.stream_reset(pid)
