#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.12 00:00:00                  #
# ================================================== #

import json
import os
import re
from datetime import datetime
from typing import Optional, List

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

    def prepare(self):
        """
        Prepare renderer
        """
        self.pids = {}

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
        self.pids[pid].loaded = True
        if self.pids[pid].html != "" and not self.pids[pid].use_buffer:
            self.clear_chunks_input(pid)
            self.clear_chunks_output(pid)
            self.clear_nodes(pid)
            self.append(pid, self.pids[pid].html, flush=True)
            self.pids[pid].html = ""

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
        pid = self.get_or_create_pid(meta)
        if self.window.controller.agent.legacy.enabled():
            if self.pids[pid].item is not None:
                self.append_context_item(meta, self.pids[pid].item)
                self.pids[pid].item = None

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

        self.pids[pid].use_buffer = True
        self.pids[pid].html = ""
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
        self.pids[pid].use_buffer = False

        # flush
        if self.pids[pid].html != "":
            self.append(
                pid,
                self.pids[pid].html,
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
        if ctx.output is None or ctx.output == "":
            return
        self.append_node(
            meta=meta,
            ctx=ctx,
            html=ctx.output.strip(),
            type=self.NODE_OUTPUT,
            prev_ctx=prev_ctx,
            next_ctx=next_ctx
        )

    def append_chunk(
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
        pid = self.get_or_create_pid(meta)
        self.pids[pid].item = ctx
        if text_chunk is None or text_chunk == "":
            if begin:
                self.pids[pid].buffer = ""  # always reset buffer
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
            self.pids[pid].buffer = ""  # reset buffer
            self.pids[pid].is_cmd = False  # reset command flag
            self.clear_chunks_output(pid)
        self.pids[pid].buffer += raw_chunk

        """
        # cooldown (throttling) to prevent high CPU usage on huge text chunks
        if len(self.buffer) > self.throttling_min_chars:
            current_time = time.time()
            if current_time - self.last_time_called <= self.cooldown:
                return  # wait a moment
            else:
                self.last_time_called = current_time
        """

        # parse chunks
        to_append = self.pids[pid].buffer
        if has_unclosed_code_tag(self.pids[pid].buffer):
            to_append += "\n```"  # fix for code block without closing ```
        html = self.parser.parse(to_append)
        escaped_chunk = json.dumps(html)
        try:
            self.get_output_node(meta).page().runJavaScript(
                f"replaceOutput('{self.pids[pid].name_bot}', {escaped_chunk});")
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
        if self.pids[pid].loaded and not self.pids[pid].use_buffer:
            self.clear_chunks(pid)
            self.flush_output(pid, html)  # render
            self.pids[pid].html = ""
        else:
            if not flush:
                self.pids[pid].html += html  # to buffer

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

        pid = self.get_pid(meta)
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
                if image in appended or image in self.pids[pid].images_appended:
                    continue
                try:
                    appended.append(image)
                    html += self.body.get_image_html(image, n, c)
                    self.pids[pid].images_appended.append(image)
                    n += 1
                except Exception as e:
                    pass

        # files and attachments, TODO check attachments
        c = len(ctx.files)
        if c > 0:
            files_html = []
            n = 1
            for file in ctx.files:
                if file in appended or file in self.pids[pid].files_appended:
                    continue
                try:
                    appended.append(file)
                    files_html.append(self.body.get_file_html(file, n, c))
                    self.pids[pid].files_appended.append(file)
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
                if url in appended or url in self.pids[pid].urls_appended:
                    continue
                try:
                    appended.append(url)
                    urls_html.append(self.body.get_url_html(url, n, c))
                    self.pids[pid].urls_appended.append(url)
                    n += 1
                except Exception as e:
                    pass
            if urls_html:
                html += "<br/>" + "<br/>".join(urls_html)

        # docs json
        if self.window.core.config.get('ctx.sources'):
            if ctx.doc_ids is not None and len(ctx.doc_ids) > 0:
                try:
                    docs = self.body.get_docs_html(ctx.doc_ids)
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

    def reset_by_pid(self, pid: Optional[int]):
        """
        Reset by PID

        :param pid: context PID
        """
        self.parser.reset()
        self.pids[pid].item = None
        self.pids[pid].html = ""
        self.clear_nodes(pid)
        self.clear_chunks(pid)
        self.pids[pid].images_appended = []
        self.pids[pid].urls_appended = []
        self.pids[pid].files_appended = []
        self.get_output_node_by_pid(pid).reset_current_content()
        self.reset_names_by_pid(pid)

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
        msg_id = "msg-user-" + str(ctx.id) if ctx is not None else ""
        content = self.append_timestamp(
            ctx,
            self.helpers.format_user_text(html),
            type=self.NODE_INPUT
        )
        html = "<p>" + content + "</p>"
        html = self.helpers.post_format_text(html)
        name = self.pids[pid].name_user

        if ctx.internal and ctx.input.startswith("[{"):
            name = trans("msg.name.system")
        if type(ctx.extra) is dict and "agent_evaluate" in ctx.extra:
            name = trans("msg.name.evaluation")

        # debug
        debug = ""
        if self.is_debug():
            debug = self.append_debug(ctx, pid, "input")

        extra = ""
        if ctx.extra is not None and "footer" in ctx.extra:
            extra = ctx.extra["footer"]
        html = (
            '<div class="msg-box msg-user" id="{msg_id}">'
            '<div class="name-header name-user">{name}</div>'
            '<div class="msg">'
            '{html}'
            '<div class="msg-extra">{extra}</div>'
            '{debug}'
            '</div>'
            '</div>'
        ).format(
            msg_id=msg_id,
            name=name,
            html=html,
            extra=extra,
            debug=debug,
        )

        return html

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
        is_cmd = False
        if (
                next_ctx is not None and
                next_ctx.internal and
                (len(ctx.cmds) > 0 or (ctx.extra_ctx is not None and len(ctx.extra_ctx) > 0))
        ):
            is_cmd = True
        pid = self.get_or_create_pid(meta)
        msg_id = "msg-bot-" + str(ctx.id) if ctx is not None else ""
        # if is_cmd:
        # html = self.helpers.format_cmd_text(html)
        html = self.helpers.pre_format_text(html)
        html = self.append_timestamp(ctx, html, type=self.NODE_OUTPUT)
        html = self.parser.parse(html)
        html = self.helpers.post_format_text(html)
        extra = self.append_extra(meta, ctx, footer=True, render=False)
        footer = self.body.prepare_action_icons(ctx)

        # append tool output
        tool_output = ""
        spinner = ""
        icon = os.path.join(
            self.window.core.config.get_app_path(),
            "data", "icons", "expand.svg"
        )
        output_class = "display:none"
        cmd_icon = (
            '<img src="file://{}" width="25" height="25" valign="middle">'
            .format(icon)
        )
        expand_btn = (
            "<span class='toggle-cmd-output' onclick='toggleToolOutput({});' "
            "role='button'>{} {}</span>"
            .format(str(ctx.id), cmd_icon, trans('action.cmd.expand'))
        )

        # check if next ctx is internal and current ctx has commands
        if is_cmd:
            # first, check current input if agent step and results
            if ctx.results is not None and len(ctx.results) > 0 \
                    and isinstance(ctx.extra, dict) and "agent_step" in ctx.extra:
                tool_output = self.helpers.format_cmd_text(str(ctx.input))
                output_class = ""  # show tool output
            else:
                # get output from next input (JSON response)
                tool_output = self.helpers.format_cmd_text(str(next_ctx.input))
                output_class = ""  # show tool output

        # check if agent step and results in current ctx
        elif ctx.results is not None and len(ctx.results) > 0 \
                and isinstance(ctx.extra, dict) and "agent_step" in ctx.extra:
            tool_output = self.helpers.format_cmd_text(str(ctx.input))
        else:
            # loading spinner
            if (
                    next_ctx is None and
                    (
                            ctx.output.startswith("~###~{\"cmd\"") or
                            ctx.output.strip().endswith("}~###~") or
                            len(ctx.cmds) > 0
                    )
            ):
                spinner_class = "display:none"  # hide by default
                if ctx.live:
                    spinner_class = ""  # show spinner only if commands and active run
                icon = os.path.join(
                    self.window.core.config.get_app_path(),
                    "data", "icons", "sync.svg"
                )
                spinner = (
                    '<span class="spinner" style="{}">'
                    '<img src="file://{}" width="30" height="30" '
                    'class="loading"></span>'
                    .format(spinner_class, icon)
                )

        html_tools = (
                spinner +
                '<div class="tool-output" style="{}">'.format(output_class) +
                expand_btn +
                '<div class="content" style="display:none">' +
                tool_output +
                '</div></div>'
        )
        tool_extra = self.body.prepare_tool_extra(ctx)

        # debug
        debug = ""
        if self.is_debug():
            debug = self.append_debug(ctx, pid, "output")

        html = (
            '<div class="msg-box msg-bot" id="{msg_id}">'
            '<div class="name-header name-bot">{name_bot}</div>'
            '<div class="msg">'
            '{html}'
            '<div class="msg-tool-extra">{tool_extra}</div>'
            '{html_tools}'
            '<div class="msg-extra">{extra}</div>'
            '{footer}'
            '{debug}'
            '</div>'
            '</div>'
        ).format(
            msg_id=msg_id,
            name_bot=self.pids[pid].name_bot,
            html=html,
            html_tools=html_tools,
            extra=extra,
            footer=footer,
            tool_extra=tool_extra,
            debug=debug,
        )

        return html

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
            nodes = self.get_all_nodes()
            for node in nodes:
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
            nodes = self.get_all_nodes()
            for node in nodes:
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
            nodes = self.get_all_nodes()
            for node in nodes:
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
            nodes = self.get_all_nodes()
            for node in nodes:
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
        nodes = self.get_all_nodes()
        for pid in self.pids:
            if self.pids[pid].loaded:
                for node in nodes:
                    node.page().runJavaScript("if (typeof window.updateCSS !== 'undefined') updateCSS({});".format(to_json))
                    if self.window.core.config.get('render.blocks'):
                        node.page().runJavaScript("if (typeof window.enableBlocks !== 'undefined') enableBlocks();")
                    else:
                        node.page().runJavaScript("if (typeof window.disableBlocks !== 'undefined') disableBlocks();")  # TODO: ctx!!!!!
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
        debug = "<b>" +title+ ":</b> pid: "+str(pid)+", ctx: " + str(ctx.to_dict())
        return "<div class='debug'>" + debug + "</div>"

    def is_debug(self) -> bool:
        """
        Check if debug mode is enabled

        :return: True if debug mode is enabled
        """
        return self.window.core.config.get("debug.render", False)
