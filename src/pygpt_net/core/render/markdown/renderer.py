#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

import re
from datetime import datetime
from typing import Optional, List

from PySide6.QtGui import QTextCursor, QTextBlockFormat, QTextCharFormat

from pygpt_net.core.render.base import BaseRenderer
from pygpt_net.item.ctx import CtxItem, CtxMeta
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.ui.widget.textarea.output import ChatOutput

from .body import Body
from .helpers import Helpers
from .parser import Parser
from .pid import PidData


class Renderer(BaseRenderer):
    def __init__(self, window=None):
        super(Renderer, self).__init__(window)
        """
        Markdown renderer

        :param window: Window instance
        """
        self.window = window
        self.parser = Parser(window)
        self.body = Body(window)
        self.helpers = Helpers(window)
        self.pids = {}  # per node data

    def prepare(self):
        """
        Prepare renderer
        """
        self.pids = {}

    def get_pid(self, meta: CtxMeta):
        """
        Get PID for context meta
        
        :param meta: context PID
        """
        if self.tab is not None:
            return self.tab.pid  # get PID from tab if exists
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

    def pid_create(self, pid, meta: CtxMeta):
        """
        Create PID data
        
        :param pid: PID
        :param meta: context meta
        """
        if pid is not None:
            self.pids[pid] = PidData(pid, meta)

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
        self.parser.reset()

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
        if stream:
            self.reload()  # reload ctx items only if stream

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
        self.to_end(meta)

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
        pass  # do nothing

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
        pass  # do nothing

    def append_context(
            self,
            meta: CtxMeta,
            items: List[CtxItem],
            clear: bool = True
    ):
        """
        Append all context to output
        
        :param meta: context meta
        :param items: context items
        :param clear: True if clear all output before append
        """
        if clear:
            self.clear_output(meta)

        i = 0
        for ctx in items:
            ctx.idx = i
            if i == 0:
                ctx.first = True
            self.append_context_item(meta, ctx)
            i += 1

    def append_input(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            flush: bool = True,
            append: bool = False
    ):
        """
        Append text input to output
        
        :param meta: context meta
        :param ctx: context item
        :param flush: True if flush
        :param append: True to force append node
        """
        if ctx.input is None or ctx.input == "":
            return

        if self.is_timestamp_enabled() \
                and ctx.input_timestamp is not None:
            name = ""
            if ctx.input_name is not None \
                    and ctx.input_name != "":
                name = ctx.input_name + " "
            text = '{} > {}'.format(name, ctx.input)
        else:
            text = "> {}".format(ctx.input)

        # check if it is a command response
        is_cmd = False
        if ctx.input.strip().startswith("[") \
                and ctx.input.strip().endswith("]"):
            is_cmd = True

        # hidden internal call
        if ctx.internal \
                and not is_cmd \
                and not ctx.first \
                and not ctx.input.strip().startswith("user: "):
            self.append_raw(meta, ctx, '>>>', "msg-user")
            return
        else:
            # don't show user prefix if provided in internal call goal update
            if ctx.internal and ctx.input.startswith("user: "):
                text = re.sub(r'^user: ', '> ', ctx.input)

        self.append_raw(meta, ctx, text.strip(), "msg-user")

    def append_output(
            self,
            meta: CtxMeta,
            ctx: CtxItem
    ):
        """
        Append text output to output
        
        :param meta: context meta
        :param ctx: context item
        """
        if ctx.output is None or ctx.output == "":
            return

        if self.is_timestamp_enabled() \
                and ctx.output_timestamp is not None:
            name = ""
            if ctx.output_name is not None \
                    and ctx.output_name != "":
                name = ctx.output_name + " "
            text = '{} {}'.format(name, ctx.output)
        else:
            text = "{}".format(ctx.output)
        self.append_raw(meta, ctx, text.strip(), "msg-bot")

    def append_extra(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            footer: bool = False
    ):
        """
        Append extra data (images, files, etc.) to output
        
        :param meta: context meta
        :param ctx: context item
        :param footer: True if it is a footer
        """
        pid = self.get_or_create_pid(meta)
        node = self.get_output_node(meta)
        appended = []

        # images
        c = len(ctx.images)
        if c > 0:
            n = 1
            for image in ctx.images:
                # don't append if it is an external url
                if image.startswith("http"):
                    continue
                if image in appended or image in self.pids[pid].images_appended:
                    continue
                try:
                    appended.append(image)
                    node.append(self.body.get_image_html(image, n, c))
                    self.pids[pid].images_appended.append(image)
                    n += 1
                except Exception as e:
                    pass

        # files and attachments, TODO check attachments
        c = len(ctx.files)
        if c > 0:
            n = 1
            for file in ctx.files:
                if file in appended:
                    continue
                try:
                    appended.append(file)
                    node.append(self.body.get_file_html(file, n, c))
                    n += 1
                except Exception as e:
                    pass

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
                node.append("<br/>" + "<br/>".join(urls_html))

        # extra action icons
        if footer:
            show_edit = self.window.core.config.get('ctx.edit_icons')
            icons_html = " ".join(self.body.get_action_icons(ctx, all=show_edit))
            if icons_html != "":
                extra = "<div class=\"action-icons\">{}</div>".format(icons_html)
                if ctx.output is not None and ctx.output.endswith("```"):
                    extra = " \n&nbsp;" + extra + "<div></div>"
                node.append(extra)
                self.to_end(meta)

        # docs json
        if self.window.core.config.get('ctx.sources'):
            if ctx.doc_ids is not None and len(ctx.doc_ids) > 0:
                try:
                    docs = self.body.get_docs_html(ctx.doc_ids)
                    node.append(docs)
                    self.to_end(meta)
                except Exception as e:
                    pass

        # jump to end
        if len(appended) > 0:
            self.to_end(meta)

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
        :param ctx: context ctx
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        if text_chunk is None or text_chunk == "":
            return

        pid = self.get_or_create_pid(meta)
        raw_chunk = str(text_chunk)

        if begin:
            self.pids[pid].buffer = ""  # reset buffer
            self.pids[pid].is_cmd = False  # reset command flag

            # store cursor position
            cursor = self.get_output_node(meta).textCursor()
            self.pids[pid].prev_position = cursor.position()

            if self.is_timestamp_enabled() \
                    and ctx.output_timestamp is not None:
                name = ""
                if ctx.output_name is not None \
                        and ctx.output_name != "":
                    name = ctx.output_name + " "
                ts = datetime.fromtimestamp(ctx.output_timestamp)
                hour = ts.strftime("%H:%M:%S")
                text_chunk = "{}{}: ".format(name, hour) + text_chunk

            self.append_block(meta)
            self.append_chunk_start(meta, ctx)

        self.pids[pid].buffer += raw_chunk
        to_append = self.pids[pid].buffer
        if re.search(r'```(?!.*```)', self.pids[pid].buffer):
            to_append += "\n```"  # fix for code block without closing ```
        html = self.parser.parse(to_append)
        self.append_html_chunk(meta, ctx, self.helpers.format_chunk(html))

    def append_block(self, meta: CtxMeta):
        """
        Append block to output
        
        :param meta: context meta
        """
        node = self.get_output_node(meta)
        cursor = node.textCursor()
        cursor.movePosition(QTextCursor.End)
        default_format = QTextCharFormat()  # reset format
        cursor.setCharFormat(default_format)
        block_format = QTextBlockFormat()
        block_format.setIndent(0)
        cursor.insertBlock(block_format)
        node.setTextCursor(cursor)

    def append_html_chunk(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            html: str
    ):
        """
        Append HTML chunk to output
        
        :param meta: context meta
        :param ctx: CtxItem instance
        :param html: HTML chunk
        """
        # remove from cursor position to end
        pid = self.get_or_create_pid(meta)
        node = self.get_output_node(meta)
        
        if self.pids[pid].prev_position is not None:
            cursor = node.textCursor()
            cursor.setPosition(self.pids[pid].prev_position)
            cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            node.setTextCursor(cursor)

        cursor = node.textCursor()
        cursor.movePosition(QTextCursor.End)
        node.setTextCursor(cursor)
        node.append(html.replace("\n", "<br>"))

    def append_raw(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text: str,
            type: str = "msg-bot"
    ):
        """
        Append and format raw text to output
        
        :param meta: context meta
        :param ctx: CtxItem instance
        :param text: text to append
        :param type: type of message
        """
        if type != "msg-user":  # markdown for bot messages
            text = self.helpers.pre_format_text(text)
            text = self.append_timestamp(ctx, text)
            text = self.parser.parse(text)
        else:
            content = self.append_timestamp(ctx, self.helpers.format_user_text(text), type=type)
            text = "<div><p>" + content + "</p></div>"

        text = self.helpers.post_format_text(text)
        if text.startswith("<div class"):
            text = " " + text.strip()
        text = '<div class="{}">'.format(type) + text + "</div>"

        self.get_output_node(meta).append(text)
        self.to_end(meta)

    def append_chunk_start(
            self,
            meta: CtxMeta,
            ctx: CtxItem
    ):
        """
        Append start of chunk to output
        
        :param meta: context meta
        :param ctx: CtxItem instance
        """
        node = self.get_output_node(meta)
        cursor = node.textCursor()
        cursor.movePosition(QTextCursor.End)
        node.setTextCursor(cursor)

    def append_context_item(
            self,
            meta: CtxMeta,
            ctx: CtxItem
    ):
        """
        Append context item to output
    
        :param meta: context meta
        :param ctx: context item
        """
        self.append_input(meta, ctx)
        self.append_output(meta, ctx)
        self.append_extra(meta, ctx, footer=True)

    def append(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text: str,
            end: str = "\n"
    ):
        """
        Append text to output
        
        :param meta: context meta
        :param ctx: context item
        :param text: text to append
        :param end: end of the line character
        """
        node = self.get_output_node(meta)
        cur = node.textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)
        s = str(text) + end
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertHtml("<br>")
        node.setTextCursor(cur)  # Update visible cursor

    def append_timestamp(
            self,
            ctx: CtxItem,
            text: str,
            type: Optional[str] = None
    ) -> str:
        """
        Append timestamp to text
        
        :param ctx: context item
        :param text: Input text
        :param type: Type of message
        :return: Text with timestamp (if enabled)
        """
        if ctx is not None \
                and self.is_timestamp_enabled() \
                and ctx.input_timestamp is not None:
            if type == "msg-user":
                timestamp = ctx.input_timestamp
            else:
                timestamp = ctx.output_timestamp
            if timestamp is not None:
                ts = datetime.fromtimestamp(timestamp)
                hour = ts.strftime("%H:%M:%S")
                text = '<span class="ts">{}:</span> {}'.format(hour, text)
        return text

    def reset(
            self,
            meta: Optional[CtxMeta] = None
    ):
        """
        Reset

        :param meta: context meta
        """
        pid = self.get_or_create_pid(meta)
        if pid is not None:
            self.pids[pid].images_appended = []
            self.pids[pid].urls_appended = []

    def reload(self):
        """
        Reload output, called externally only on theme change to redraw content
        """
        self.window.controller.ctx.refresh_output()  # if clear all and appends all items again

    def clear_output(
            self,
            meta: Optional[CtxMeta] = None
    ):
        """
        Clear output

        :param meta: context meta
        """
        self.reset(meta)
        self.get_output_node(meta).clear()

    def clear_input(self):
        """Clear input"""
        self.get_input_node().clear()

    def to_end(self, meta: CtxMeta):
        """
        Move cursor to end of output
    
        :param meta: context meta
        """
        node = self.get_output_node(meta)
        cursor = node.textCursor()
        cursor.movePosition(QTextCursor.End)
        node.setTextCursor(cursor)

    def is_timestamp_enabled(self) -> bool:
        """
        Check if timestamp is enabled

        :return: True if timestamp is enabled
        """
        return self.window.core.config.get('output_timestamp')

    def get_output_node(self, meta: CtxMeta) -> ChatOutput:
        """
        Get output node
        
        :param meta: context meta
        :return: output node
        """
        return self.window.core.ctx.output.get_current(meta)

    def get_input_node(self) -> ChatInput:
        """
        Get input node

        :return: input node
        """
        return self.window.ui.nodes['input']

    def get_all_nodes(self) -> list:
        """
        Return all registered nodes

        :return: list of ChatOutput nodes (tabs)
        """
        return self.window.core.ctx.output.get_all()

    def clear_all(self):
        """Clear all"""
        for node in self.get_all_nodes():
            node.clear()
            node.document().setDefaultStyleSheet("")
            node.setStyleSheet("")
            node.document().setMarkdown("")
            node.document().setHtml("")
            node.setPlainText("")

    def on_theme_change(self):
        """On theme change"""
        stylesheet = self.window.controller.theme.markdown.css['markdown']
        for node in self.get_all_nodes():
            # self.window.ui.nodes['output_plain'].setStyleSheet(stylesheet)
            node.setStyleSheet(stylesheet)
            node.document().setDefaultStyleSheet(stylesheet)
            node.document().setMarkdown(self.window.ui.nodes['output'].document().toMarkdown())
            self.window.controller.ctx.refresh()
