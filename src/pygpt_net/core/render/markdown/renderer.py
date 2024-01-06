#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.05 11:00:00                  #
# ================================================== #

import re
from datetime import datetime
from PySide6.QtGui import QTextCursor, QTextBlockFormat
import html

from pygpt_net.item.ctx import CtxItem
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.ui.widget.textarea.output import ChatOutput
from .parser import Parser
from pygpt_net.utils import trans


class Renderer:
    def __init__(self, window=None):
        """
        Markdown renderer

        :param window: Window instance
        """
        self.window = window
        self.parser = Parser(window)
        self.images_appended = []
        self.urls_appended = []
        self.buffer = ""
        self.is_cmd = False

    def begin(self, stream: bool = False):
        """Render begin"""
        pass  # do nothing

    def end(self, stream: bool = False):
        """Render end"""
        if stream:
            self.reload()  # reload ctx items only if stream

    def stream_begin(self):
        """Render stream begin"""
        pass  # do nothing

    def stream_end(self):
        """Render stream end"""
        pass  # do nothing

    def end_extra(self, stream: bool = False):
        """Render end extra"""
        self.to_end()

    def clear_output(self):
        """Clear output"""
        self.reset()
        self.get_output_node().clear()

    def clear_input(self):
        """Clear input"""
        self.get_input_node().clear()

    def reset(self):
        """Reset"""
        self.images_appended = []
        self.urls_appended = []

    def reload(self):
        """Reload output, called externally only on theme change to redraw content"""
        self.window.controller.ctx.refresh_output()  # if clear all and appends all items again

    def append_context(self, items: list, clear: bool = True):
        """
        Append all context to output

        :param items: Context items
        :param clear: True if clear all output before append
        """
        if clear:
            self.clear_output()
        for item in items:
            self.append_context_item(item)

    def append_input(self, item: CtxItem):
        """
        Append text input to output

        :param item: context item
        """
        if item.input is None or item.input == "":
            return
        if self.is_timestamp_enabled() and item.input_timestamp is not None:
            name = ""
            if item.input_name is not None and item.input_name != "":
                name = item.input_name + " "
            text = '{} > {}'.format(name, item.input)
        else:
            text = "> {}".format(item.input)

        # hidden internal call
        if item.internal:
            self.append_raw('-->', "msg-user", item)
            return

        self.append_raw(text.strip(), "msg-user", item)

    def append_output(self, item: CtxItem):
        """
        Append text output to output

        :param item: context item
        """
        if item.output is None or item.output == "":
            return
        if self.is_timestamp_enabled() and item.output_timestamp is not None:
            name = ""
            if item.output_name is not None and item.output_name != "":
                name = item.output_name + " "
            text = '{} {}'.format(name, item.output)
        else:
            text = "{}".format(item.output)
        self.append_raw(text.strip(), "msg-bot", item)

    def append_extra(self, item: CtxItem):
        """
        Append extra data (images, files, etc.) to output

        :param item: context item
        """
        appended = []

        # images
        if len(item.images) > 0:
            for image in item.images:
                if image in appended or image in self.images_appended:
                    continue
                try:
                    appended.append(image)
                    self.get_output_node().append(self.get_image_html(image))
                    self.images_appended.append(image)
                except Exception as e:
                    pass

        # files and attachments, TODO check attachments
        if len(item.files) > 0:
            for file in item.files:
                if file in appended:
                    continue
                try:
                    appended.append(file)
                    self.get_output_node().append(self.get_file_html(file))
                except Exception as e:
                    pass

        # urls
        if len(item.urls) > 0:
            for url in item.urls:
                if url in appended or url in self.urls_appended:
                    continue
                try:
                    appended.append(url)
                    self.get_output_node().append(self.get_url_html(url))
                    self.urls_appended.append(url)
                except Exception as e:
                    pass

        # jump to end
        if len(appended) > 0:
            self.to_end()

    def append_chunk(self, item: CtxItem, text_chunk: str, begin: bool = False):
        """
        Append output chunk to output

        :param item: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        if text_chunk is None or text_chunk == "":
            return

        raw_chunk = str(text_chunk)

        if begin:
            self.buffer = ""  # reset buffer
            self.is_cmd = False  # reset command flag

            if self.is_timestamp_enabled() and item.output_timestamp is not None:
                name = ""
                if item.output_name is not None and item.output_name != "":
                    name = item.output_name + " "
                ts = datetime.fromtimestamp(item.output_timestamp)
                hour = ts.strftime("%H:%M:%S")
                text_chunk = "{}{}: ".format(name, hour) + text_chunk

            self.append_block()
            self.append_chunk_start()

        self.buffer += raw_chunk
        self.append(self.format_chunk(text_chunk), "")

    def append_text(self, text: str):
        """
        Append custom text to input

        :param text: Text to append
        """
        prev_text = self.get_input_node().toPlainText()
        if prev_text != "":
            prev_text += "\n\n"
        new_text = prev_text + text.strip()
        self.get_input_node().setText(new_text)
        cur = self.get_input_node().textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)

    def append_to_input(self, text: str):
        """
        Append text to input

        :param text: text to append
        """
        cur = self.get_input_node().textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)
        s = str(text) + "\n"
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertBlock()
        self.get_input_node().setTextCursor(cur)  # Update visible cursor

    def append_block(self):
        """Append block to output"""
        cursor = self.get_output_node().textCursor()
        cursor.movePosition(QTextCursor.End)
        block_format = QTextBlockFormat()
        block_format.setIndent(0)
        cursor.insertBlock(block_format)
        self.get_output_node().setTextCursor(cursor)

    def to_end(self):
        """Move cursor to end of output"""
        cursor = self.get_output_node().textCursor()
        cursor.movePosition(QTextCursor.End)
        self.get_output_node().setTextCursor(cursor)

    def append_raw(self, text: str, type: str = "msg-bot", item: CtxItem = None):
        """
        Append and format raw text to output

        :param text: text to append
        :param type: type of message
        :param item: CtxItem instance
        """
        if type != "msg-user":  # markdown for bot messages
            text = self.pre_format_text(text)
            text = self.append_timestamp(text, item)
            text = self.parser.parse(text)
        else:
            text = "<p>" + self.append_timestamp(self.format_user_text(text), item) + "</p>"

        text = self.post_format_text(text)
        text = '<div class="{}">'.format(type) + text.strip() + "</div>"

        self.get_output_node().append(text)
        self.to_end()

    def append_chunk_start(self):
        """
        Append start of chunk to output
        """
        cursor = self.get_output_node().textCursor()
        cursor.movePosition(QTextCursor.End)
        self.get_output_node().setTextCursor(cursor)

    def append_context_item(self, item: CtxItem):
        """
        Append context item to output

        :param item: context item
        """
        self.append_input(item)
        self.append_output(item)
        self.append_extra(item)

    def get_image_html(self, link: str) -> str:
        """
        Get image HTML

        :param link: image link
        :return: HTML
        """
        return """<a href="{link}"><img src="{link}" width="400" class="image"></a>
        <p><b>{prefix}:</b> <a href="{link}">{link}</a></p>""".format(prefix=trans('chat.prefix.img'), link=link)

    def get_url_html(self, link: str) -> str:
        """
        Get URL HTML

        :param link: URL link
        :return: HTML
        """
        return """<br/><b>{prefix}:</b> <a href="{link}">{link}</a>""".format(prefix=trans('chat.prefix.url'),
                                                                              link=link)

    def get_file_html(self, link: str) -> str:
        """
        Get file HTML

        :param link: file link
        :return: HTML
        """
        return """<div><b>{prefix}:</b> <a href="{link}">{link}</a></div>""".format(prefix=trans('chat.prefix.file'),
                                                                                    link=link)

    def append(self, text: str, end: str = "\n"):
        """
        Append text to output

        :param text: text to append
        :param end: end of the line character
        """
        cur = self.get_output_node().textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)
        s = str(text) + end
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertHtml("<br>")
        self.get_output_node().setTextCursor(cur)  # Update visible cursor

    def append_timestamp(self, text: str, item: CtxItem) -> str:
        """
        Append timestamp to text

        :param text: Input text
        :param item: Context item
        :return: Text with timestamp (if enabled)
        """
        if item is not None and self.is_timestamp_enabled() and item.input_timestamp is not None:
            ts = datetime.fromtimestamp(item.input_timestamp)
            hour = ts.strftime("%H:%M:%S")
            text = '<span class="ts">{}:</span> {}'.format(hour, text)
        return text

    def replace_code_tags(self, text: str) -> str:
        """
        Replace cmd code tags
        :param text:
        """
        pattern = r"~###~(.*?)~###~"
        replacement = r'<span class="cmd">\1</span>'
        return re.sub(pattern, replacement, text)

    def pre_format_text(self, text: str) -> str:
        """
        Post-format text

        :param text: text to format
        :return: formatted text
        """
        text = text.strip()
        text = text.replace("#~###~", "~###~")  # fix for #~###~ in text (previous versions)
        text = text.replace("# ~###~", "~###~")  # fix for # ~###~ in text (previous versions)
        text = self.replace_code_tags(text)
        return text

    def post_format_text(self, text: str) -> str:
        """
        Post-format text

        :param text: text to format
        :return: formatted text
        """
        return text.strip()

    def format_user_text(self, text: str) -> str:
        """
        Post-format user text

        :param text: text to format
        :return: formatted text
        """
        return html.escape(text).strip().replace("\n", "<br>")

    def format_chunk(self, text: str) -> str:
        """
        Format chunk

        :param text: text to format
        :return: formatted text
        """
        return text

    def is_timestamp_enabled(self) -> bool:
        """
        Check if timestamp is enabled

        :return: True if timestamp is enabled
        """
        return self.window.core.config.get('output_timestamp')

    def get_output_node(self) -> ChatOutput:
        """
        Get output node

        :return: output node
        """
        return self.window.ui.nodes['output']

    def get_input_node(self) -> ChatInput:
        """
        Get input node

        :return: input node
        """
        return self.window.ui.nodes['input']
