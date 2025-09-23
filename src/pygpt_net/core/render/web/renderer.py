#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.17 05:00:00                  #
# ================================================== #

import json
import os
import re
import html as _html
from dataclasses import dataclass, field

from datetime import datetime
from typing import Optional, List, Any, Dict, Tuple
from time import monotonic
from io import StringIO

from PySide6.QtCore import QTimer, QUrl, QCoreApplication, QEventLoop, QEvent
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


@dataclass(slots=True)
class RenderBlock:
    """
    JSON payload for node rendering in JS templates.

    Keep only raw data here. HTML is avoided except where there is
    no easy way to keep raw (e.g. plugin-provided tool extras), which are
    carried under extra.tool_extra_html.
    """
    id: int
    meta_id: Optional[int] = None
    input: Optional[dict] = None
    output: Optional[dict] = None
    files: dict = field(default_factory=dict)
    images: dict = field(default_factory=dict)
    urls: dict = field(default_factory=dict)
    tools: dict = field(default_factory=dict)
    tools_outputs: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "meta_id": self.meta_id,
            "input": self.input,
            "output": self.output,
            "files": self.files,
            "images": self.images,
            "urls": self.urls,
            "tools": self.tools,
            "tools_outputs": self.tools_outputs,
            "extra": self.extra,
        }

    def to_json(self, wrap: bool = True) -> str:
        """
        Convert node to JSON string.

        :param wrap: wrap into {"node": {...}} (single appendNode case)
        """
        data = self.to_dict()
        if wrap:
            return json.dumps({"node": data}, ensure_ascii=False, separators=(',', ':'))
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    def debug(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


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

        self._stream_interval_ms: int = _cfg('render.stream.interval_ms', 30)
        self._stream_max_bytes: int = _cfg('render.stream.max_bytes', 8 * 1024)
        self._stream_emergency_bytes: int = _cfg('render.stream.emergency_bytes', 512 * 1024)

        # Per-PID streaming state
        self._stream_acc: dict[int, Renderer._AppendBuffer] = {}
        self._stream_timer: dict[int, QTimer] = {}
        self._stream_header: dict[int, str] = {}
        self._stream_last_flush: dict[int, float] = {}
        self._stream_last_cleanup: float = 0.0

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

        :param state: new state
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
                    except Exception:
                        pass

        elif state == RenderEvent.STATE_IDLE:
            for pid in self.pids:
                node = self.get_output_node_by_pid(pid)
                if node is not None:
                    try:
                        node.page().runJavaScript(
                            "if (typeof window.hideLoading !== 'undefined') hideLoading();"
                        )
                    except Exception:
                        pass

        elif state == RenderEvent.STATE_ERROR:
            for pid in self.pids:
                node = self.get_output_node_by_pid(pid)
                if node is not None:
                    try:
                        node.page().runJavaScript(
                            "if (typeof window.hideLoading !== 'undefined') hideLoading();"
                        )
                    except Exception:
                        pass

    def begin(self, meta: CtxMeta, ctx: CtxItem, stream: bool = False):
        """
        Render begin

        :param meta: context meta
        :param ctx: context item
        :param stream: True if streaming mode
        """
        pid = self.get_or_create_pid(meta)
        self.init(pid)
        self.reset_names(meta)
        self.tool_output_end()
        self.prev_chunk_replace = False

    def end(self, meta: CtxMeta, ctx: CtxItem, stream: bool = False):
        """
        Render end

        :param meta: context meta
        :param ctx: context item
        :param stream: True if streaming mode
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
        self.auto_cleanup(meta)

    def end_extra(self, meta: CtxMeta, ctx: CtxItem, stream: bool = False):
        """
        Render end extra

        :param meta: context meta
        :param ctx: context item
        :param stream: True if streaming mode
        """
        self.to_end(ctx)

    def stream_begin(self, meta: CtxMeta, ctx: CtxItem):
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

        try:
            self.pids[pid].header = self.get_name_header(ctx, stream=True)
        except Exception:
            self.pids[pid].header = ""
        self.update_names(meta, ctx)

    def stream_end(self, meta: CtxMeta, ctx: CtxItem):
        """
        Render stream end

        :param meta: context meta
        :param ctx: context item
        """
        self.prev_chunk_replace = False
        pid = self.get_or_create_pid(meta)
        if pid is None:
            return

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
        self._stream_reset(pid)
        self.auto_cleanup(meta)

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
        Try to trim memory on Linux

        Soft cleanup, called after each context is done.
        """
        def cleanup():
            malloc_trim_linux()
        try:
            QTimer.singleShot(0, cleanup)
        except Exception:
            pass

    def append_context(self, meta: CtxMeta, items: List[CtxItem], clear: bool = True):
        """
        Append all context items to output

        :param meta: context meta
        :param items: list of context items
        :param clear: clear previous content
        """
        self.tool_output_end()
        self.append_context_all(meta, items, clear=clear)

    def append_context_partial(self, meta: CtxMeta, items: List[CtxItem], clear: bool = True):
        """
        Append context items part-by-part

        Append each item as it comes, useful for non-streaming mode when
        context is built gradually.

        :param meta: context meta
        :param items: list of context items
        :param clear: clear previous content
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

            # ignore hidden
            if item.hidden:
                prev_ctx = item
                continue

            # build single RenderBlock with both input and output (if present)
            input_text = self.prepare_input(meta, item, flush=False, append=False)
            output_text = self.prepare_output(meta, item, flush=False, prev_ctx=prev_ctx, next_ctx=next_item)
            block = self._build_render_block(meta, item, input_text, output_text, prev_ctx=prev_ctx, next_ctx=next_item)
            if block:
                self.append(pid, block.to_json(wrap=True))

            prev_ctx = item

        self.pids[pid].use_buffer = False
        if self.pids[pid].html != "":
            self.append(pid, self.pids[pid].html, flush=True)

    def append_context_all(self, meta: CtxMeta, items: List[CtxItem], clear: bool = True):
        """
        Append whole context at once, using JSON nodes

        :param meta: context meta
        :param items: list of context items
        :param clear: clear previous content
        """
        if len(items) == 0:
            if meta is None:
                return

        pid = self.get_or_create_pid(meta)
        self.init(pid)

        if clear:
            # nodes will be cleared on JS when replace flag is True
            self.reset(meta, clear_nodes=False)

        self.pids[pid].use_buffer = True
        self.pids[pid].html = ""
        prev_ctx = None
        next_ctx = None
        total = len(items)
        nodes: List[dict] = []

        for i, item in enumerate(items):
            self.update_names(meta, item)
            item.idx = i
            if i == 0:
                item.first = True
            next_ctx = items[i + 1] if i + 1 < total else None

            if item.hidden:
                prev_ctx = item
                continue

            input_text = self.prepare_input(meta, item, flush=False, append=False)
            output_text = self.prepare_output(meta, item, flush=False, prev_ctx=prev_ctx, next_ctx=next_ctx)
            block = self._build_render_block(meta, item, input_text, output_text, prev_ctx=prev_ctx, next_ctx=next_ctx)
            if block:
                nodes.append(block.to_dict())

            prev_ctx = item

        if nodes:
            payload = json.dumps({"nodes": nodes}, ensure_ascii=False, separators=(',', ':'))
            self.append(pid, payload, replace=True)

        prev_ctx = None
        next_ctx = None
        self.pids[pid].use_buffer = False
        if self.pids[pid].html != "":
            self.append(pid, self.pids[pid].html, flush=True, replace=True)

    def prepare_input(self, meta: CtxMeta, ctx: CtxItem, flush: bool = True, append: bool = False) -> Optional[str]:
        """
        Prepare text input (raw, no HTML)

        :param meta: context meta
        :param ctx: context item
        :param flush: True if flush input area (legacy)
        :param append: True if append to input area (legacy)
        :return: prepared text or None
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

        return str(text).strip()

    def append_input(self, meta: CtxMeta, ctx: CtxItem, flush: bool = True, append: bool = False):
        """
        Append user input as RenderBlock JSON

        :param meta: context meta
        :param ctx: context item
        :param flush: True if flush input area (legacy)
        :param append: True if append to input area (legacy)
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
                    # legacy streaming input (leave as-is)
                    content = self.prepare_node(meta, ctx, text, self.NODE_INPUT)
                    self.append_chunk_input(meta, ctx, content, begin=False)
                    return
            block = self._build_render_block(meta, ctx, input_text=text, output_text=None)
            if block:
                self.append(pid, block.to_json(wrap=True))

    def prepare_output(self, meta: CtxMeta, ctx: CtxItem, flush: bool = True,
                       prev_ctx: Optional[CtxItem] = None, next_ctx: Optional[CtxItem] = None) -> Optional[str]:
        """
        Prepare text output (raw markdown text)

        :param meta: context meta
        :param ctx: context item
        :param flush: True if flush output area (legacy)
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        :return: prepared text or None
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
        return str(output).strip()

    def append_output(self, meta: CtxMeta, ctx: CtxItem, flush: bool = True,
                      prev_ctx: Optional[CtxItem] = None, next_ctx: Optional[CtxItem] = None):
        """
        Append bot output as RenderBlock JSON

        :param meta: context meta
        :param ctx: context item
        :param flush: True if flush output area (legacy)
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        """
        self.tool_output_end()
        output = self.prepare_output(meta=meta, ctx=ctx, flush=flush, prev_ctx=prev_ctx, next_ctx=next_ctx)
        if output:
            block = self._build_render_block(meta, ctx, input_text=None, output_text=output,
                                             prev_ctx=prev_ctx, next_ctx=next_ctx)
            if block:
                pid = self.get_or_create_pid(meta)
                self.append(pid, block.to_json(wrap=True))

    def append_chunk(self, meta: CtxMeta, ctx: CtxItem, text_chunk: str, begin: bool = False):
        """
        Append streamed Markdown chunk to JS with micro-batching and typed chunk support.

        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk to append
        :param begin: True if begin of stream
        """
        pid = self.get_or_create_pid(meta)
        if pid is None:
            return

        pctx = self.pids[pid]
        pctx.item = ctx

        if begin:
            try:
                self.get_output_node(meta).page().runJavaScript(
                    "if (typeof window.beginStream !== 'undefined') beginStream(true);"
                )
            except Exception:
                pass
            pctx.header = self.get_name_header(ctx, stream=True)
            self._stream_reset(pid)
            self.update_names(meta, ctx)

        if not text_chunk:
            return

        self._stream_push(pid, pctx.header or "", str(text_chunk))

    def next_chunk(self, meta: CtxMeta, ctx: CtxItem):
        """
        Flush current stream and start with new chunks

        :param meta: context meta
        :param ctx: context item
        """
        pid = self.get_or_create_pid(meta)
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
        try:
            self.pids[pid].header = self.get_name_header(ctx, stream=True)
        except Exception:
            self.pids[pid].header = ""

    def append_chunk_input(self, meta: CtxMeta, ctx: CtxItem, text_chunk: str, begin: bool = False):
        """
        Append output chunk to input area (legacy)

        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk to append
        :param begin: True if begin of stream
        """
        if not text_chunk:
            return
        if ctx.hidden:
            return
        try:
            self.get_output_node(meta).page().bridge.nodeInput.emit(
                self.sanitize_html(text_chunk)
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

        try:
            self.get_output_node(meta).page().runJavaScript(
                f"""replaceLive({self.to_json(
                    self.sanitize_html(
                        self.pids[pid].live_buffer
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
        pid = self.get_or_create_pid(meta)
        try:
            self.get_output_node_by_pid(pid).page().runJavaScript(
                "if (typeof window.clearLive !== 'undefined') clearLive();"
            )
        except Exception:
            pass

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

        pid = self.get_or_create_pid(meta)

        # Convert to RenderBlock JSON
        input_text = html if type == self.NODE_INPUT else None
        output_text = html if type == self.NODE_OUTPUT else None
        block = self._build_render_block(meta, ctx, input_text, output_text, prev_ctx=prev_ctx, next_ctx=next_ctx)
        if block:
            self.append(pid, block.to_json(wrap=True))

    def append(self, pid, payload: str, flush: bool = False, replace: bool = False):
        """
        Append payload (HTML legacy or JSON string) to output.

        :param pid: context PID
        :param payload: payload to append
        :param flush: True if flush immediately (legacy HTML path)
        :param replace: True if replace whole output (legacy HTML path)
        """
        if self.pids[pid].loaded and not self.pids[pid].use_buffer:
            self.clear_chunks(pid)
            if payload:
                self.flush_output(pid, payload, replace)
            self.pids[pid].clear()
        else:
            if not flush:
                self.pids[pid].append_html(payload)

    def append_context_item(self, meta: CtxMeta, ctx: CtxItem,
                            prev_ctx: Optional[CtxItem] = None, next_ctx: Optional[CtxItem] = None):
        """
        Append context item as one RenderBlock with input+output (if present)

        :param meta: context meta
        :param ctx: context item
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        """
        input_text = self.prepare_input(meta, ctx, flush=False, append=False)
        output_text = self.prepare_output(meta, ctx, flush=False, prev_ctx=prev_ctx, next_ctx=next_ctx)
        block = self._build_render_block(meta, ctx, input_text, output_text, prev_ctx=prev_ctx, next_ctx=next_ctx)
        if block:
            pid = self.get_or_create_pid(meta)
            self.append(pid, block.to_json(wrap=True))

    def append_extra(self, meta: CtxMeta, ctx: CtxItem, footer: bool = False, render: bool = True) -> str:
        """
        Append extra data (legacy HTML way) – kept for runtime calls that append later.

        :param meta: context meta
        :param ctx: context item
        :param footer: True if append at the end (legacy)
        :param render: True if render to output (legacy)
        :return: rendered HTML
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
                except Exception:
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
                except Exception:
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
                except Exception:
                    pass
            if urls_html:
                html_parts.append("<br/><br/>".join(urls_html))

        if self.window.core.config.get('ctx.sources'):
            if ctx.doc_ids is not None and len(ctx.doc_ids) > 0:
                try:
                    docs = self.body.get_docs_html(ctx.doc_ids)
                    html_parts.append(docs)
                except Exception:
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
                except Exception:
                    pass

        return html

    def append_timestamp(self, ctx: CtxItem, text: str, type: Optional[int] = None) -> str:
        """
        Append timestamp to text (legacy HTML path)

        :param ctx: context item
        :param text: text to append timestamp to
        :param type: NODE_INPUT or NODE_OUTPUT
        :return: text with timestamp
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

    def reset(self, meta: Optional[CtxMeta] = None, clear_nodes: bool = True):
        """
        Reset current output

        :param meta: context meta
        :param clear_nodes: True if clear nodes list
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
        :param clear_nodes: True if clear nodes list
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
        self._stream_reset(pid)

    def clear_input(self):
        """Clear input"""
        self.get_input_node().clear()

    def clear_output(self, meta: Optional[CtxMeta] = None):
        """
        Clear output

        :param meta: context meta
        """
        self.prev_chunk_replace = False
        self.reset(meta)

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
            self.get_output_node_by_pid(pid).page().runJavaScript(
                "if (typeof window.clearInput !== 'undefined') clearInput();"
            )
        except Exception:
            pass

    def clear_chunks_output(self, pid: Optional[int]):
        """
        Clear chunks from output

        :param pid: context PID
        """
        self.prev_chunk_replace = False
        try:
            self.get_output_node_by_pid(pid).page().runJavaScript(
                "if (typeof window.clearOutput !== 'undefined') clearOutput();"
            )
        except Exception:
            pass
        self._stream_reset(pid)

    def clear_nodes(self, pid: Optional[int]):
        """
        Clear nodes list

        :param pid: context PID
        """
        try:
            self.get_output_node_by_pid(pid).page().runJavaScript(
                "if (typeof window.clearNodes !== 'undefined') clearNodes();"
            )
        except Exception:
            pass

    # Legacy methods kept for compatibility with existing code paths
    def prepare_node(self, meta: CtxMeta, ctx: CtxItem, html: str, type: int = 1,
                     prev_ctx: Optional[CtxItem] = None, next_ctx: Optional[CtxItem] = None) -> str:
        """
        Compatibility shim: convert single input/output into markdown/raw for JS templates.

        :param meta: context meta
        :param ctx: context item
        :param html: HTML content
        :param type: NODE_INPUT or NODE_OUTPUT
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        :return: prepared text
        """
        pid = self.get_or_create_pid(meta)
        if type == self.NODE_OUTPUT:
            return str(html)
        elif type == self.NODE_INPUT:
            return str(html)

    def get_name_header(self, ctx: CtxItem, stream: bool = False) -> str:
        """
        Legacy - kept for stream header text (avatar + name string)

        :param ctx: context item
        :param stream: True if streaming mode
        :return: HTML string
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

    def flush_output(self, pid: int, payload: str, replace: bool = False):
        """
        Send content via QWebChannel (JSON or HTML string).

        :param pid: context PID
        :param payload: payload to send
        :param replace: True if replace nodes list
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
                        f"if (typeof window.replaceNodes !== 'undefined') replaceNodes({self.to_json(payload)});"
                    )
                else:
                    node.page().runJavaScript(
                        f"if (typeof window.appendNode !== 'undefined') appendNode({self.to_json(payload)});"
                    )
            except Exception:
                pass

    def reload(self):
        """Reload output, called externally only on theme change to redraw content"""
        self.window.controller.ctx.refresh_output()

    def flush(self, pid: Optional[int]):
        """
        Flush output page HTML (initial)

        :param pid: context PID
        """
        if self.pids[pid].loaded:
            return

        html = self.body.get_html(pid)
        node = self.get_output_node_by_pid(pid)
        if node is not None:
            try:
                node.setHtml(html, baseUrl="file://")
            except Exception as e:
                print("[Renderer] flush error:", e)

    def fresh(self, meta: Optional[CtxMeta] = None, force: bool = False):
        """
        Reset page / unload old renderer from memory

        :param meta: context meta
        :param force: True if force even when not needed
        """
        plain = self.window.core.config.get('render.plain')
        if plain:
            return

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
            node.unload()  # unload web page
            self._stream_reset(pid)
            self.pids[pid].clear(all=True)
            self.pids[pid].loaded = False
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
        tab.unwrap(node)
        self.window.ui.nodes['output'].pop(tab.pid, None)

        try:
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            QCoreApplication.processEvents(QEventLoop.AllEvents, 0)
        except Exception:
            pass

        view = ChatWebOutput(self.window)
        view.set_tab(tab)
        view.set_meta(meta)
        view.signals.save_as.connect(self.window.controller.chat.render.handle_save_as)
        view.signals.audio_read.connect(self.window.controller.chat.render.handle_audio_read)

        layout.addWidget(view)  # tab body layout
        tab.add_ref(view)
        view.setVisible(True)
        self.window.ui.nodes['output'][tab.pid] = view
        self.auto_cleanup_soft(meta)

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

        :param pid: context PID
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
        On edit submit

        :param ctx: context item
        """
        self.remove_items_from(ctx)

    def on_enable_edit(self, live: bool = True):
        """
        On enable edit icons

        :param live: True if live mode
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

        :param live: True if live mode
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

        :param live: True if live mode
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

        :param live: True if live mode
        """
        if not live:
            return
        try:
            nodes = self.get_all_nodes()
            for node in nodes:
                node.page().runJavaScript("if (typeof window.disableTimestamp !== 'undefined') disableTimestamp();")
        except Exception:
            pass

    def update_names(self, meta: CtxMeta, ctx: CtxItem):
        """
        Update names from ctx

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
        """Clear all tabs"""
        for pid in self.pids:
            self.clear_chunks(pid)
            self.clear_nodes(pid)
            self.pids[pid].html = ""
            self._stream_reset(pid)

    def scroll_to_bottom(self):
        """Scroll to bottom placeholder"""
        pass

    def append_block(self):
        """Append block placeholder"""
        pass

    def to_end(self, ctx: CtxItem):
        """Move cursor to end placeholder"""
        pass

    def get_all_nodes(self) -> list:
        """Return all registered nodes"""
        return self.window.core.ctx.output.get_all()

    def reload_css(self):
        """Reload CSS – propagate theme and config to runtime"""
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
                    except Exception:
                        pass
                return

    def on_theme_change(self):
        """On theme change"""
        self.window.controller.theme.markdown.load()
        for pid in self.pids:
            if self.pids[pid].loaded:
                self.reload_css()
                return

    def tool_output_append(self, meta: CtxMeta, content: str):
        """
        Add tool output (append)

        :param meta: context meta
        :param content: content to append
        """
        try:
            self.get_output_node(meta).page().runJavaScript(
                f"""if (typeof window.appendToolOutput !== 'undefined') appendToolOutput({self.to_json(
                    self.sanitize_html(content)
                )});"""
            )
        except Exception:
            pass

    def tool_output_update(self, meta: CtxMeta, content: str):
        """
        Replace tool output

        :param meta: context meta
        :param content: content to set
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
        Sanitize HTM

        :param html: HTML string
        """
        return html
        if not html:
            return ""
        if '&amp;' not in html:
            return html
        return self.RE_AMP_LT_GT.sub(r'&\1;', html)

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

    def is_debug(self) -> bool:
        """
        Check debug flag

        :return: True if debug enabled
        """
        return self.window.core.config.get("debug.render", False)

    def js_stream_queue_len(self, pid: int):
        """
        Ask JS side for stream queue length

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
        Remove PID and clean resources

        :param pid: context PID
        """
        if pid in self.pids:
            del self.pids[pid]
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
        Called by JS via bridge when ready

        :param pid: context PID
        """
        if pid not in self._bridge_ready:
            self._bridge_ready[pid] = False
            self._pending_nodes.setdefault(pid, [])
        self._bridge_ready[pid] = True
        self._drain_pending_nodes(pid)

    def _drain_pending_nodes(self, pid: int):
        """
        Flush queued node payloads

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
                break
        t = self._pending_timer.pop(pid, None)
        if t:
            try:
                t.stop()
            except Exception:
                pass

    def _queue_node(self, pid: int, payload: str, replace: bool):
        """
        Queue node payload until bridge is ready (with safe fallback)

        :param pid: context PID
        :param payload: payload to queue
        :param replace: True if replace nodes list
        """
        q = self._pending_nodes.setdefault(pid, [])
        q.append((replace, payload))
        if pid not in self._pending_timer:
            t = QTimer(self.window)
            t.setSingleShot(True)
            t.setInterval(1200)  # ms

            def on_timeout(pid=pid):
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
        Get/create per-PID append buffer and timer

        :param pid: context PID
        :return: (buffer, timer)
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
                self._stream_flush(pid, force=False)

            t.timeout.connect(on_timeout)
            self._stream_timer[pid] = t

        return buf, t

    def _stream_reset(self, pid: Optional[int]):
        """
        Reset micro-batch state for PID

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
        Push chunk into buffer and schedule flush

        :param pid: context PID
        :param header: optional header (first chunk only)
        :param chunk: chunk to append
        """
        if not chunk:
            return

        buf, timer = self._stream_get(pid)
        if header and not self._stream_header.get(pid):
            self._stream_header[pid] = header

        buf.append(chunk)
        pending_size = getattr(buf, "_size", 0)
        if pending_size >= self._stream_emergency_bytes:
            self._stream_flush(pid, force=True)
            return
        if pending_size >= self._stream_max_bytes:
            self._stream_flush(pid, force=True)
            return
        if not timer.isActive():
            try:
                timer.start()
            except Exception:
                self._stream_flush(pid, force=True)

    def _stream_flush(self, pid: int, force: bool = False):
        """
        Flush buffered chunks via QWebChannel (bridge.chunk.emit(name, chunk, type))

        :param pid: context PID
        :param force: True if force flush ignoring interval
        """
        buf = self._stream_acc.get(pid)
        if buf is None or buf.is_empty():
            t = self._stream_timer.get(pid)
            if t and t.isActive():
                try:
                    t.stop()
                except Exception:
                    pass
            return

        node = self.get_output_node_by_pid(pid)
        if node is None:
            buf.clear()
            return

        t = self._stream_timer.get(pid)
        if t and t.isActive():
            try:
                t.stop()
            except Exception:
                pass

        data = buf.get_and_clear()
        name = self._stream_header.get(pid, "") or ""

        node.page().bridge.chunk.emit(name, data, "text_delta")

        try:
            del data
            # auto GC cleanup after some time
            now = monotonic()
            last = self._stream_last_cleanup
            if now - last > 120.0:
                self.auto_cleanup_soft()
                self._stream_last_cleanup = now
        except Exception:
            pass

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

    # ------------------------- Helpers: build JSON blocks -------------------------

    def _output_identity(self, ctx: CtxItem) -> Tuple[str, Optional[str], bool]:
        """
        Resolve output identity (name, avatar file:// path) based on preset.

        :param ctx: context item
        :return: (name, avatar, personalize)
        """
        meta = ctx.meta
        if meta is None:
            return self.pids[self.get_or_create_pid(meta)].name_bot if meta else "", None, False
        preset_id = meta.preset
        if not preset_id:
            return self.pids[self.get_or_create_pid(meta)].name_bot, None, False
        preset = self.window.core.presets.get(preset_id)
        if preset is None or not preset.ai_personalize:
            return self.pids[self.get_or_create_pid(meta)].name_bot, None, False
        name = preset.ai_name or self.pids[self.get_or_create_pid(meta)].name_bot
        avatar = None
        if preset.ai_avatar:
            presets_dir = self.window.core.config.get_user_dir("presets")
            avatars_dir = os.path.join(presets_dir, "avatars")
            avatar_path = os.path.join(avatars_dir, preset.ai_avatar)
            if os.path.exists(avatar_path):
                avatar = f"{self._file_prefix}{avatar_path}"
        return name, avatar, bool(preset.ai_personalize)

    def _build_render_block(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            input_text: Optional[str],
            output_text: Optional[str],
            prev_ctx: Optional[CtxItem] = None,
            next_ctx: Optional[CtxItem] = None
    ) -> Optional[RenderBlock]:
        """
        Build RenderBlock for given ctx and payloads (input/output).

        - if input_text or output_text is None, that part is skipped.
        - if ctx.hidden is True, returns None.
        - if both input_text and output_text are None, returns None.
        - if meta is None or invalid, returns None.

        :param meta: CtxMeta object
        :param ctx: CtxItem object
        :param input_text: Input text (raw, un-formatted)
        :param prev_ctx: Previous CtxItem (for context, optional)
        :param next_ctx: Next CtxItem (for context, optional)
        :return: RenderBlock object or None
        """
        pid = self.get_or_create_pid(meta)
        if pid is None:
            return

        block = RenderBlock(id=getattr(ctx, "id", None), meta_id=getattr(meta, "id", None))

        # input
        if input_text:
            # Keep raw; formatting is a template duty (escape/BR etc.)
            block.input = {
                "type": "user",
                "name": self.pids[pid].name_user,
                "avatar_img": None,  # no user avatar by default
                "text": str(input_text),
                "timestamp": ctx.input_timestamp if hasattr(ctx, "input_timestamp") else None,
            }

        # output
        if output_text:
            # Pre/post format raw markdown via Helpers to preserve placeholders ([!cmd], think) and workdir tokens.
            md_src = self.helpers.pre_format_text(output_text)
            md_text = self.helpers.post_format_text(md_src)
            name, avatar, personalize = self._output_identity(ctx)

            # tool output visibility (agent step / commands)
            is_cmd = (
                next_ctx is not None and
                next_ctx.internal and
                (len(ctx.cmds) > 0 or (ctx.extra_ctx is not None and len(ctx.extra_ctx) > 0))
            )
            tool_output = ""
            tool_output_visible = False
            if is_cmd:
                if ctx.results is not None and len(ctx.results) > 0 \
                        and isinstance(ctx.extra, dict) and "agent_step" in ctx.extra:
                    tool_output = self.helpers.format_cmd_text(str(ctx.input), indent=True)
                    tool_output_visible = True
                else:
                    tool_output = self.helpers.format_cmd_text(str(next_ctx.input), indent=True)
                    tool_output_visible = True
            elif ctx.results is not None and len(ctx.results) > 0 \
                    and isinstance(ctx.extra, dict) and "agent_step" in ctx.extra:
                tool_output = self.helpers.format_cmd_text(str(ctx.input), indent=True)

            # plugin-driven extra (HTML) – keep as-is to preserve functionality
            tool_extra_html = self.body.prepare_tool_extra(ctx)

            block.output = {
                "type": "bot",
                "name": name or self.pids[pid].name_bot,
                "avatar_img": avatar,
                "text": md_text,
                "timestamp": ctx.output_timestamp if hasattr(ctx, "output_timestamp") else None,
            }

            # extras (images/files/urls/actions)
            images, files, urls, extra_actions = self.body.build_extras_dicts(ctx, pid)
            block.images = images
            block.files = files
            block.urls = urls

            # docs as raw data -> rendered in JS
            docs_norm = []
            if self.window.core.config.get('ctx.sources'):
                if ctx.doc_ids is not None and len(ctx.doc_ids) > 0:
                    docs_norm = self.body.normalize_docs(ctx.doc_ids)

            block.extra.update({
                "tool_output": tool_output,
                "tool_output_visible": tool_output_visible,
                "tool_extra_html": tool_extra_html,
                "docs": docs_norm,
                "footer_icons": True,
                "personalize": personalize,
            })
            block.extra.update(extra_actions)

        # carry ctx.extra flags as-is (do not collide with our own keys)
        if isinstance(ctx.extra, dict):
            block.extra.setdefault("ctx_extra", ctx.extra)

        # debug
        if self.is_debug():
            print(block.debug())
            block.extra["debug_html"] = self.append_debug(ctx, pid, "output")

        return block