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

import json
import os
import re
import html as _html

from datetime import datetime
from typing import Optional, List, Any

from PySide6.QtCore import QTimer

from pygpt_net.core.render.base import BaseRenderer
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.ui.widget.textarea.web import ChatWebOutput
from pygpt_net.utils import sizeof_fmt
from pygpt_net.core.tabs.tab import Tab

from .body import Body
from .debug import malloc_trim_linux, parse_bytes, mem_used_bytes
from .helpers import Helpers
from .parser import Parser
from .pid import PidData
from .parts.state import RenderState
from .parts.session import Session
from .parts.view import View
from .parts.loading import Loading
from .parts.streaming import Streaming
from .parts.agents import Agents
from .parts.artifacts import Artifacts
from .parts.tools import Tools
from .parts.history import History
from .parts.messages import Messages
from .parts.timeline import Timeline
from .parts.bridge import Bridge


class Renderer(BaseRenderer):
    """Public rendering facade coordinating composed web rendering components."""

    NODE_INPUT = 0
    NODE_OUTPUT = 1
    RE_AMP_LT_GT = re.compile(r'&amp;(lt|gt);')
    RE_MD_STRUCTURAL = re.compile(
        r'(?m)(^|\n)\s*(?:#{1,6}\s|[-*+]\s|\d+\.\s|>\s|\|[^|\n]+\|[^|\n]*\|)'
    )

    # ========================================
    # Initialization
    # ========================================

    def __init__(self, window=None):
        """Create the session and its rendering components."""
        super().__init__(window)
        self.window = window
        self.body = Body(window)
        self.helpers = Helpers(window)
        self.parser = Parser(window)
        self.state = RenderState(self.window.core.config if self.window else None)
        self.session = Session(self)
        self.view = View(self)
        self.loading = Loading(self)
        self.streaming = Streaming(self)
        self.agents = Agents(self)
        self.artifacts = Artifacts(self)
        self.tools = Tools(self)
        self.history = History(self)
        self.messages = Messages(self)
        self.timeline = Timeline(self)
        self.bridge = Bridge(self)

        # Paths and icons
        app_path = self.window.core.config.get_app_path() if self.window else ""
        self._icon_expand = os.path.join(app_path, "data", "icons", "expand.svg")
        self._icon_sync = os.path.join(app_path, "data", "icons", "sync.svg")
        self._agent_avatar = os.path.join(app_path, "data", "icons", "robot.svg")
        self._file_prefix = 'file:///' if self.window and self.window.core.platforms.is_windows() else 'file://'

        # Pid-related cached methods
        self._get_pid = None
        self._get_output_node_by_meta = None
        self._get_output_node_by_pid = None
        if (self.window and hasattr(self.window, "core")
                and hasattr(self.window.core, "ctx")
                and hasattr(self.window.core.ctx, "output")):
            self._get_pid = self.window.core.ctx.output.get_pid
            self._get_output_node_by_meta = self.window.core.ctx.output.get_current
            self._get_output_node_by_pid = self.window.core.ctx.output.get_by_pid

        # store last memory cleanup time
        self._last_memory_cleanup = None
        self._min_memory_cleanup_interval = 30  # seconds
        self._min_memory_cleanup_bytes = 2147483648  # 2GB, TODO: init at startup based on system RAM

    # ========================================
    # Session and page lifecycle
    # ========================================

    def prepare(self):
        return self.session.prepare()

    def on_load(self, meta: CtxMeta = None):
        return self.session.on_load(meta)

    def on_page_loaded(
            self,
            meta: Optional[CtxMeta] = None,
            tab: Optional[Tab] = None
    ):
        return self.session.on_page_loaded(meta, tab)

    def reload(self, meta: Optional[CtxMeta] = None):
        return self.session.reload(meta)

    def fresh(self, meta: Optional[CtxMeta] = None, force: bool = False):
        return self.session.fresh(meta, force)

    def reset(self, meta: Optional[CtxMeta] = None, clear_nodes: bool = True):
        return self.session.reset(meta, clear_nodes)

    def remove_pid(self, pid: int):
        return self.session.remove_pid(pid)

    # ========================================
    # PID and output node access
    # ========================================

    def get_pid(self, meta: CtxMeta) -> Optional[int]:
        """
        Get PID for context meta

        :param meta: context meta
        :return: PID or None
        """
        if self._get_pid is None:
            self._get_pid = self.window.core.ctx.output.get_pid
        return self._get_pid(meta)

    def get_pid_data(self, pid: int) -> Optional[PidData]:
        return self.session.get_pid_data(pid)

    def get_input_node(self) -> ChatInput:
        """
        Get input node

        :return: input node
        """
        return self.window.ui.nodes['input']

    def get_output_node(self, meta: Optional[CtxMeta] = None) -> Optional[ChatWebOutput]:
        """
        Get output node

        :param meta: context meta
        :return: output node or None
        """
        if self._get_output_node_by_meta is None:
            self._get_output_node_by_meta = self.window.core.ctx.output.get_current
        return self._get_output_node_by_meta(meta)

    def get_output_node_by_pid(self, pid: Optional[int]) -> Optional[ChatWebOutput]:
        """
        Get output node by PID

        :param pid: context PID
        :return: output node or None
        """
        if self._get_output_node_by_pid is None:
            self._get_output_node_by_pid = self.window.core.ctx.output.get_by_pid
        return self._get_output_node_by_pid(pid)

    # ========================================
    # Response lifecycle
    # ========================================

    def begin(self, meta: CtxMeta, ctx: CtxItem, stream: bool = False):
        """
        Render begin

        :param meta: context meta
        :param ctx: context item
        :param stream: True if streaming mode
        """
        pid = self.session.get_or_create_pid(meta)
        self.session.init(pid)
        self.view.reset_names(meta)
        self.tools.tool_output_end()
        self.state.prev_chunk_replace = False

        # Ensure stream header identity is up-to-date (agent/preset override)
        try:
            header = self.messages.get_name_header(ctx, stream=True)
            if pid is not None:
                self.state.pids[pid].header = header
                self.state.stream_header[pid] = header or ""
        except Exception:
            pass

        try:
            msg_id = json.dumps(str(getattr(ctx, "id", "") or ""), ensure_ascii=False)
            self.get_output_node(meta).page().runJavaScript(
                "if (typeof window.begin !== 'undefined') "
                f"begin({msg_id});"
            )
        except Exception:
            pass

    def end(self, meta: CtxMeta, ctx: CtxItem, stream: bool = False):
        """
        Render end

        :param meta: context meta
        :param ctx: context item
        :param stream: True if streaming mode
        """
        pid = self.session.get_or_create_pid(meta)
        if pid is None:
            return
        # END is a lifecycle boundary only. Durable DOM changes are explicit
        # SYNC/REPLACE mutations; a live row is promoted by STREAM_END.
        self.state.pids[pid].item = None

        try:
            msg_id = json.dumps(str(getattr(ctx, "id", "") or ""), ensure_ascii=False)
            self.get_output_node(meta).page().runJavaScript(
                "if (typeof window.end !== 'undefined') "
                f"end({msg_id});"
            )
        except Exception:
            pass

        self.state.pids[pid].clear()
        self.auto_cleanup(meta)

    def end_extra(self, meta: CtxMeta, ctx: CtxItem, stream: bool = False):
        """
        Render end extra

        :param meta: context meta
        :param ctx: context item
        :param stream: True if streaming mode
        """
        self.view.to_end(ctx)

    # ========================================
    # Loading indicators
    # ========================================

    def state_changed(
            self,
            state: str,
            meta: CtxMeta,
            loading_delay_ms: int = 0,
            loading_wait_for_input: bool = False,
    ):
        return self.loading.state_changed(state, meta, loading_delay_ms, loading_wait_for_input)

    # ========================================
    # History and messages
    # ========================================

    def append_context(self, meta: CtxMeta, items: List[CtxItem], clear: bool = True):
        return self.history.append_context(meta, items, clear)

    def append_input(self, meta: CtxMeta, ctx: CtxItem, flush: bool = True, append: bool = False):
        return self.messages.append_input(meta, ctx, flush, append)

    def append_output(self, meta: CtxMeta, ctx: CtxItem, flush: bool = True,
                      prev_ctx: Optional[CtxItem] = None, next_ctx: Optional[CtxItem] = None):
        return self.messages.append_output(meta, ctx, flush, prev_ctx, next_ctx)

    def append_extra(self, meta: CtxMeta, ctx: CtxItem, footer: bool = False, render: bool = True) -> str:
        return self.artifacts.append_extra(meta, ctx, footer, render)

    # ========================================
    # Message mutations
    # ========================================

    def replace_input(self, meta: CtxMeta, ctx: CtxItem, reason: Optional[str] = None) -> None:
        return self.bridge.replace_input(meta, ctx, reason)

    def replace_output(self, meta: CtxMeta, ctx: CtxItem, reason: Optional[str] = None) -> None:
        return self.bridge.replace_output(meta, ctx, reason)

    def sync_output(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            replace_text: bool = False,
            reason: Optional[str] = None,
    ) -> None:
        return self.bridge.sync_output(meta, ctx, replace_text, reason)

    def finalize_output(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            replace_text: bool = False,
            reason: Optional[str] = None,
    ) -> None:
        return self.bridge.finalize_output(meta, ctx, replace_text, reason)

    # ========================================
    # Streaming
    # ========================================

    def stream_begin(self, meta: CtxMeta, ctx: CtxItem):
        return self.streaming.stream_begin(meta, ctx)

    def append_chunk(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text_chunk: str,
            begin: bool = False,
            part_key: Optional[object] = None,
    ):
        return self.streaming.append_chunk(meta, ctx, text_chunk, begin, part_key)

    def next_chunk(self, meta: CtxMeta, ctx: CtxItem):
        return self.streaming.next_chunk(meta, ctx)

    def stream_end(self, meta: CtxMeta, ctx: CtxItem):
        return self.streaming.stream_end(meta, ctx)

    def append_part_chunk(
            self,
            meta: CtxMeta,
            parent_ctx: CtxItem,
            part_key: object,
            text_chunk: str,
            begin: bool = False,
    ):
        return self.streaming.append_part_chunk(meta, parent_ctx, part_key, text_chunk, begin)

    def discard_part_streams(self, meta: Optional[CtxMeta] = None):
        return self.streaming.discard_part_streams(meta)

    # ========================================
    # Workflows and status
    # ========================================

    def agent_v2_final_begin(self, meta: CtxMeta, ctx: CtxItem):
        return self.agents.agent_v2_final_begin(meta, ctx)

    def agent_status(self, meta: CtxMeta, ctx: CtxItem, status: str):
        return self.agents.agent_status(meta, ctx, status)

    def agent_status_clear(self, meta: CtxMeta, ctx: CtxItem):
        return self.agents.agent_status_clear(meta, ctx)

    # ========================================
    # Live messages
    # ========================================

    def append_live(self, meta: CtxMeta, ctx: CtxItem, text_chunk: str, begin: bool = False):
        return self.streaming.append_live(meta, ctx, text_chunk, begin)

    def clear_live(self, meta: CtxMeta, ctx: CtxItem):
        return self.streaming.clear_live(meta, ctx)

    # ========================================
    # Tool output
    # ========================================

    def tool_output_begin(
            self,
            meta: CtxMeta,
            tool_names: Optional[list] = None,
            ctx: Optional[CtxItem] = None,
    ):
        return self.tools.tool_output_begin(meta, tool_names, ctx)

    def tool_output_snapshot(self, meta: CtxMeta, ctx: CtxItem):
        return self.tools.tool_output_snapshot(meta, ctx)

    def tool_output_append(self, meta: CtxMeta, content: str):
        return self.tools.tool_output_append(meta, content)

    def tool_output_update(self, meta: CtxMeta, content: str):
        return self.tools.tool_output_update(meta, content)

    def tool_output_clear(
            self,
            meta: CtxMeta,
            ctx: Optional[CtxItem] = None,
            immediate: bool = False,
    ):
        return self.tools.tool_output_clear(meta, ctx, immediate)

    def tool_output_end(self):
        return self.tools.tool_output_end()

    # ========================================
    # Message controls
    # ========================================

    def on_reply_submit(self, ctx: CtxItem):
        return self.view.on_reply_submit(ctx)

    def on_edit_submit(self, ctx: CtxItem):
        return self.view.on_edit_submit(ctx)

    def remove_item(self, ctx: CtxItem):
        return self.view.remove_item(ctx)

    def remove_items_from(self, ctx: CtxItem):
        return self.view.remove_items_from(ctx)

    def on_enable_edit(self, live: bool = True):
        return self.view.on_enable_edit(live)

    def on_disable_edit(self, live: bool = True):
        return self.view.on_disable_edit(live)

    def on_enable_timestamp(self, live: bool = True):
        return self.view.on_enable_timestamp(live)

    def on_disable_timestamp(self, live: bool = True):
        return self.view.on_disable_timestamp(live)

    # ========================================
    # View and WebView bridge
    # ========================================

    def clear_input(self):
        return self.view.clear_input()

    def clear_output(self, meta: Optional[CtxMeta] = None):
        return self.session.clear_output(meta)

    def clear_all(self):
        return self.view.clear_all()

    def resume_auto_follow_if_near_bottom(
            self,
            meta: CtxMeta,
            margin: int = 128,
            force: bool = False
    ):
        return self.view.resume_auto_follow_if_near_bottom(meta, margin, force)

    def remeasure_user_messages(self, pid: Optional[int]) -> None:
        return self.bridge.remeasure_user_messages(pid)

    def on_theme_change(self):
        return self.view.on_theme_change()

    def on_js_ready(self, pid: int) -> None:
        return self.bridge.on_js_ready(pid)

    def eval_js(self, script: str):
        return self.bridge.eval_js(script)

    # ========================================
    # Payload formatting
    # ========================================

    def to_json(self, data: Any) -> str:
        """
        Convert data to JSON object

        :param data: data to convert
        :return: JSON object or None
        """
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    def sanitize_html(self, html: str) -> str:
        """
        Sanitize HTM

        :param html: HTML string
        """
        return html

    # ========================================
    # Memory cleanup and diagnostics
    # ========================================

    def auto_cleanup(self, meta: CtxMeta):
        """
        Automatic cleanup after context is done

        If memory limit is set, perform fresh() cleanup when exceeded.
        """
        try:
            limit_bytes = parse_bytes(self.window.core.config.get('render.memory.limit', 0))
        except Exception as e:
            self.window.core.debug.log("[Renderer] auto-cleanup:", e)
            limit_bytes = 0

        if limit_bytes <= 0:
            self.auto_cleanup_soft(meta)
            return
        rss = mem_used_bytes()
        excluded = 0
        try:
            excluded = self.window.core.audio.get_memory_excluded_bytes()
        except Exception:
            pass
        used = max(0, rss - excluded)
        if used >= limit_bytes:
            now = datetime.now()
            if self._last_memory_cleanup is not None:
                delta = (now - self._last_memory_cleanup).total_seconds()
                if delta < self._min_memory_cleanup_interval:
                    return
            try:
                self._last_memory_cleanup = now
                self.session.fresh(meta, force=True)
                details = ""
                if excluded > 0:
                    details = f" (RSS: {sizeof_fmt(rss)}, excluded: {sizeof_fmt(excluded)})"
                print(
                    f"[Renderer] Memory auto-cleanup done, reached limit: "
                    f"{sizeof_fmt(used)} / {sizeof_fmt(limit_bytes)}{details}"
                )
            except Exception as e:
                self.window.core.debug.log(e)
        else:
            self.auto_cleanup_soft(meta)

    def auto_cleanup_soft(self, meta: CtxMeta = None):
        """
        Try to trim memory on Linux

        Soft cleanup, called after each context is done.
        """
        def cleanup():
            malloc_trim_linux()
        try:
            QTimer.singleShot(0, cleanup)
        except Exception:
            pass

    def is_debug(self) -> bool:
        """
        Check debug flag

        :return: True if debug enabled
        """
        return self.window.core.config.get("debug.render", False)

    def append_debug(self, ctx: CtxItem, pid, title: Optional[str] = None) -> str:
        """
        Append debug info HTML (legacy path)

        :param ctx: context item
        :param pid: context PID
        :param title: optional title
        :return: HTML string
        """
        if title is None:
            title = "debug"
        return f"<div class='debug'><b>{title}:</b> pid: {pid}, ctx: {_html.escape(ctx.to_debug())}</div>"
