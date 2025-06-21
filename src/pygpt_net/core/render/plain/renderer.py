#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt    #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.21 16:00:00                  #
# ================================================== #

from datetime import datetime
from typing import Optional, List

from PySide6.QtGui import QTextCursor, QTextBlockFormat

from pygpt_net.core.render.base import BaseRenderer
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.ui.widget.textarea.output import ChatOutput
from pygpt_net.item.ctx import CtxItem, CtxMeta

from .body import Body
from .helpers import Helpers
from .pid import PidData


class Renderer(BaseRenderer):
    def __init__(self, window=None):
        super(Renderer, self).__init__(window)
        """
        Plain text renderer

        :param window: Window instance
        """
        self.window = window
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
        self.to_end(meta)

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
        self.to_end(meta)

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
        for item in items:
            item.idx = i
            self.append_context_item(meta, item)
            i += 1

    def append_input(
            self,
            meta: CtxMeta,
            item: CtxItem,
            flush: bool = True,
            append: bool = False
    ):
        """
        Append text input to output

        :param meta: context meta
        :param item: context item
        :param flush: True if flush
        :param append: True to force append node
        """
        if item.input is None or item.input == "":
            return
        if self.is_timestamp_enabled() and item.input_timestamp is not None:
            name = ""
            if item.input_name is not None and item.input_name != "":
                name = item.input_name + " "
            ts = datetime.fromtimestamp(item.input_timestamp)
            hour = ts.strftime("%H:%M:%S")
            text = '{}{} > {}'.format(name, hour, item.input)
        else:
            text = "> {}".format(item.input)
        self.append_raw(meta, item, text.strip())
        self.to_end(meta)

    def append_output(
            self,
            meta: CtxMeta,
            item: CtxItem
    ):
        """
        Append text output to output

        :param meta: context meta
        :param item: context item
        """
        if item.output is None or item.output == "":
            return
        if self.is_timestamp_enabled() and item.output_timestamp is not None:
            name = ""
            if item.output_name is not None and item.output_name != "":
                name = item.output_name + " "
            ts = datetime.fromtimestamp(item.output_timestamp)
            hour = ts.strftime("%H:%M:%S")
            text = '{}{} {}'.format(name, hour, item.output)
        else:
            text = "{}".format(item.output)
        self.append_raw(meta, item, text.strip())
        self.to_end(meta)

    def append_extra(
            self,
            meta: CtxMeta,
            item: CtxItem,
            footer: bool = False
    ):
        """
        Append extra data (images, files, etc.) to output

        :param meta: context meta
        :param item: context item
        :param footer: True if it is a footer
        """
        appended = []
        pid = self.get_or_create_pid(meta)

        # images
        c = len(item.images)
        if c > 0:
            n = 1
            for image in item.images:
                if image in appended or image in self.pids[pid].images_appended:
                    continue
                try:
                    appended.append(image)
                    self.append_raw(meta, item, self.body.get_image_html(image, n, c))
                    self.pids[pid].images_appended.append(image)
                    n += 1
                except Exception as e:
                    pass

        # files and attachments, TODO check attachments
        c = len(item.files)
        if c > 0:
            n = 1
            for file in item.files:
                if file in appended:
                    continue
                try:
                    appended.append(file)
                    self.append_raw(meta, item, self.body.get_file_html(file, n, c))
                    n += 1
                except Exception as e:
                    pass

        # urls
        c = len(item.urls)
        if c > 0:
            urls_str = []
            n = 1
            for url in item.urls:
                if url in appended or url in self.pids[pid].urls_appended:
                    continue
                try:
                    appended.append(url)
                    urls_str.append(self.body.get_url_html(url, n, c))
                    self.pids[pid].urls_appended.append(url)
                    n += 1
                except Exception as e:
                    pass
            if urls_str:
                self.append_raw(meta, item, "\n" + "\n".join(urls_str))

        if self.window.core.config.get('ctx.sources'):
            if item.doc_ids is not None and len(item.doc_ids) > 0:
                try:
                    docs = self.body.get_docs_html(item.doc_ids)
                    self.append_raw(meta, item, docs)
                    self.to_end(meta)
                except Exception as e:
                    pass

        # jump to end
        if len(appended) > 0:
            self.to_end(meta)

    def append_chunk(
            self,
            meta: CtxMeta,
            item: CtxItem,
            text_chunk: str,
            begin: bool = False
    ):
        """
        Append output chunk to output

        :param meta: context meta
        :param item: context item
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

            if self.is_timestamp_enabled() and item.output_timestamp is not None:
                name = ""
                if item.output_name is not None and item.output_name != "":
                    name = item.output_name + " "
                ts = datetime.fromtimestamp(item.output_timestamp)
                hour = ts.strftime("%H:%M:%S")
                text_chunk = "{}{}: ".format(name, hour) + text_chunk

            text_chunk = "\n" + text_chunk
            self.append_block(meta)
            self.append_chunk_start(meta, item)

        self.pids[pid].buffer += raw_chunk
        self.append(meta, item, self.helpers.format_chunk(text_chunk), "")

    def append_block(
            self,
            meta: CtxMeta
    ):
        """
        Append block to output

        :param meta: context meta
        """
        node = self.get_output_node(meta)
        cursor = node.textCursor()
        cursor.movePosition(QTextCursor.End)
        block_format = QTextBlockFormat()
        block_format.setIndent(0)
        cursor.insertBlock(block_format)
        node.setTextCursor(cursor)

    def append_raw(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text: str
    ):
        """
        Append and format raw text to output as plain text.
        
        :param meta: context meta
        :param ctx: context item
        :param text: text to append
        """
        node = self.get_output_node(meta)
        prev_text = node.toPlainText()
        if prev_text != "":
            prev_text += "\n\n"
        new_text = prev_text + text.strip()
        node.setPlainText(new_text)
        cur = node.textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)

    def append_chunk_start(self, meta: CtxMeta, ctx: CtxItem):
        """
        Append start of chunk to output
        
        :param meta: context meta
        :param ctx: context item
        """
        node = self.get_output_node(meta)
        cursor = node.textCursor()
        cursor.movePosition(QTextCursor.End)
        node.setTextCursor(cursor)

    def append_context_item(
            self,
            meta: CtxMeta,
            item: CtxItem
    ):
        """
        Append context item to output
        
        :param meta: context meta
        :param item: context item
        """
        self.append_input(meta, item)
        self.append_output(meta, item)
        self.append_extra(meta, item)

    def append(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text: str,
            end: str = "\n"
    ):
        """
        Append text to output.

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
            cur.insertText(head)
            if sep:
                cur.insertText("\n")
        node.setTextCursor(cur)

    def append_timestamp(
            self,
            item: CtxItem,
            text: str
    ) -> str:
        """
        Append timestamp to text
        
        :param item: context item
        :param text: input text
        :return: Text with timestamp (if enabled)
        """
        if item is not None \
                and self.is_timestamp_enabled() \
                and item.input_timestamp is not None:
            ts = datetime.fromtimestamp(item.input_timestamp)
            hour = ts.strftime("%H:%M:%S")
            text = '{}: {}'.format(hour, text)
        return text

    def reset(self, meta: Optional[CtxMeta] = None):
        """
        Reset

        :param meta: context meta
        """
        pid = self.get_or_create_pid(meta)
        if pid is not None:
            self.pids[pid].images_appended = []
            self.pids[pid].urls_appended = []

    def reload(self):
        """Reload output, called externally only on theme change to redraw content"""
        self.window.controller.ctx.refresh_output()  # if clear all and appends all items again

    def clear_output(self, meta: Optional[CtxMeta] = None):
        """
        Clear output

        :param meta: context meta
        """
        self.reset()
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

    def get_output_node(
            self,
            meta: Optional[CtxMeta] = None
    ) -> ChatOutput:
        """
        Get output node for current context.
        
        :param meta: context meta
        :return: output node
        """
        node = self.window.core.ctx.output.get_current_plain(meta)
        node.setAcceptRichText(False)
        return node

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
        return self.window.core.ctx.output.get_all_plain()

    def clear_all(self):
        """Clear all"""
        for node in self.get_all_nodes():
            node.clear()
            node.document().setDefaultStyleSheet("")
            node.setStyleSheet("")
            node.document().setMarkdown("")
            node.document().setHtml("")
            node.setPlainText("")