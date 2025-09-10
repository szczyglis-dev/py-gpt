#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.11 08:00:00                  #
# ================================================== #

import gc
import json
import os
import re
import html as _html
from dataclasses import dataclass, field

from datetime import datetime
from typing import Optional, List, Any
from time import monotonic
from io import StringIO

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWebEngineCore import QWebEnginePage

from pygpt_net.core.render.base import BaseRenderer
from pygpt_net.core.text.utils import has_unclosed_code_tag
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.ui.widget.textarea.web import ChatWebOutput
from pygpt_net.utils import trans, sizeof_fmt
from pygpt_net.core.tabs.tab import Tab

from .body import Body
from .debug import malloc_trim_linux, parse_bytes, mem_used_bytes
from .helpers import Helpers
from .parser import Parser
from .pid import PidData

from pygpt_net.core.events import RenderEvent


class Renderer(BaseRenderer):

    NODE_INPUT = 0
    NODE_OUTPUT = 1
    RE_AMP_LT_GT = re.compile(r'&amp;(lt|gt);')
    RE_MD_STRUCTURAL = re.compile(
        r'(?m)(^|\n)\s*(?:#{1,6}\s|[-*+]\s|\d+\.\s|>\s|\|[^|\n]+\|[^|\n]*\|)'
    )

    @dataclass(slots=True)
    class _AppendBuffer:
        """Small, allocation-friendly buffer for throttled appends."""
        _buf: StringIO = field(default_factory=StringIO, repr=False)
        _size: int = 0

        def append(self, s: str) -> None:
            if not s:
                return
            self._buf.write(s)
            self._size += len(s)

        def is_empty(self) -> bool:
            return self._size == 0

        def get_and_clear(self) -> str:
            """Return content and replace underlying buffer to release memory eagerly."""
            if self._size == 0:
                return ""
            data = self._buf.getvalue()
            old = self._buf
            # Replace the internal buffer instance to drop capacity immediately
            self._buf = StringIO()
            self._size = 0
            try:
                old.close()
            except Exception:
                pass
            return data

        def clear(self) -> None:
            """Clear content and drop buffer capacity."""
            old = self._buf
            self._buf = StringIO()
            self._size = 0
            try:
                old.close()
            except Exception:
                pass

    def __init__(self, window=None):
        super(Renderer, self).__init__(window)
        """
        WebEngine renderer

        :param window: Window instance
        """
        self.window = window
        self.body = Body(window)
        self.helpers = Helpers(window)
        self.parser = Parser(window)
        self.pids = {}
        self.prev_chunk_replace = False
        self.prev_chunk_newline = False

        app_path = self.window.core.config.get_app_path() if self.window else ""
        self._icon_expand = os.path.join(app_path, "data", "icons", "expand.svg")
        self._icon_sync = os.path.join(app_path, "data", "icons", "sync.svg")
        self._file_prefix = 'file:///' if self.window and self.window.core.platforms.is_windows() else 'file://'

        # Bridge readiness for node append/replace path
        self._bridge_ready: dict[int, bool] = {}
        self._pending_nodes: dict[int, list[tuple[bool, str]]] = {}  # (replace, payload)
        self._pending_timer: dict[int, QTimer] = {}

        def _cfg(name: str, default: int) -> int:
            try:
                return int(self.window.core.config.get(name, default) if self.window else default)
            except Exception:
                return default

        # ------------------------------------------------------------------
        # Python-side micro-batching for streaming
        # ------------------------------------------------------------------
        #   render.stream.interval_ms      (int, default 100)
        #   render.stream.max_bytes        (int, default 8192)
        #   render.stream.emergency_bytes  (int, default 524288)

        self._stream_interval_ms: int = _cfg('render.stream.interval_ms', 30)  # ~100ms pacing
        self._stream_max_bytes: int = _cfg('render.stream.max_bytes', 8 * 1024) # idle flush threshold
        self._stream_emergency_bytes: int = _cfg('render.stream.emergency_bytes', 512 * 1024)  # backstop

        # Per-PID streaming state
        self._stream_acc: dict[int, Renderer._AppendBuffer] = {}
        self._stream_timer: dict[int, QTimer] = {}
        self._stream_header: dict[int, str] = {}
        self._stream_last_flush: dict[int, float] = {}

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

    def prepare(self):
        """Prepare renderer"""
        self.pids = {}

    def on_load(self, meta: CtxMeta = None):
        """
        On load (meta) event

        :param meta: context meta
        """
        node = self.get_output_node(meta)
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
        if pid is None or pid not in self.pids:
            return

        node = self.get_output_node_by_pid(pid)
        if node:
            if pid not in self._bridge_ready:
                self._bridge_ready[pid] = False
                self._pending_nodes.setdefault(pid, [])

        self.pids[pid].loaded = True
        if self.pids[pid].html != "" and not self.pids[pid].use_buffer:
            self.clear_chunks_input(pid)
            self.clear_chunks_output(pid)
            self.clear_nodes(pid)
            self.append(pid, self.pids[pid].html, flush=True)
            self.pids[pid].html = ""

    def get_pid(self, meta: CtxMeta) -> Optional[int]:
        """
        Get PID for context meta

        :param meta: context meta
        :return: PID or None
        """
        if self._get_pid is None:
            self._get_pid = self.window.core.ctx.output.get_pid
        return self._get_pid(meta)

    def get_or_create_pid(self, meta: CtxMeta) -> Optional[int]:
        """
        Get PID for context meta and create PID data (if not exists)

        :param meta: context meta
        :return: PID or None
        """
        if meta is not None:
            pid = self.get_pid(meta)
            if pid not in self.pids:
                self.pid_create(pid, meta)
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
            self.pids[pid] = PidData(pid, meta)

    def get_pid_data(self, pid: int) -> Optional[PidData]:
        """
        Get PID data for given PID

        :param pid: PID
        :return: PidData or None
        """
        if pid in self.pids:
            return self.pids[pid]

    def init(self, pid: Optional[int]):
        """
        Initialize renderer

        :param pid: context PID
        """
        if pid in self.pids and not self.pids[pid].initialized:
            self.flush(pid)
            self.pids[pid].initialized = True
        else:
            self.clear_chunks(pid)

    def to_json(self, data: Any) -> str:
        """
        Convert data to JSON object

        :param data: data to convert
        :return: JSON object or None
        """
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    def state_changed(
            self,
            state: str,
            meta: CtxMeta,
    ):
        """
        On kernel state changed event

        :param state: state name
        :param meta: context meta
        """
        if state == RenderEvent.STATE_BUSY:
            if meta:
                pid = self.get_pid(meta)
                if pid is not None:
                    node = self.get_output_node_by_pid(pid)
                    try:
                        node.page().runJavaScript(
                            "if (typeof window.showLoading !== 'undefined') showLoading();"
                        )
                    except Exception as e:
                        pass

        elif state == RenderEvent.STATE_IDLE:
            for pid in self.pids:
                node = self.get_output_node_by_pid(pid)
                if node is not None:
                    try:
                        node.page().runJavaScript(
                            "if (typeof window.hideLoading !== 'undefined') hideLoading();"
                        )
                    except Exception as e:
                        pass

        elif state == RenderEvent.STATE_ERROR:
            for pid in self.pids:
                node = self.get_output_node_by_pid(pid)
                if node is not None:
                    try:
                        node.page().runJavaScript(
                            "if (typeof window.hideLoading !== 'undefined') hideLoading();"
                        )
                    except Exception as e:
                        pass

    def begin(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            stream: bool = False
    ):
        """
        Render begin

        :param meta: context meta
        :param ctx: context item
        :param stream: True if it is a stream
        """
        pid = self.get_or_create_pid(meta)
        self.init(pid)
        self.reset_names(meta)
        self.tool_output_end()
        self.prev_chunk_replace = False

    def end(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            stream: bool = False
    ):
        """
        Render end

        :param meta: context meta
        :param ctx: context item
        :param stream: True if it is a stream
        """
        pid = self.get_or_create_pid(meta)
        if pid is None:
            return
        if self.pids[pid].item is not None and stream:
            self.append_context_item(meta, self.pids[pid].item)
            self.pids[pid].item = None
        else:
            self.reload()
        self.pids[pid].clear()

        # memory cleanup if needed
        self.auto_cleanup(meta)

    def end_extra(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            stream: bool = False
    ):
        """
        Render end extra

        :param meta: context meta
        :param ctx: context item
        :param stream: True if it is a stream
        """
        self.to_end(ctx)

    def stream_begin(
            self,
            meta: CtxMeta,
            ctx: CtxItem
    ):
        """
        Render stream begin

        :param meta: context meta
        :param ctx: context item
        """
        pid = self.get_or_create_pid(meta)
        if pid is not None:
            pctx = self.pids[pid]
            pctx.clear()
            self._stream_reset(pid)
        self.prev_chunk_replace = False
        try:
            self.get_output_node(meta).page().runJavaScript(
                "if (typeof window.beginStream !== 'undefined') beginStream();"
            )
        except Exception:
            pass

        # cache name header once per stream (used by JS to show avatar/name)
        try:
            self.pids[pid].header = self.get_name_header(ctx, stream=True)
        except Exception:
            self.pids[pid].header = ""
        self.update_names(meta, ctx)

    def stream_end(
            self,
            meta: CtxMeta,
            ctx: CtxItem
    ):
        """
        Render stream end

        :param meta: context meta
        :param ctx: context item
        """
        self.prev_chunk_replace = False
        pid = self.get_or_create_pid(meta)
        if pid is None:
            return

        # Flush any pending micro-batch before we close the stream
        self._stream_flush(pid, force=True)
        if self.window.controller.agent.legacy.enabled():
            if self.pids[pid].item is not None:
                self.append_context_item(meta, self.pids[pid].item)
                self.pids[pid].item = None
        self.pids[pid].clear()
        try:
            self.get_output_node(meta).page().runJavaScript("if (typeof window.endStream !== 'undefined') endStream();")
        except Exception:
            pass
        self._stream_reset(pid)  # clean after end

        # memory cleanup if needed
        self.auto_cleanup(meta)

    def auto_cleanup(self, meta: CtxMeta):
        """
        Automatic cleanup after context is done

        :param meta: context meta
        """
        # if memory limit reached - destroy old page view
        try:
            limit_bytes = parse_bytes(self.window.core.config.get('render.memory.limit', 0))
        except Exception as e:
            self.window.core.debug.log("[Renderer] auto-cleanup:", e)
            limit_bytes = 0
        #if limit_bytes <= 0 or limit_bytes < self._min_memory_cleanup_bytes:
        if limit_bytes <= 0:
            self.auto_cleanup_soft(meta)
            return
        used = mem_used_bytes()
        if used >= limit_bytes:
            now = datetime.now()
            if self._last_memory_cleanup is not None:
                delta = (now - self._last_memory_cleanup).total_seconds()
                if delta < self._min_memory_cleanup_interval:
                    return
            try:
                self._last_memory_cleanup = now
                self.fresh(meta, force=True)
                print(f"[Renderer] Memory auto-cleanup done, reached limit: {sizeof_fmt(used)} / {sizeof_fmt(limit_bytes)}")
            except Exception as e:
                self.window.core.debug.log(e)
        else:
            self.auto_cleanup_soft(meta)

    def auto_cleanup_soft(self, meta: CtxMeta = None):
        """
        Automatic soft cleanup (try to trim memory)

        :param meta: context meta
        """
        try:
            malloc_trim_linux()
        except Exception:
            pass

    def append_context(
            self,
            meta: CtxMeta,
            items: List[CtxItem],
            clear: bool = True
    ):
        """
        Append all context items to output

        :param meta: Context meta
        :param items: context items
        :param clear: True if clear all output before append
        """
        self.tool_output_end()
        self.append_context_all(
            meta,
            items,
            clear=clear,
        )

    def append_context_partial(
            self,
            meta: CtxMeta,
            items: List[CtxItem],
            clear: bool = True
    ):
        """
        Append all context items to output (part by part)

        :param meta: Context meta
        :param items: context items
        :param clear: True if clear all output before append
        """
        if len(items) == 0:
            if meta is None:
                return

        pid = self.get_or_create_pid(meta)
        self.init(pid)

        if clear:
            self.reset(meta)

        self.pids[pid].use_buffer = True
        self.pids[pid].html = ""
        prev_ctx = None
        next_item = None
        total = len(items)
        for i, item in enumerate(items):
            self.update_names(meta, item)
            item.idx = i
            if i == 0:
                item.first = True
            next_item = items[i + 1] if i + 1 < total else None
            self.append_context_item(
                meta,
                item,
                prev_ctx=prev_ctx,
                next_ctx=next_item,
            )
            prev_ctx = item

        prev_ctx = None
        next_item = None
        self.pids[pid].use_buffer = False
        if self.pids[pid].html != "":
            self.append(
                pid,
                self.pids[pid].html,
                flush=True,
            )

    def append_context_all(
            self,
            meta: CtxMeta,
            items: List[CtxItem],
            clear: bool = True
    ):
        """
        Append all context items to output (whole context at once)

        :param meta: Context meta
        :param items: context items
        :param clear: True if clear all output before append
        """
        if len(items) == 0:
            if meta is None:
                return

        pid = self.get_or_create_pid(meta)
        self.init(pid)

        if clear:
            self.reset(meta, clear_nodes=False)  # nodes will be cleared later, in flush_output()

        self.pids[pid].use_buffer = True
        self.pids[pid].html = ""
        prev_ctx = None
        next_ctx = None
        total = len(items)
        html_parts = []
        for i, item in enumerate(items):
            self.update_names(meta, item)
            item.idx = i
            if i == 0:
                item.first = True
            next_ctx = items[i + 1] if i + 1 < total else None

            # ignore hidden items
            if item.hidden:
                prev_ctx = item
                continue

            # input node
            data = self.prepare_input(meta, item, flush=False)
            if data:
                html = self.prepare_node(
                    meta=meta,
                    ctx=item,
                    html=data,
                    type=self.NODE_INPUT,
                    prev_ctx=prev_ctx,
                    next_ctx=next_ctx,
                )
                if html:
                    html_parts.append(html)

            # output node
            data = self.prepare_output(
                meta,
                item,
                flush=False,
                prev_ctx=prev_ctx,
                next_ctx=next_ctx,
            )
            if data:
                html = self.prepare_node(
                    meta=meta,
                    ctx=item,
                    html=data,
                    type=self.NODE_OUTPUT,
                    prev_ctx=prev_ctx,
                    next_ctx=next_ctx,
                )
                if html:
                    html_parts.append(html)

            prev_ctx = item

        # flush all nodes at once
        if html_parts:
            self.append(
                pid,
                "".join(html_parts),
                replace=True,
            )

        html_parts.clear()
        html_parts = None
        prev_ctx = None
        next_ctx = None
        self.pids[pid].use_buffer = False
        if self.pids[pid].html != "":
            self.append(
                pid,
                self.pids[pid].html,
                flush=True,
                replace=True,
            )

    def prepare_input(
            self, meta: CtxMeta,
            ctx: CtxItem,
            flush: bool = True,
            append: bool = False
    ) -> Optional[str]:
        """
        Prepare text input

        :param meta: context meta
        :param ctx: context item
        :param flush: flush HTML
        :param append: True if force append node
        :return: Prepared input text or None if internal or empty input
        """
        if ctx.input is None or ctx.input == "":
            return

        text = ctx.input
        if isinstance(ctx.extra, dict) and "sub_reply" in ctx.extra and ctx.extra["sub_reply"]:
            try:
                json_encoded = json.loads(text)
                if isinstance(json_encoded, dict):
                    if "expert_id" in json_encoded and "result" in json_encoded:
                        tmp = "@" + str(ctx.input_name) + ":\n\n" + str(json_encoded["result"])
                        text = tmp
            except json.JSONDecodeError:
                pass

        if ctx.internal \
                and not ctx.first \
                and not ctx.input.strip().startswith("user: ") \
                and not ctx.input.strip().startswith("@"):
            return
        else:
            if ctx.internal and ctx.input.startswith("user: "):
                text = re.sub(r'^user: ', '> ', ctx.input)

        return text.strip()

    def append_input(
            self, meta: CtxMeta,
            ctx: CtxItem,
            flush: bool = True,
            append: bool = False
    ):
        """
        Append text input to output

        :param meta: context meta
        :param ctx: context item
        :param flush: flush HTML
        :param append: True if force append node
        """
        self.tool_output_end()
        pid = self.get_or_create_pid(meta)
        if not flush:
            self.clear_chunks_input(pid)

        self.update_names(meta, ctx)
        text = self.prepare_input(meta, ctx, flush, append)
        if text:
            if flush:
                if self.is_stream() and not append:
                    content = self.prepare_node(meta, ctx, text, self.NODE_INPUT)
                    self.append_chunk_input(meta, ctx, content, begin=False)
                    text = None
                    return
            self.append_node(
                meta=meta,
                ctx=ctx,
                html=text,
                type=self.NODE_INPUT,
            )
        text = None  # free reference

    def prepare_output(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            flush: bool = True,
            prev_ctx: Optional[CtxItem] = None,
            next_ctx: Optional[CtxItem] = None
    ) -> Optional[str]:
        """
        Prepare text output

        :param meta: context meta
        :param ctx: context item
        :param flush: flush HTML
        :param prev_ctx: previous context
        :param next_ctx: next context
        :return: Prepared output text or None if empty output
        """
        output = ctx.output
        if isinstance(ctx.extra, dict) and ctx.extra.get("output"):
            if self.window.core.config.get("agent.output.render.all", False):
                output = ctx.output  # full agent output
            else:
                output = ctx.extra["output"]  # final output only
        else:
            if not output:
                return
        return output.strip()

    def append_output(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            flush: bool = True,
            prev_ctx: Optional[CtxItem] = None,
            next_ctx: Optional[CtxItem] = None
    ):
        """
        Append text output to output

        :param meta: context meta
        :param ctx: context item
        :param flush: flush HTML
        :param prev_ctx: previous context
        :param next_ctx: next context
        """
        self.tool_output_end()
        output = self.prepare_output(
            meta=meta,
            ctx=ctx,
            flush=flush,
            prev_ctx=prev_ctx,
            next_ctx=next_ctx,
        )
        if output:
            self.append_node(
                meta=meta,
                ctx=ctx,
                html=output,
                type=self.NODE_OUTPUT,
                prev_ctx=prev_ctx,
                next_ctx=next_ctx,
            )

    def append_chunk(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text_chunk: str,
            begin: bool = False
    ):
        """
        Append streamed Markdown chunk to JS with micro-batching.
        - No Python-side parsing
        - No Python-side full buffer retention
        - Minimal signal rate thanks to micro-batching (per PID)

        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        pid = self.get_or_create_pid(meta)
        if pid is None:
            return

        pctx = self.pids[pid]
        pctx.item = ctx

        if begin:
            # Reset stream area and loader on the JS side
            try:
                self.get_output_node(meta).page().runJavaScript(
                    "if (typeof window.beginStream !== 'undefined') beginStream(true);"
                )
            except Exception:
                pass
            # Prepare name header for this stream (avatar/name)
            pctx.header = self.get_name_header(ctx, stream=True)
            self._stream_reset(pid)
            self.update_names(meta, ctx)

        if not text_chunk:
            return

        # Push chunk into per-PID micro-batch buffer (will be flushed by a QTimer)
        self._stream_push(pid, pctx.header or "", str(text_chunk))
        # self.get_output_node(meta).page().bridge.chunk.emit(pctx.header or "", str(text_chunk))
        text_chunk = None  # release ref

    def next_chunk(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
    ):
        """
        Flush current stream and start with new chunks

        :param meta: context meta
        :param ctx: context item
        """
        pid = self.get_or_create_pid(meta)
        # Ensure all pending chunks are delivered before switching message
        self._stream_flush(pid, force=True)
        self.pids[pid].item = ctx
        self.pids[pid].buffer = ""
        self.update_names(meta, ctx)
        self.prev_chunk_replace = False
        self.prev_chunk_newline = False
        try:
            self.get_output_node(meta).page().runJavaScript(
                "if (typeof window.nextStream !== 'undefined') nextStream();"
            )
        except Exception:
            pass
        # Reset micro-batch header for the next message
        try:
            self.pids[pid].header = self.get_name_header(ctx, stream=True)
        except Exception:
            self.pids[pid].header = ""

    def append_chunk_input(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text_chunk: str,
            begin: bool = False
    ):
        """
        Append output chunk to output

        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        if not text_chunk:
            return
        if ctx.hidden:
            return
        try:
            self.get_output_node(meta).page().bridge.nodeInput.emit(
                self.sanitize_html(
                    text_chunk
                )
            )
        except Exception:
            pass
        text_chunk = None  # free reference

    def append_live(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text_chunk: str,
            begin: bool = False
    ):
        """
        Append live output chunk to output

        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        pid = self.get_or_create_pid(meta)
        self.pids[pid].item = ctx
        if text_chunk is None or text_chunk == "":
            if begin:
                self.pids[pid].live_buffer = ""
            return

        self.update_names(meta, ctx)
        raw_chunk = str(text_chunk).translate({ord('<'): '&lt;', ord('>'): '&gt;'})
        if begin:
            debug = ""
            if self.is_debug():
                debug = self.append_debug(ctx, pid, "stream")
            if debug:
                raw_chunk = debug + raw_chunk
            self.pids[pid].live_buffer = ""
            self.pids[pid].is_cmd = False
            self.clear_live(meta, ctx)
        self.pids[pid].append_live_buffer(raw_chunk)
        raw_chunk = None  # free reference

        try:
            self.get_output_node(meta).page().runJavaScript(
                f"""replaceLive({self.to_json(
                    self.sanitize_html(
                        self.pids[pid].live_buffer
                    )
                )});"""
            )
        except Exception as e:
            pass

    def clear_live(self, meta: CtxMeta, ctx: CtxItem):
        """
        Clear live output

        :param meta: context meta
        :param ctx: context item
        """
        if meta is None:
            return
        pid = self.get_or_create_pid(meta)
        try:
            self.get_output_node_by_pid(pid).page().runJavaScript(
                "if (typeof window.clearLive !== 'undefined') clearLive();"
            )
        except Exception:
            pass

    def append_node(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            html: str,
            type: int = 1,
            prev_ctx: Optional[CtxItem] = None,
            next_ctx: Optional[CtxItem] = None
    ):
        """
        Append and format raw text to output

        :param meta: context meta
        :param html: text to append
        :param type: type of message
        :param ctx: CtxItem instance
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        """
        if ctx.hidden:
            return

        pid = self.get_or_create_pid(meta)
        self.append(
            pid,
            self.prepare_node(
                meta=meta,
                ctx=ctx,
                html=html,
                type=type,
                prev_ctx=prev_ctx,
                next_ctx=next_ctx,
            )
        )

    def append(
            self,
            pid,
            html: str,
            flush: bool = False,
            replace: bool = False,
    ):
        """
        Append text to output

        :param pid: ctx pid
        :param html: HTML code
        :param flush: True if flush only
        :param replace: True if replace current content
        """
        if self.pids[pid].loaded and not self.pids[pid].use_buffer:
            self.clear_chunks(pid)
            if html:
                self.flush_output(pid, html, replace)
            self.pids[pid].clear()
        else:
            if not flush:
                self.pids[pid].append_html(html)
        html = None  # free reference

    def append_context_item(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            prev_ctx: Optional[CtxItem] = None,
            next_ctx: Optional[CtxItem] = None
    ):
        """
        Append context item to output

        :param meta: context meta
        :param ctx: context item
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        """
        self.append_input(
            meta,
            ctx,
            flush=False,
        )
        self.append_output(
            meta,
            ctx,
            flush=False,
            prev_ctx=prev_ctx,
            next_ctx=next_ctx,
        )

    def append_extra(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            footer: bool = False,
            render: bool = True
    ) -> str:
        """
        Append extra data (images, files, etc.) to output

        :param meta: Context meta
        :param ctx: context item
        :param footer: True if it is a footer
        :param render: True if render, False if only return HTML
        :return: HTML code
        """
        self.tool_output_end()

        pid = self.get_pid(meta)
        appended = set()
        html_parts = []

        c = len(ctx.images)
        if c > 0:
            n = 1
            for image in ctx.images:
                if image is None:
                    continue
                if image in appended or image in self.pids[pid].images_appended:
                    continue
                try:
                    appended.add(image)
                    html_parts.append(self.body.get_image_html(image, n, c))
                    self.pids[pid].images_appended.append(image)
                    n += 1
                except Exception as e:
                    pass

        c = len(ctx.files)
        if c > 0:
            files_html = []
            n = 1
            for file in ctx.files:
                if file in appended or file in self.pids[pid].files_appended:
                    continue
                try:
                    appended.add(file)
                    files_html.append(self.body.get_file_html(file, n, c))
                    self.pids[pid].files_appended.append(file)
                    n += 1
                except Exception as e:
                    pass
            if files_html:
                html_parts.append("<br/><br/>".join(files_html))

        c = len(ctx.urls)
        if c > 0:
            urls_html = []
            n = 1
            for url in ctx.urls:
                if url in appended or url in self.pids[pid].urls_appended:
                    continue
                try:
                    appended.add(url)
                    urls_html.append(self.body.get_url_html(url, n, c))
                    self.pids[pid].urls_appended.append(url)
                    n += 1
                except Exception as e:
                    pass
            if urls_html:
                html_parts.append("<br/><br/>".join(urls_html))

        if self.window.core.config.get('ctx.sources'):
            if ctx.doc_ids is not None and len(ctx.doc_ids) > 0:
                try:
                    docs = self.body.get_docs_html(ctx.doc_ids)
                    html_parts.append(docs)
                except Exception as e:
                    pass

        html = "".join(html_parts)
        if render and html != "":
            if footer:
                self.append(pid, html)
            else:
                try:
                    self.get_output_node(meta).page().runJavaScript(
                        f"""appendExtra('{ctx.id}',{self.to_json(
                            self.sanitize_html(html)
                        )});"""
                    )
                except Exception as e:
                    pass

        return html

    def append_timestamp(
            self,
            ctx: CtxItem,
            text: str,
            type: Optional[int] = None
    ) -> str:
        """
        Append timestamp to text

        :param ctx: context item
        :param text: Input text
        :param type: Type of message
        :return: Text with timestamp (if enabled)
        """
        if ctx is not None and ctx.input_timestamp is not None:
            timestamp = None
            if type == self.NODE_INPUT:
                timestamp = ctx.input_timestamp
            elif type == self.NODE_OUTPUT:
                timestamp = ctx.output_timestamp
            if timestamp is not None:
                ts = datetime.fromtimestamp(timestamp)
                hour = ts.strftime("%H:%M:%S")
                text = f'<span class="ts">{hour}: </span>{text}'
        return text

    def reset(
            self,
            meta: Optional[CtxMeta] = None,
            clear_nodes: bool = True
    ):
        """
        Reset

        :param meta: Context meta
        :param clear_nodes: True if clear nodes
        """
        pid = self.get_pid(meta)
        if pid is not None and pid in self.pids:
            self.reset_by_pid(pid, clear_nodes=clear_nodes)
        else:
            if meta is not None:
                pid = self.get_or_create_pid(meta)
                self.reset_by_pid(pid, clear_nodes=clear_nodes)

        self.clear_live(meta, CtxItem())

    def reset_by_pid(self, pid: Optional[int], clear_nodes: bool = True):
        """
        Reset by PID

        :param pid: context PID
        :param clear_nodes: True if clear nodes
        """
        self.pids[pid].item = None
        self.pids[pid].html = ""
        if clear_nodes:
            self.clear_nodes(pid)
            self.clear_chunks(pid)
        self.pids[pid].images_appended = []
        self.pids[pid].urls_appended = []
        self.pids[pid].files_appended = []
        node = self.get_output_node_by_pid(pid)
        if node is not None:
            node.reset_current_content()
        self.reset_names_by_pid(pid)
        self.prev_chunk_replace = False
        self._stream_reset(pid)  # NEW

    def clear_input(self):
        """Clear input"""
        self.get_input_node().clear()

    def clear_output(
            self,
            meta: Optional[CtxMeta] = None
    ):
        """
        Clear output

        :param meta: Context meta
        """
        self.prev_chunk_replace = False
        self.reset(meta)

    def clear_chunks(self, pid):
        """
        Clear chunks from output

        :param pid: context PID
        """
        if pid is None:
            return
        self.clear_chunks_input(pid)
        self.clear_chunks_output(pid)

    def clear_chunks_input(
            self,
            pid: Optional[int]
    ):
        """
        Clear chunks from input

        :pid: context PID
        """
        if pid is None:
            return
        try:
            self.get_output_node_by_pid(pid).page().runJavaScript(
                "if (typeof window.clearInput !== 'undefined') clearInput();"
            )
        except Exception:
            pass

    def clear_chunks_output(
            self,
            pid: Optional[int]
    ):
        """
        Clear chunks from output

        :pid: context PID
        """
        self.prev_chunk_replace = False
        try:
            self.get_output_node_by_pid(pid).page().runJavaScript(
                "if (typeof window.clearOutput !== 'undefined') clearOutput();"
            )
        except Exception:
            pass
        self._stream_reset(pid)  # NEW

    def clear_nodes(
            self,
            pid: Optional[int]
    ):
        """
        Clear nodes from output

        :pid: context PID
        """
        try:
            self.get_output_node_by_pid(pid).page().runJavaScript(
                "if (typeof window.clearNodes !== 'undefined') clearNodes();"
            )
        except Exception:
            pass

    def prepare_node(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            html: str,
            type: int = 1,
            prev_ctx: Optional[CtxItem] = None,
            next_ctx: Optional[CtxItem] = None
    ) -> str:
        """
        Prepare node HTML

        :param meta: context meta
        :param ctx: CtxItem instance
        :param html: html text
        :param type: type of message
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        :return: prepared HTML
        """
        pid = self.get_or_create_pid(meta)
        if type == self.NODE_OUTPUT:
            return self.prepare_node_output(
                meta=meta,
                ctx=ctx,
                html=html,
                prev_ctx=prev_ctx,
                next_ctx=next_ctx,
            )
        elif type == self.NODE_INPUT:
            return self.prepare_node_input(
                pid=pid,
                ctx=ctx,
                html=html,
                prev_ctx=prev_ctx,
                next_ctx=next_ctx,
            )

    def prepare_node_input(
            self,
            pid,
            ctx: CtxItem,
            html: str,
            prev_ctx: Optional[CtxItem] = None,
            next_ctx: Optional[CtxItem] = None
    ) -> str:
        """
        Prepare input node

        :param pid: context PID
        :param ctx: CtxItem instance
        :param html: html text
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        :return: prepared HTML
        """
        msg_id = "msg-user-" + str(ctx.id) if ctx is not None else ""
        content = self.append_timestamp(
            ctx,
            self.helpers.format_user_text(html),
            type=self.NODE_INPUT
        )
        html = f"<p>{content}</p>"
        html = self.helpers.post_format_text(html)
        name = self.pids[pid].name_user

        if ctx.internal and ctx.input.startswith("[{"):
            name = trans("msg.name.system")
        if type(ctx.extra) is dict and "agent_evaluate" in ctx.extra:
            name = trans("msg.name.evaluation")

        debug = ""
        if self.is_debug():
            debug = self.append_debug(ctx, pid, "input")

        extra_style = ""
        extra = ""
        if ctx.extra is not None and "footer" in ctx.extra:
            extra = ctx.extra["footer"]
            extra_style = "display:block;"

        return f'<div class="msg-box msg-user" id="{msg_id}"><div class="name-header name-user">{name}</div><div class="msg">{html}<div class="msg-extra" style="{extra_style}">{extra}</div>{debug}</div></div>'

    def prepare_node_output(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            html: str,
            prev_ctx: Optional[CtxItem] = None,
            next_ctx: Optional[CtxItem] = None
    ) -> str:
        """
        Prepare output node wrapper; content stays as raw Markdown in HTML (md-block-markdown=1).
        JS (markdown-it) will render it and decorate code blocks.
        Backward compatible with previous JS pipeline and public API.

        :param meta: context meta
        :param ctx: CtxItem instance
        :param html: raw markdown text (pre/post formatted)
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        :return: prepared HTML
        """
        is_cmd = (
                next_ctx is not None and
                next_ctx.internal and
                (len(ctx.cmds) > 0 or (ctx.extra_ctx is not None and len(ctx.extra_ctx) > 0))
        )

        pid = self.get_or_create_pid(meta)
        msg_id = f"msg-bot-{ctx.id}" if ctx is not None else ""

        # raw Markdown (no Python-side HTML rendering); keep existing pre/post formatting hooks
        md_src = self.helpers.pre_format_text(html)
        md_text = self.helpers.post_format_text(md_src)

        # Escape Markdown for safe inclusion as textContent (browser will decode entities back to chars)
        # This ensures no HTML is parsed before markdown-it processes the content on the JS side.
        md_text_escaped = _html.escape(md_text, quote=False)

        # extras/footer
        extra = self.append_extra(meta, ctx, footer=True, render=False)
        footer = self.body.prepare_action_icons(ctx)

        tool_output = ""
        output_class = "display:none"
        if is_cmd:
            if ctx.results is not None and len(ctx.results) > 0 \
                    and isinstance(ctx.extra, dict) and "agent_step" in ctx.extra:
                tool_output = self.helpers.format_cmd_text(str(ctx.input), indent=True)
                output_class = ""
            else:
                tool_output = self.helpers.format_cmd_text(str(next_ctx.input), indent=True)
                output_class = ""
        elif ctx.results is not None and len(ctx.results) > 0 \
                and isinstance(ctx.extra, dict) and "agent_step" in ctx.extra:
            tool_output = self.helpers.format_cmd_text(str(ctx.input), indent=True)

        tool_extra = self.body.prepare_tool_extra(ctx)
        debug = self.append_debug(ctx, pid, "output") if self.is_debug() else ""
        name_header = self.get_name_header(ctx)

        # Native Markdown block: JS runtime will pick [md-block-markdown] and render via markdown-it.
        return (
            f"<div class='msg-box msg-bot' id='{msg_id}'>"
            f"{name_header}"
            f"<div class='msg'>"
            f"<div class='md-block' md-block-markdown='1'>{md_text_escaped}</div>"
            f"<div class='msg-tool-extra'>{tool_extra}</div>"
            f"<div class='tool-output' style='{output_class}'>"
            f"<span class='toggle-cmd-output' onclick='toggleToolOutput({ctx.id});' "
            f"title='{trans('action.cmd.expand')}' role='button'>"
            f"<img src='{self._file_prefix}{self._icon_expand}' width='25' height='25' valign='middle'></span>"
            f"<div class='content' style='display:none'>{tool_output}</div>"
            f"</div>"
            f"<div class='msg-extra'>{extra}</div>"
            f"{footer}{debug}"
            f"</div></div>"
        )

    def get_name_header(self, ctx: CtxItem, stream: bool = False) -> str:
        """
        Get name header for the bot

        :param ctx: CtxItem instance
        :param stream: True if it is a stream
        :return: HTML name header
        """
        meta = ctx.meta
        if meta is None:
            return ""
        preset_id = meta.preset
        if preset_id is None or preset_id == "":
            return ""
        preset = self.window.core.presets.get(preset_id)
        if preset is None:
            return ""
        if not preset.ai_personalize:
            return ""

        output_name = ""
        avatar_html = ""
        if preset.ai_name:
            output_name = preset.ai_name
        if preset.ai_avatar:
            presets_dir = self.window.core.config.get_user_dir("presets")
            avatars_dir = os.path.join(presets_dir, "avatars")
            avatar_path = os.path.join(avatars_dir, preset.ai_avatar)
            if os.path.exists(avatar_path):
                avatar_html = f"<img src=\"{self._file_prefix}{avatar_path}\" class=\"avatar\"> "

        if not output_name and not avatar_html:
            return ""

        if stream:
            return f"{avatar_html}{output_name}"
        else:
            return f"<div class=\"name-header name-bot\">{avatar_html}{output_name}</div>"

    def flush_output(self, pid: int, html: str, replace: bool = False):
        """
        Send content via QWebChannel when ready; otherwise queue with a safe fallback.

        :param pid: context PID
        :param html: HTML code
        :param replace: True if replace current content
        """
        if pid is None:
            return
        node = self.get_output_node_by_pid(pid)
        if node is None:
            return
        try:
            if pid not in self._bridge_ready:
                self._bridge_ready[pid] = False
                self._pending_nodes.setdefault(pid, [])
            if self._bridge_ready.get(pid, False):
                br = getattr(node.page(), "bridge", None)
                if br is not None:
                    if replace and hasattr(br, "nodeReplace"):
                        self.clear_nodes(pid)
                        br.nodeReplace.emit(html)
                        return
                    if not replace and hasattr(br, "node"):
                        br.node.emit(html)
                        return
            # Not ready yet -> queue
            self._queue_node(pid, html, replace)
        except Exception:
            # JS fallback
            try:
                if replace:
                    node.page().runJavaScript(
                        f"if (typeof window.replaceNodes !== 'undefined') replaceNodes({self.to_json(html)});"
                    )
                else:
                    node.page().runJavaScript(
                        f"if (typeof window.appendNode !== 'undefined') appendNode({self.to_json(html)});"
                    )
            except Exception:
                pass

    def reload(self):
        """Reload output, called externally only on theme change to redraw content"""
        self.window.controller.ctx.refresh_output()

    def flush(
            self,
            pid:
            Optional[int]
    ):
        """
        Flush output

        :param pid: context PID
        """
        if self.pids[pid].loaded:
            return

        html = self.body.get_html(pid)
        node = self.get_output_node_by_pid(pid)
        if node is not None:
            node.setHtml(html, baseUrl="file://")

    def fresh(
            self,
            meta: Optional[CtxMeta] = None,
            force: bool = False
    ):
        """
        Reset page / unload old renderer from memory

        :param meta: context meta
        :param force: True if force recycle even if not loaded
        """
        plain = self.window.core.config.get('render.plain')
        if plain:
            return  # plain text mode, no need to recycle

        pid = self.get_or_create_pid(meta)
        if pid is None:
            return
        node = self.get_output_node_by_pid(pid)
        if node is not None:
            t = self._pending_timer.pop(pid, None)
            if t:
                try:
                    t.stop()
                except Exception:
                    pass
            self._bridge_ready[pid] = False
            self._pending_nodes[pid] = []
            node.hide()
            p = node.page()
            p.triggerAction(QWebEnginePage.Stop)
            p.setUrl(QUrl("about:blank"))
            p.history().clear()
            p.setLifecycleState(QWebEnginePage.LifecycleState.Discarded)
            self._stream_reset(pid)
            self.pids[pid].clear(all=True)
            self.pids[pid].loaded = False
            self.recycle(node, meta)
            self.flush(pid)

    def recycle(
            self,
            node: ChatWebOutput,
            meta: Optional[CtxMeta] = None
    ):
        """
        Recycle renderer to free memory and avoid leaks

        Swaps out the old QWebEngineView with a fresh instance.

        :param node: output node
        :param meta: context meta
        """
        tab = node.get_tab()
        layout = tab.child.layout()  # layout of TabBody
        layout.removeWidget(node)
        self.window.ui.nodes['output'].pop(tab.pid, None)
        tab.child.delete_refs()

        node.on_delete()  # destroy old node

        view = ChatWebOutput(self.window)
        view.set_tab(tab)
        view.set_meta(meta)
        view.signals.save_as.connect(self.window.controller.chat.render.handle_save_as)
        view.signals.audio_read.connect(self.window.controller.chat.render.handle_audio_read)

        layout.addWidget(view)
        view.setVisible(True)
        self.window.ui.nodes['output'][tab.pid] = view
        try:
            gc.collect()
        except Exception:
            pass
        self.auto_cleanup_soft(meta)  # trim memory in Linux

    def get_output_node(
            self,
            meta: Optional[CtxMeta] = None
    ) -> Optional[ChatWebOutput]:
        """
        Get output node

        :param meta: context meta
        :return: output node
        """
        if self._get_output_node_by_meta is None:
            self._get_output_node_by_meta = self.window.core.ctx.output.get_output_node_by_meta
        return self._get_output_node_by_meta(meta)

    def get_output_node_by_pid(
            self,
            pid: Optional[int]
    ) -> Optional[ChatWebOutput]:
        """
        Get output node by PID

        :param pid: context pid
        :return: output node
        """
        if self._get_output_node_by_pid is None:
            self._get_output_node_by_pid = self.window.core.ctx.output.get_output_node_by_pid
        return self._get_output_node_by_pid(pid)

    def get_input_node(self) -> ChatInput:
        """
        Get input node

        :return: input node
        """
        return self.window.ui.nodes['input']

    def remove_item(self, ctx: CtxItem):
        """
        Remove item from output

        :param ctx: context item
        """
        try:
            self.get_output_node(ctx.meta).page().runJavaScript(
                f"if (typeof window.removeNode !== 'undefined') removeNode({self.to_json(ctx.id)});"
            )
        except Exception:
            pass

    def remove_items_from(self, ctx: CtxItem):
        """
        Remove item from output

        :param ctx: context item
        """
        try:
            self.get_output_node(ctx.meta).page().runJavaScript(
                f"if (typeof window.removeNodesFromId !== 'undefined') removeNodesFromId({self.to_json(ctx.id)});"
            )
        except Exception:
            pass

    def reset_names(self, meta: CtxMeta):
        """
        Reset names

       :param meta: context meta
        """
        if meta is None:
            return
        pid = self.get_or_create_pid(meta)
        self.reset_names_by_pid(pid)

    def reset_names_by_pid(self, pid: int):
        """
        Reset names by PID

        :param pid: context pid
        """
        self.pids[pid].name_user = trans("chat.name.user")
        self.pids[pid].name_bot = trans("chat.name.bot")

    def on_reply_submit(self, ctx: CtxItem):
        """
        On regenerate submit

        :param ctx: context item
        """
        self.remove_items_from(ctx)

    def on_edit_submit(self, ctx: CtxItem):
        """
        On regenerate submit

        :param ctx: context item
        """
        self.remove_items_from(ctx)

    def on_enable_edit(self, live: bool = True):
        """
        On enable edit icons

        :param live: True if live update
        """
        if not live:
            return
        try:
            nodes = self.get_all_nodes()
            for node in nodes:
                node.page().runJavaScript("if (typeof window.enableEditIcons !== 'undefined') enableEditIcons();")
        except Exception:
            pass

    def on_disable_edit(self, live: bool = True):
        """
        On disable edit icons

        :param live: True if live update
        """
        if not live:
            return
        try:
            nodes = self.get_all_nodes()
            for node in nodes:
                node.page().runJavaScript("if (typeof window.disableEditIcons !== 'undefined') disableEditIcons();")
        except Exception:
            pass

    def on_enable_timestamp(self, live: bool = True):
        """
        On enable timestamp

        :param live: True if live update
        """
        if not live:
            return
        try:
            nodes = self.get_all_nodes()
            for node in nodes:
                node.page().runJavaScript("if (typeof window.enableTimestamp !== 'undefined') enableTimestamp();")
        except Exception:
            pass

    def on_disable_timestamp(self, live: bool = True):
        """
        On disable timestamp

        :param live: True if live update
        """
        if not live:
            return
        try:
            nodes = self.get_all_nodes()
            for node in nodes:
                node.page().runJavaScript("if (typeof window.disableTimestamp !== 'undefined') disableTimestamp();")
        except Exception:
            pass

    def update_names(
            self,
            meta: CtxMeta,
            ctx: CtxItem
    ):
        """
        Update names

        :param meta: context meta
        :param ctx: context item
        """
        pid = self.get_or_create_pid(meta)
        if pid is None:
            return
        if ctx.input_name is not None and ctx.input_name != "":
            self.pids[pid].name_user = ctx.input_name
        if ctx.output_name is not None and ctx.output_name != "":
            self.pids[pid].name_bot = ctx.output_name

    def clear_all(self):
        """Clear all"""
        for pid in self.pids:
            self.clear_chunks(pid)
            self.clear_nodes(pid)
            self.pids[pid].html = ""
            self._stream_reset(pid)

    def scroll_to_bottom(self):
        """Scroll to bottom"""
        pass

    def append_block(self):
        """Append block to output"""
        pass

    def to_end(self, ctx: CtxItem):
        """
        Move cursor to end of output

        :param ctx: context item
        """
        pass

    def get_all_nodes(self) -> list:
        """
        Return all registered nodes

        :return: list of ChatOutput nodes (tabs)
        """
        return self.window.core.ctx.output.get_all()

    # TODO: on lang change

    def reload_css(self):
        """Reload CSS - all, global"""
        to_json = self.to_json(self.body.prepare_styles())
        nodes = self.get_all_nodes()
        for pid in self.pids:
            if self.pids[pid].loaded:
                for node in nodes:
                    try:
                        node.page().runJavaScript(
                            f"if (typeof window.updateCSS !== 'undefined') updateCSS({to_json});"
                        )
                        if self.window.core.config.get('render.blocks'):
                            node.page().runJavaScript(
                                "if (typeof window.enableBlocks !== 'undefined') enableBlocks();"
                            )
                        else:
                            node.page().runJavaScript(
                                "if (typeof window.disableBlocks !== 'undefined') disableBlocks();"
                            )
                    except Exception as e:
                        pass
                return

    def on_theme_change(self):
        """On theme change"""
        self.window.controller.theme.markdown.load()
        for pid in self.pids:
            if self.pids[pid].loaded:
                self.reload_css()
                return

    def tool_output_append(
            self,
            meta: CtxMeta,
            content: str
    ):
        """
        Add tool output (append)

        :param meta: context meta
        :param content: content
        """
        try:
            self.get_output_node(meta).page().runJavaScript(
                f"""if (typeof window.appendToolOutput !== 'undefined') appendToolOutput({self.to_json(
                    self.sanitize_html(content)
                )});"""
            )
        except Exception:
            pass

    def tool_output_update(
            self,
            meta: CtxMeta,
            content: str
    ):
        """
        Replace tool output

        :param meta: context meta
        :param content: content
        """
        try:
            self.get_output_node(meta).page().runJavaScript(
                f"""if (typeof window.updateToolOutput !== 'undefined') updateToolOutput({self.to_json(
                    self.sanitize_html(content)
                )});"""
            )
        except Exception:
            pass

    def tool_output_clear(self, meta: CtxMeta):
        """
        Clear tool output

        :param meta: context meta
        """
        try:
            self.get_output_node(meta).page().runJavaScript(
                f"if (typeof window.clearToolOutput !== 'undefined') clearToolOutput();"
            )
        except Exception:
            pass

    def tool_output_begin(self, meta: CtxMeta):
        """
        Begin tool output

        :param meta: context meta
        """
        try:
            self.get_output_node(meta).page().runJavaScript(
                f"if (typeof window.beginToolOutput !== 'undefined') beginToolOutput();"
            )
        except Exception:
            pass

    def tool_output_end(self):
        """End tool output"""
        try:
            self.get_output_node().page().runJavaScript(
                f"if (typeof window.endToolOutput !== 'undefined') endToolOutput();"
            )
        except Exception:
            pass

    def sanitize_html(self, html: str) -> str:
        """
        Sanitize HTML to prevent XSS attacks

        :param html: HTML string to sanitize
        :return: sanitized HTML string
        """
        return html
        if not html:
            return ""
        if '&amp;' not in html:
            return html
        return self.RE_AMP_LT_GT.sub(r'&\1;', html)

    def append_debug(
            self,
            ctx: CtxItem,
            pid,
            title: Optional[str] = None
    ) -> str:
        """
        Append debug info

        :param ctx: context item
        :param pid: context PID
        :param title: debug title
        :return: HTML debug info
        """
        if title is None:
            title = "debug"
        return f"<div class='debug'><b>{title}:</b> pid: {pid}, ctx: {ctx.to_dict()}</div>"

    def is_debug(self) -> bool:
        """
        Check if debug mode is enabled

        :return: True if debug mode is enabled
        """
        return self.window.core.config.get("debug.render", False)

    def js_stream_queue_len(self, pid: int):
        """
        Ask the JS side how many items are currently queued for streaming (streamQ.length).

        :param pid: context PID
        """
        node = self.get_output_node_by_pid(pid)
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

    def remove_pid(self, pid: int):
        """
        Remove PID from renderer

        :param pid: context PID
        """
        if pid in self.pids:
            del self.pids[pid]
        # Clean micro-batch resources
        self._stream_reset(pid)
        t = self._stream_timer.pop(pid, None)
        if t:
            try:
                t.stop()
            except Exception:
                pass
        self._stream_acc.pop(pid, None)
        self._stream_header.pop(pid, None)
        self._stream_last_flush.pop(pid, None)

    def on_js_ready(self, pid: int) -> None:
        """
        On JS ready - called from JS side via QWebChannel when bridge is ready.

        :param pid: context PID
        """
        if pid not in self._bridge_ready:
            self._bridge_ready[pid] = False
            self._pending_nodes.setdefault(pid, [])
        self._bridge_ready[pid] = True
        self._drain_pending_nodes(pid)

    def _drain_pending_nodes(self, pid: int):
        """
        Drain any pending nodes queued while bridge was not ready.

        :param pid: context PID
        """
        node = self.get_output_node_by_pid(pid)
        if node is None:
            return
        br = getattr(node.page(), "bridge", None)
        if br is None:
            return
        q = self._pending_nodes.get(pid, [])
        while q:
            replace, payload = q.pop(0)
            try:
                if replace and hasattr(br, "nodeReplace"):
                    self.clear_nodes(pid)
                    br.nodeReplace.emit(payload)
                elif not replace and hasattr(br, "node"):
                    br.node.emit(payload)
            except Exception:
                # If something goes wrong, stop draining to avoid dropping further items.
                break
        # stop/clear fallback timer if any
        t = self._pending_timer.pop(pid, None)
        if t:
            try:
                t.stop()
            except Exception:
                pass

    def _queue_node(self, pid: int, payload: str, replace: bool):
        """
        Queue node payload for later delivery when bridge is ready, with a safe fallback.

        :param pid: context PID
        :param payload: sanitized HTML payload
        :param replace: True if replace current content
        """
        q = self._pending_nodes.setdefault(pid, [])
        q.append((replace, payload))
        if pid not in self._pending_timer:
            t = QTimer(self.window)
            t.setSingleShot(True)
            t.setInterval(1200)  # ms

            def on_timeout(pid=pid):
                # Still not ready? Fallback: flush queued via runJavaScript once.
                node = self.get_output_node_by_pid(pid)
                if node:
                    while self._pending_nodes.get(pid):
                        rep, pl = self._pending_nodes[pid].pop(0)
                        try:
                            if rep:
                                node.page().runJavaScript(
                                    f"if (typeof window.replaceNodes !== 'undefined') "
                                    f"replaceNodes({self.to_json(pl)});"
                                )
                            else:
                                node.page().runJavaScript(
                                    f"if (typeof window.appendNode !== 'undefined') "
                                    f"appendNode({self.to_json(pl)});"
                                )
                        except Exception:
                            pass
                self._pending_timer.pop(pid, None)

            t.timeout.connect(on_timeout)
            self._pending_timer[pid] = t
            t.start()

    # ------------------------- Micro-batching -------------------------

    def _stream_get(self, pid: int) -> tuple[_AppendBuffer, QTimer]:
        """
        Get or create per-PID append buffer and timer for micro-batching.
        Timer is single-shot and (re)started only when there is pending data.

        :param pid: context PID
        :return: (buffer, timer) tuple
        """
        buf = self._stream_acc.get(pid)
        if buf is None:
            buf = Renderer._AppendBuffer()
            self._stream_acc[pid] = buf

        t = self._stream_timer.get(pid)
        if t is None:
            t = QTimer(self.window)
            t.setSingleShot(True)
            t.setInterval(self._stream_interval_ms)

            def on_timeout(pid=pid):
                # Flush pending batch and, if more data arrives later, timer will be restarted by _stream_push()
                self._stream_flush(pid, force=False)

            t.timeout.connect(on_timeout)
            self._stream_timer[pid] = t

        return buf, t

    def _stream_reset(self, pid: Optional[int]):
        """
        Reset micro-batch resources for a PID. Safe to call frequently.

        Clear buffer, stop timer, clear header and last-flush timestamp.

        :param pid: context PID
        """
        if pid is None:
            return
        buf = self._stream_acc.get(pid)
        if buf:
            buf.clear()
        t = self._stream_timer.get(pid)
        if t and t.isActive():
            try:
                t.stop()
            except Exception:
                pass
        self._stream_header[pid] = ""
        self._stream_last_flush[pid] = 0.0

    def _stream_push(self, pid: int, header: str, chunk: str):
        """
        Append chunk to per-PID buffer. Start the micro-batch timer if it's not running.
        If accumulated size crosses thresholds, flush immediately.

        :param pid: context PID
        :param header: header/name for this stream (only used if first chunk)
        :param chunk: chunk of text to append
        """
        if not chunk:
            return

        buf, timer = self._stream_get(pid)
        # Remember last known header for this PID
        if header and not self._stream_header.get(pid):
            self._stream_header[pid] = header

        # Append chunk cheaply
        buf.append(chunk)

        # Emergency backstop: if buffer is getting too large, flush now
        pending_size = getattr(buf, "_size", 0)
        if pending_size >= self._stream_emergency_bytes:
            self._stream_flush(pid, force=True)
            return

        # Size-based early flush for responsiveness
        if pending_size >= self._stream_max_bytes:
            self._stream_flush(pid, force=True)
            return

        # Start timer if not active to flush at ~frame rate
        if not timer.isActive():
            try:
                timer.start()
            except Exception:
                # As a fallback, if timer cannot start, flush synchronously
                self._stream_flush(pid, force=True)

    def _stream_flush(self, pid: int, force: bool = False):
        """
        Flush buffered chunks for a PID via QWebChannel (bridge.chunk.emit(name, chunk)).
        If the bridge is not available, fall back to runJavaScript appendStream(name, chunk).

        If no data is pending, do nothing. Stop the timer if running.

        :param pid: context PID
        :param force: True to force flush ignoring interval
        """
        buf = self._stream_acc.get(pid)
        if buf is None or buf.is_empty():
            # Nothing to send; stop timer if any
            t = self._stream_timer.get(pid)
            if t and t.isActive():
                try:
                    t.stop()
                except Exception:
                    pass
            return

        node = self.get_output_node_by_pid(pid)
        if node is None:
            # Drop buffer if node is gone to avoid leaks
            buf.clear()
            return

        # Stop timer for this flush; next push will re-arm it
        t = self._stream_timer.get(pid)
        if t and t.isActive():
            try:
                t.stop()
            except Exception:
                pass

        # Gather and clear the pending data in one allocation
        data = buf.get_and_clear()
        name = self._stream_header.get(pid, "") or ""

        try:
            br = getattr(node.page(), "bridge", None)
            if br is not None and hasattr(br, "chunk"):
                # Send as raw text; JS runtime handles buffering/rendering
                br.chunk.emit(name, data)
            else:
                # Fallback path if bridge not yet connected on this page
                node.page().runJavaScript(
                    f"if (typeof window.appendStream !== 'undefined') appendStream({self.to_json(name)},{self.to_json(data)});"
                )
        except Exception:
            # If something goes wrong, attempt a JS fallback once
            try:
                node.page().runJavaScript(
                    f"if (typeof window.appendStream !== 'undefined') appendStream({self.to_json(name)},{self.to_json(data)});"
                )
            except Exception:
                pass

        # Opportunistic memory release on Linux for very large flushes
        try:
            if len(data) >= (256 * 1024):
                self.auto_cleanup_soft()
        except Exception:
            pass

        # Explicitly drop reference to large string so GC/malloc_trim can reclaim sooner
        del data

        self._stream_last_flush[pid] = monotonic()

    def eval_js(self, script: str):
        """
        Evaluate arbitrary JS in the output node context.

        :param script: JS code to run
        """
        current = self.window.core.ctx.get_current()
        meta = self.window.core.ctx.get_meta_by_id(current)
        node = self.get_output_node(meta)
        if node is None:
            return
        def callback(val):
            self.window.core.debug.console.log(f"[JS] {val}")
            print(f"[JS] {val}")
        try:
            node.page().runJavaScript(script, callback)
        except Exception:
            pass