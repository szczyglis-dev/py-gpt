#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.11 00:00:00                  #
# ================================================== #

import html
import json
import os
import re
from datetime import datetime
from typing import Optional, List, Dict

from PySide6.QtCore import QTimer

from pygpt_net.core.render.base import BaseRenderer
from pygpt_net.core.text.utils import has_unclosed_code_tag
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.utils import trans
from pygpt_net.core.tabs.tab import Tab

from .body import Body
from .helpers import Helpers
from .parser import Parser
from .pid import PidData

from pygpt_net.core.events import RenderEvent


class Renderer(BaseRenderer):
    NODE_INPUT = 0
    NODE_OUTPUT = 1

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
        self.pids = {}  # per node data
        self.prev_chunk_replace = False
        self.prev_chunk_newline = False
        self._stream_flush_delay_ms = 12
        self._stream_max_pending_bytes = 8192
        self._stream_immediate_on_newline = True
        self._stream_state: Dict[int, dict] = {}

    def prepare(self):
        """
        Prepare renderer
        """
        self.pids.clear()

    def on_load(self, meta: CtxMeta = None):
        """
        On load (meta) event

        :param meta: context meta
        """
        node = self.get_output_node(meta)
        node.set_meta(meta)
        self.reset(meta)
        self.parser.reset()
        try:
            node.page().runJavaScript(f"if (typeof window.prepare !== 'undefined') prepare();")
        except Exception as e:
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
        if meta is None:
            return
        pid = tab.pid
        if pid is None or pid not in self.pids:
            return
        p = self.pids[pid]
        p.loaded = True
        node = self.get_output_node(meta)

        if p.html != "" and not p.use_buffer:
            self.clear_chunks_input(pid)
            self.clear_chunks_output(pid)
            self.clear_nodes(pid)
            self.append(pid, p.html, flush=True)
            p.html = ""

        node.setUpdatesEnabled(True)

    def get_pid(self, meta: CtxMeta):
        """
        Get PID for context meta
        
        :param meta: context PID
        """
        return self.window.core.ctx.output.get_pid(meta)

    def get_or_create_pid(self, meta: CtxMeta):
        """
        Get PID for context meta and create PID data (if not exists)
        
        :param meta: context PID
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
        # BUSY: current pid only
        if state == RenderEvent.STATE_BUSY:
            if meta:
                pid = self.get_pid(meta)
                if pid is not None:
                    node = self.get_output_node_by_pid(pid)
                    try:
                        node.page().runJavaScript(
                            f"if (typeof window.showLoading !== 'undefined') showLoading();")
                    except Exception as e:
                        pass

        # IDLE: all pids
        elif state == RenderEvent.STATE_IDLE:
            for pid in self.pids.keys():
                node = self.get_output_node_by_pid(pid)
                if node is not None:
                    try:
                        node.page().runJavaScript(
                            f"if (typeof window.hideLoading !== 'undefined') hideLoading();")
                    except Exception as e:
                        pass

        # ERROR: all pids
        elif state == RenderEvent.STATE_ERROR:
            for pid in self.pids.keys():
                node = self.get_output_node_by_pid(pid)
                if node is not None:
                    try:
                        node.page().runJavaScript(
                            f"if (typeof window.hideLoading !== 'undefined') hideLoading();")
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
        self.tool_output_end()  # reset tools
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
        self._stream_state.clear()  # reset stream state
        pid = self.get_or_create_pid(meta)
        if pid is None:
            return
        p = self.pids[pid]
        if p.item is not None and stream:
            self.append_context_item(meta, p.item)
            p.item = None

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
        self.prev_chunk_replace = False
        try:
            self.get_output_node(meta).page().runJavaScript("beginStream();")
        except Exception as e:
            pass

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
        self._stream_state.clear()  # reset stream state
        self.prev_chunk_replace = False
        pid = self.get_or_create_pid(meta)
        if pid is None:
            return

        p = self.pids[pid]
        if self.window.controller.agent.legacy.enabled():
            if p.item is not None:
                self.append_context_item(meta, p.item)
                p.item = None

        p.buffer = ""  # reset buffer
        p.live_buffer = ""  # reset live buffer
        p.html = ""  # reset html buffer

        try:
            self.get_output_node(meta).page().runJavaScript("endStream();")
        except Exception as e:
            pass

    def append_context(
            self,
            meta: CtxMeta,
            items: List[CtxItem],
            clear: bool = True
    ):
        """
        Append all context to output
        
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
        i = 0

        p = self.pids[pid]
        p.use_buffer = True
        p.html = ""
        prev_ctx = None
        for item in items:
            self.update_names(meta, item)
            item.idx = i
            if i == 0:
                item.first = True
            next_item = items[i + 1] if i + 1 < len(items) else None   # append next item if exists
            self.append_context_item(
                meta,
                item,
                prev_ctx=prev_ctx,
                next_ctx=next_item
            )  # to html buffer
            prev_ctx = item
            i += 1
        p.use_buffer = False

        # flush
        if p.html != "":
            self.append(
                pid,
                p.html,
                flush=True
            )  # flush buffer if page loaded, otherwise it will be flushed on page load

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
        self.tool_output_end()  # reset tools
        pid = self.get_or_create_pid(meta)
        if not flush:
            self.clear_chunks_input(pid)

        self.update_names(meta, ctx)
        if ctx.input is None or ctx.input == "":
            return

        text = ctx.input

        # if sub-reply
        if isinstance(ctx.extra, dict) and "sub_reply" in ctx.extra and ctx.extra["sub_reply"]:
            try:
                json_encoded = json.loads(text)
                if isinstance(json_encoded, dict):
                    if "expert_id" in json_encoded and "result" in json_encoded:
                        tmp = "@" + str(ctx.input_name) + ":\n\n" + str(json_encoded["result"])
                        text = tmp
            except json.JSONDecodeError:
                pass

        # hidden internal call
        if ctx.internal \
                and not ctx.first \
                and not ctx.input.strip().startswith("user: ") \
                and not ctx.input.strip().startswith("@"):  # expert says:
            return
        else:
            # don't show user prefix if provided in internal call goal update
            if ctx.internal and ctx.input.startswith("user: "):
                text = re.sub(r'^user: ', '> ', ctx.input)

        if flush:  # to chunk buffer
            if self.is_stream() and not append:
                content = self.prepare_node(meta, ctx, text.strip(), self.NODE_INPUT)
                self.append_chunk_input(meta, ctx, content, False)
                return

        self.append_node(meta, ctx, text.strip(), self.NODE_INPUT)

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
        self.tool_output_end()  # reset tools
        output = ctx.output
        if (isinstance(ctx.extra, dict)
                and "output" in ctx.extra
                and ctx.extra["output"]):
            if self.window.core.config.get("llama.idx.chat.agent.render.all", False):
                output = "__agent_begin__" + ctx.output + "__agent_end__" + ctx.extra["output"]
            else:
                output = ctx.extra["output"]
        else:
            if ctx.output is None or ctx.output == "":
                return
        self.append_node(
            meta=meta,
            ctx=ctx,
            html=output.strip(),
            type=self.NODE_OUTPUT,
            prev_ctx=prev_ctx,
            next_ctx=next_ctx
        )

    def _get_stream_state(self, pid: int):
        """
        Get stream state for PID

        :param pid: context PID
        :return: dict – stream state
        """
        # pid state for micro chunk
        st = self._stream_state.get(pid)
        if st is None:
            st = {
                "pending": [],  # list[str] – uncommitted chunks
                "pending_bytes": 0,  # fast check for flush
                "scheduled": False,  # is flush scheduled?
                "gen": 0,  # count of stream generations (for flush)
                "last_ctx": None,  # last ctx for name_header
                "last_meta": None,  # last meta (to get_output_node)
            }
            self._stream_state[pid] = st
        return st

    def _schedule_flush(
            self,
            pid: int,
            gen: int,
            delay_ms: int
    ):
        """
        Schedule flush for stream output

        :param pid: context PID
        :param gen: generation number (to avoid flush on reset)
        :param delay_ms: delay in milliseconds
        """
        # no leaks, only primitive closures
        def _run():
            # if reset or new generation, don't flush
            st = self._stream_state.get(pid)
            if not st or st["gen"] != gen:
                return
            self._flush_stream(pid)
        QTimer.singleShot(max(0, int(delay_ms)), _run)

    def _flush_stream(self, pid: int):
        """
        Flush stream output

        :param pid: context PID
        """
        st = self._get_stream_state(pid)
        if not st["pending"]:
            st["scheduled"] = False
            return

        p = self.pids[pid]

        # confirm cumulated chunks
        raw_chunk = "".join(st["pending"])
        st["pending"].clear()
        st["pending_bytes"] = 0
        st["scheduled"] = False

        # header+update_names based on last ctx
        ctx = st["last_ctx"] if st["last_ctx"] is not None else p.item
        meta = st["last_meta"]

        name_header = self.get_name_header(ctx)
        self.update_names(meta, ctx)

        # buffer commited only on flush (less copies)
        # begin reset was already called in append_chunk gdy begin=True
        p.append_buffer(raw_chunk)
        buffer = p.buffer

        has_unclosed = has_unclosed_code_tag
        parse_buffer = buffer + "\n```" if has_unclosed(buffer) else buffer
        html = self.parser.parse(parse_buffer)

        code_endings = ("</code></pre></div>", "</code></pre></div><br/>", "</code></pre></div><br>")
        is_code_block = html.endswith(code_endings)

        newline_in_chunk = "\n" in raw_chunk
        is_newline = newline_in_chunk or buffer.endswith("\n") or is_code_block

        force_replace = self.prev_chunk_newline
        self.prev_chunk_newline = newline_in_chunk

        replace_bool = is_newline or force_replace
        if is_code_block and not newline_in_chunk:
            replace_bool = False

        # prepare for DOM
        out_chunk = raw_chunk
        if not is_code_block:
            out_chunk = out_chunk.replace("\n", "<br/>")
        else:
            if self.prev_chunk_replace and not has_unclosed(out_chunk):
                out_chunk = "\n" + out_chunk

        # JSON-escape
        name_header_json = json.dumps(name_header)
        html_json = json.dumps(html)
        chunk_json = json.dumps(out_chunk)

        self.prev_chunk_replace = replace_bool

        replace_js = "true" if replace_bool else "false"
        code_block_js = "true" if is_code_block else "false"

        try:
            self.get_output_node(meta).page().runJavaScript(
                f"appendStream({name_header_json}, {html_json}, {chunk_json}, {replace_js}, {code_block_js});"
            )
        except Exception:
            pass

    def append_chunk(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text_chunk: str,
            begin: bool = False
    ):
        """
        Append output chunk to output (micro-batching + delay)

        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        pid = self.get_or_create_pid(meta)
        p = self.pids[pid]
        p.item = ctx

        # empty chunk
        if not text_chunk:
            if begin:
                p.buffer = ""  # always reset buffer
            return

        st = self._get_stream_state(pid)
        st["last_ctx"] = ctx
        st["last_meta"] = meta

        # on begin, reset generation and pending chunks
        raw_chunk = text_chunk if isinstance(text_chunk, str) else str(text_chunk)
        if begin:
            debug = self.append_debug(ctx, pid, "stream") if self.is_debug() else ""
            if debug:
                raw_chunk = debug + raw_chunk
            p.buffer = ""  # reset buffer
            p.is_cmd = False  # reset command flag
            self.clear_chunks_output(pid)
            self.prev_chunk_replace = False

            # micro-batch reset
            st["pending"].clear()
            st["pending_bytes"] = 0
            st["gen"] += 1
            st["scheduled"] = False

        # accumulation in list (no fragmentation by +=)
        st["pending"].append(raw_chunk)
        st["pending_bytes"] += len(raw_chunk)

        # Flush:
        # - immediate on newline/``` or huge amount of pending bytes
        # - otherwise delay (12 ms)
        immediate = False
        if self._stream_immediate_on_newline and ("\n" in raw_chunk or "```" in raw_chunk):
            immediate = True
        if st["pending_bytes"] >= self._stream_max_pending_bytes:
            immediate = True

        if not st["scheduled"]:
            st["scheduled"] = True
            delay = 0 if immediate else self._stream_flush_delay_ms
            gen_snapshot = st["gen"]
            self._schedule_flush(pid, gen_snapshot, delay)
        else:
            # already planned, flush will be executed later
            pass

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
        p = self.pids[pid]
        p.item = ctx
        p.buffer = ""  # always reset buffer
        self.update_names(meta, ctx)
        self.prev_chunk_replace = False
        self.prev_chunk_newline = False
        try:
            self.get_output_node(meta).page().runJavaScript(
                f"nextStream();")
        except Exception as e:
            pass

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
        if text_chunk is None or text_chunk == "":
            return
        if ctx.hidden:
            return

        pid = self.get_or_create_pid(meta)
        self.clear_chunks_input(pid)
        chunk = self.helpers.format_chunk(text_chunk)
        escaped_chunk = json.dumps(chunk)
        try:
            self.get_output_node(meta).page().runJavaScript(f"appendToInput({escaped_chunk});")
        except Exception as e:
            pass

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
        p = self.pids[pid]
        p.item = ctx
        if text_chunk is None or text_chunk == "":
            if begin:
                p.live_buffer = ""  # always reset buffer
            return
        self.update_names(meta, ctx)
        raw_chunk = str(text_chunk)
        raw_chunk = raw_chunk.replace("<", "&lt;")
        raw_chunk = raw_chunk.replace(">", "&gt;")
        if begin:
            # debug
            debug = ""
            if self.is_debug():
                debug = self.append_debug(ctx, pid, "stream")
            if debug:
                raw_chunk = debug + raw_chunk
            p.live_buffer = ""  # reset buffer
            p.is_cmd = False  # reset command flag
            self.clear_live(meta, ctx)  # clear live output
        p.append_live_buffer(raw_chunk)

        # parse chunks
        to_append = p.live_buffer
        if has_unclosed_code_tag(p.live_buffer):
            to_append += "\n```"  # fix for code block without closing ```
        html = self.parser.parse(to_append)
        escaped_chunk = json.dumps(html)
        try:
            self.get_output_node(meta).page().runJavaScript(
                f"replaceLive({escaped_chunk});")
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
        if not self.pids[pid].loaded:
            js = "var element = document.getElementById('_append_live_'); if (element) { element.innerHTML = ''; }"
        else:
            js = "clearLive();"
        try:
            self.get_output_node_by_pid(pid).page().runJavaScript(js)
        except Exception as e:
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
                next_ctx=next_ctx
            )
        )

    def append(
            self,
            pid,
            html: str,
            flush: bool = False
    ):
        """
        Append text to output
        
        :param pid: ctx pid
        :param html: HTML code
        :param flush: True if flush only
        """
        p = self.pids[pid]
        if p.loaded and not p.use_buffer:
            self.clear_chunks(pid)
            self.flush_output(pid, html)  # render
            p.html = ""
        else:
            if not flush:
                p.append_html(html)  # to buffer

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
            flush=False
        )
        self.append_output(
            meta,
            ctx,
            flush=False,
            prev_ctx=prev_ctx,
            next_ctx=next_ctx
        )  # + extra

    def append_extra(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            footer: bool = False,
            render: bool = True
    ) -> str:
        """
        Append extra data (images, files, etc.) to output
        
        :param meta: context meta
        :param ctx: context item
        :param footer: True if it is a footer
        :param render: True if render, False if only return HTML
        :return: HTML code
        """
        self.tool_output_end()  # reset tools
        body = self.body
        pid = self.get_pid(meta)
        p = self.pids.get(pid)
        appended = []
        html = ""
        # images
        c = len(ctx.images)
        if c > 0:
            n = 1
            for image in ctx.images:
                if image is None:
                    continue
                # don't append if it is an external url
                # if image.startswith("http"):
                    # continue
                if image in appended or image in p.images_appended:
                    continue
                try:
                    appended.append(image)
                    html += body.get_image_html(image, n, c)
                    p.images_appended.append(image)
                    n += 1
                except Exception as e:
                    pass

        # files and attachments, TODO check attachments
        c = len(ctx.files)
        if c > 0:
            files_html = []
            n = 1
            for file in ctx.files:
                if file in appended or file in p.files_appended:
                    continue
                try:
                    appended.append(file)
                    files_html.append(body.get_file_html(file, n, c))
                    p.files_appended.append(file)
                    n += 1
                except Exception as e:
                    pass
            if files_html:
                html += "<br/>" + "<br/>".join(files_html)

        # urls
        c = len(ctx.urls)
        if c > 0:
            urls_html = []
            n = 1
            for url in ctx.urls:
                if url in appended or url in p.urls_appended:
                    continue
                try:
                    appended.append(url)
                    urls_html.append(body.get_url_html(url, n, c))
                    p.urls_appended.append(url)
                    n += 1
                except Exception as e:
                    pass
            if urls_html:
                html += "<br/>" + "<br/>".join(urls_html)

        # docs json
        if self.window.core.config.get('ctx.sources'):
            if ctx.doc_ids is not None and len(ctx.doc_ids) > 0:
                try:
                    docs = body.get_docs_html(ctx.doc_ids)
                    html += docs
                except Exception as e:
                    pass
        # flush
        if render and html != "":
            if footer:
                # append to output
                self.append(pid, html)
            else:
                # append to existing message box using JS
                escaped_html = json.dumps(html)
                self.get_output_node(meta).page().runJavaScript("appendExtra('{}',{});".format(ctx.id, escaped_html))

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
                text = '<span class="ts">{}: </span>{}'.format(hour, text)
        return text

    def reset(
            self,
            meta: Optional[CtxMeta] = None
    ):
        """
        Reset

        :param meta: Context meta
        """
        pid = self.get_pid(meta)
        if pid is not None and pid in self.pids:  # in PIDs only if at least one ctx item is appended
            self.reset_by_pid(pid)
        else:
            # there is no pid here if empty context so check for meta, and clear current
            if meta is not None:
                # create new PID using only meta
                pid = self.get_or_create_pid(meta)
                self.reset_by_pid(pid)

        # clear live output
        self.clear_live(meta, CtxItem())

    def reset_by_pid(self, pid: Optional[int]):
        """
        Reset by PID

        :param pid: context PID
        """
        p = self.pids.get(pid)
        self.parser.reset()
        p.item = None
        p.html = ""
        self.clear_nodes(pid)
        self.clear_chunks(pid)
        p.images_appended.clear()
        p.urls_appended.clear()
        p.files_appended.clear()
        self.get_output_node_by_pid(pid).reset_current_content()
        self.reset_names_by_pid(pid)
        self.prev_chunk_replace = False
        self._stream_state.clear()  # reset stream state

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
        if not self.pids[pid].loaded:
            js = "var element = document.getElementById('_append_input_');"
            js += "if (element) { element.innerHTML = ''; }"
        else:
            js = "clearInput();"
        try:
            self.get_output_node_by_pid(pid).page().runJavaScript(js)
        except Exception as e:
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
        if not self.pids[pid].loaded:
            js = "var element = document.getElementById('_append_output_');"
            js += "if (element) { element.innerHTML = ''; }"
        else:
            js = "clearOutput();"
        try:
            self.get_output_node_by_pid(pid).page().runJavaScript(js)
        except Exception as e:
            pass

    def clear_nodes(
            self,
            pid: Optional[int]
    ):
        """
        Clear nodes from output

        :pid: context PID
        """
        if not self.pids[pid].loaded:
            js = "var element = document.getElementById('_nodes_');"
            js += "if (element) { element.innerHTML = ''; }"
        else:
            js = "clearNodes();"
        try:
            self.get_output_node_by_pid(pid).page().runJavaScript(js)
        except Exception as e:
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
                next_ctx=next_ctx
            )
        elif type == self.NODE_INPUT:
            return self.prepare_node_input(
                pid=pid,
                ctx=ctx,
                html=html,
                prev_ctx=prev_ctx,
                next_ctx=next_ctx
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
        helpers = self.helpers
        format_user_text = helpers.format_user_text
        post_format_text = helpers.post_format_text
        append_timestamp = self.append_timestamp
        append_debug = self.append_debug
        is_debug = self.is_debug
        pids = self.pids
        node_input = self.NODE_INPUT

        msg_id = f"msg-user-{ctx.id}" if ctx is not None else ""

        content = append_timestamp(
            ctx,
            format_user_text(html),
            type=node_input
        )
        html = post_format_text(f"<p>{content}</p>")

        name = pids[pid].name_user
        if ctx.internal and ctx.input.startswith("[{"):
            name = trans("msg.name.system")
        if type(ctx.extra) is dict and "agent_evaluate" in ctx.extra:
            name = trans("msg.name.evaluation")

        debug = append_debug(ctx, pid, "input") if is_debug() else ""

        extra = ""
        extra_style = ""
        if ctx.extra is not None and "footer" in ctx.extra:
            extra = ctx.extra["footer"]
            extra_style = "display:block;"

        return "".join((
            f'<div class="msg-box msg-user" id="{msg_id}">',
            f'<div class="name-header name-user">{name}</div>',
            '<div class="msg">',
            html,
            f'<div class="msg-extra" style="{extra_style}">{extra}</div>',
            debug,
            '</div>',
            '</div>',
        ))

    def prepare_node_output(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            html: str,
            prev_ctx: Optional[CtxItem] = None,
            next_ctx: Optional[CtxItem] = None
    ) -> str:
        """
        Prepare output node

        :param meta: context meta
        :param ctx: CtxItem instance
        :param html: html text
        :param prev_ctx: previous context item
        :param next_ctx: next context item
        :return: prepared HTML
        """
        helpers = self.helpers
        pre_format = helpers.pre_format_text
        post_format = helpers.post_format_text
        format_cmd = helpers.format_cmd_text
        parser = self.parser
        append_timestamp = self.append_timestamp
        append_extra = self.append_extra
        body = self.body
        prepare_action_icons = body.prepare_action_icons
        prepare_tool_extra = body.prepare_tool_extra
        get_name_header = self.get_name_header
        is_debug = self.is_debug
        append_debug = self.append_debug
        get_or_create_pid = self.get_or_create_pid
        node_output = self.NODE_OUTPUT
        trans_expand = trans('action.cmd.expand')

        str_id = str(ctx.id)
        msg_id = f"msg-bot-{ctx.id}" if ctx is not None else ""
        cmds_len = len(ctx.cmds)
        extra_ctx_len = len(ctx.extra_ctx) if ctx.extra_ctx is not None else 0
        is_cmd = (
                next_ctx is not None
                and next_ctx.internal
                and (cmds_len > 0 or extra_ctx_len > 0)
        )

        pid = get_or_create_pid(meta)
        html = pre_format(html)
        html = parser.parse(html)
        html = append_timestamp(ctx, html, type=node_output)
        html = post_format(html)

        extra = append_extra(meta, ctx, footer=True, render=False)
        footer = prepare_action_icons(ctx)

        app_path = self.window.core.config.get_app_path()
        expand_icon_path = os.path.join(app_path, "data", "icons", "expand.svg")
        cmd_icon = (
            f'<img src="file://{expand_icon_path}" width="25" height="25" valign="middle">'
        )
        expand_btn = (
            f"<span class='toggle-cmd-output' onclick='toggleToolOutput({str_id});' "
            f"title='{trans_expand}' role='button'>{cmd_icon}</span>"
        )

        tool_output = ""
        output_class = "display:none"
        agent_step = (
                ctx.results is not None
                and len(ctx.results) > 0
                and isinstance(ctx.extra, dict)
                and "agent_step" in ctx.extra
        )

        if is_cmd:
            if agent_step:
                tool_output = format_cmd(str(ctx.input))
                output_class = ""  # show tool output
            else:
                tool_output = format_cmd(str(next_ctx.input))
                output_class = ""  # show tool output
        elif agent_step:
            tool_output = format_cmd(str(ctx.input))

        html_tools = "".join((
            f'<div class="tool-output" style="{output_class}">',
            expand_btn,
            '<div class="content" style="display:none">',
            tool_output,
            '</div></div>',
        ))

        tool_extra = prepare_tool_extra(ctx)

        debug = append_debug(ctx, pid, "output") if is_debug() else ""
        name_header = get_name_header(ctx)

        return "".join((
            f'<div class="msg-box msg-bot" id="{msg_id}">',
            name_header,
            '<div class="msg">',
            html,
            f'<div class="msg-tool-extra">{tool_extra}</div>',
            html_tools,
            f'<div class="msg-extra">{extra}</div>',
            footer,
            debug,
            '</div>',
            '</div>',
        ))

    def get_name_header(self, ctx: CtxItem) -> str:
        """
        Get name header for the bot

        :param ctx: CtxItem instance
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
                if self.window.core.platforms.is_windows():
                    prefix = 'file:///'
                else:
                    prefix = 'file://'
                avatar_html = f"<img src=\"{prefix}{avatar_path}\" class=\"avatar\"> "

        if not output_name and not avatar_html:
            return ""
        return f"<div class=\"name-header name-bot\">{avatar_html}{output_name}</div>"

    def flush_output(
            self,
            pid: Optional[int],
            html: str
    ):
        """
        Flush output

        :param pid: context PID
        :param html: HTML code
        """
        escaped_html = json.dumps(html)
        try:
            node = self.get_output_node_by_pid(pid)
            node.page().runJavaScript(f"if (typeof window.appendNode !== 'undefined') appendNode({escaped_html});")
            node.update_current_content()
        except Exception as e:
            pass

    def reload(self):
        """Reload output, called externally only on theme change to redraw content"""
        self.window.controller.ctx.refresh_output()  # if clear all and appends all items again

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
            return  # wait for page load

        html = self.body.get_html(pid)
        self.pids[pid].document = html
        self.get_output_node_by_pid(pid).setHtml(html, baseUrl="file://")

    def fresh(
            self,
            meta: Optional[CtxMeta] = None
    ):
        """
        Reset page

        :param meta: context meta
        """
        pid = self.get_or_create_pid(meta)
        if pid is None:
            return
        p = self.pids[pid]
        html = self.body.get_html(pid)
        p.loaded = False
        p.document = html
        node = self.get_output_node_by_pid(pid)
        node.resetPage()
        node.setHtml(html, baseUrl="file://")

    def get_output_node(
            self,
            meta: Optional[CtxMeta] = None
    ):
        """
        Get output node

        :param meta: context meta
        :return: output node
        """
        return self.window.core.ctx.output.get_current(meta)

    def get_output_node_by_pid(
            self,
            pid: Optional[int]
    ):
        """
        Get output node by PID

        :param pid: context pid
        :return: output node
        """
        return self.window.core.ctx.output.get_by_pid(pid)

    def get_input_node(self) -> ChatInput:
        """
        Get input node

        :return: input node
        """
        return self.window.ui.nodes['input']

    def get_document(
            self,
            plain: bool = False
    ):
        """
        Get document content (plain or HTML)

        :param plain: True to convert to plain text
        :return: document content
        """
        pid = self.window.core.ctx.container.get_active_pid()
        if pid is None:
            return ""
        if plain:
            return self.parser.to_plain_text(self.pids[pid].document.replace("<br>", "\n"))
        return self.pids[pid].document

    def remove_item(self, ctx: CtxItem):
        """
        Remove item from output

        :param ctx: context item
        """
        try:
            self.get_output_node(ctx.meta).page().runJavaScript("if (typeof window.removeNode !== 'undefined') removeNode({});".format(ctx.id))
        except Exception as e:
            pass

    def remove_items_from(self, ctx: CtxItem):
        """
        Remove item from output

        :param ctx: context item
        """
        try:
            self.get_output_node(ctx.meta).page().runJavaScript("if (typeof window.removeNodesFromId !== 'undefined') removeNodesFromId({});".format(ctx.id))
        except Exception as e:
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
        # remove all items from ID
        self.remove_items_from(ctx)

    def on_edit_submit(self, ctx: CtxItem):
        """
        On regenerate submit

        :param ctx: context item
        """
        # remove all items from ID
        self.remove_items_from(ctx)

    def on_enable_edit(self, live: bool = True):
        """
        On enable edit icons

        :param live: True if live update
        """
        if not live:
            return
        try:
            for node in self.get_all_nodes():
                node.page().runJavaScript("if (typeof window.enableEditIcons !== 'undefined') enableEditIcons();")
        except Exception as e:
            pass

    def on_disable_edit(self, live: bool = True):
        """
        On disable edit icons

        :param live: True if live update
        """
        if not live:
            return
        try:
            for node in self.get_all_nodes():
                node.page().runJavaScript("if (typeof window.disableEditIcons !== 'undefined') disableEditIcons();")
        except Exception as e:
            pass

    def on_enable_timestamp(self, live: bool = True):
        """
        On enable timestamp

        :param live: True if live update
        """
        if not live:
            return
        try:
            for node in self.get_all_nodes():
                node.page().runJavaScript("if (typeof window.enableTimestamp !== 'undefined') enableTimestamp();")
        except Exception as e:
            pass

    def on_disable_timestamp(self, live: bool = True):
        """
        On disable timestamp

        :param live: True if live update
        """
        if not live:
            return
        try:
            for node in self.get_all_nodes():
                node.page().runJavaScript("if (typeof window.disableTimestamp !== 'undefined') disableTimestamp();")
        except Exception as e:
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
        for pid in self.pids.keys():
            self.clear_chunks(pid)
            self.clear_nodes(pid)
            self.pids[pid].html = ""

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
        to_json = json.dumps(self.body.prepare_styles())
        for pid in self.pids.keys():
            if self.pids[pid].loaded:
                for node in self.get_all_nodes():
                    try:
                        node.page().runJavaScript("if (typeof window.updateCSS !== 'undefined') updateCSS({});".format(to_json))
                        if self.window.core.config.get('render.blocks'):
                            node.page().runJavaScript("if (typeof window.enableBlocks !== 'undefined') enableBlocks();")
                        else:
                            node.page().runJavaScript("if (typeof window.disableBlocks !== 'undefined') disableBlocks();")  # TODO: ctx!!!!!
                    except Exception as e:
                        pass
                return

    def on_theme_change(self):
        """On theme change"""
        self.window.controller.theme.markdown.load()
        for pid in self.pids.keys():
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
        escaped_content = json.dumps(content)
        try:
            self.get_output_node(meta).page().runJavaScript(f"if (typeof window.appendToolOutput !== 'undefined') appendToolOutput({escaped_content});")
        except Exception as e:
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
        escaped_content = json.dumps(content)
        try:
            self.get_output_node(meta).page().runJavaScript(f"if (typeof window.updateToolOutput !== 'undefined') updateToolOutput({escaped_content});")
        except Exception as e:
            pass

    def tool_output_clear(self, meta: CtxMeta):
        """
        Clear tool output

        :param meta: context meta
        """
        try:
            self.get_output_node(meta).page().runJavaScript(f"if (typeof window.clearToolOutput !== 'undefined') clearToolOutput();")
        except Exception as e:
            pass

    def tool_output_begin(self, meta: CtxMeta):
        """
        Begin tool output

        :param meta: context meta
        """
        try:
            self.get_output_node(meta).page().runJavaScript(f"if (typeof window.beginToolOutput !== 'undefined') beginToolOutput();")
        except Exception as e:
            pass

    def tool_output_end(self):
        """End tool output"""
        try:
            self.get_output_node().page().runJavaScript(f"if (typeof window.endToolOutput !== 'undefined') endToolOutput();")
        except Exception as e:
            pass

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
        """
        if title is None:
            title = "debug"
        return f"<div class='debug'><b>{title}:</b> pid: {pid}, ctx: {html.escape(ctx.to_debug())}</div>"

    def is_debug(self) -> bool:
        """
        Check if debug mode is enabled

        :return: True if debug mode is enabled
        """
        return self.window.core.config.get("debug.render", False)

    def remove_pid(self, pid: int):
        """
        Remove PID from renderer
        """
        if pid in self.pids:
            del self.pids[pid]
