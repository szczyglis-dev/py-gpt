#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.01 03:00:00                  #
# ================================================== #

import re
from datetime import datetime
from PySide6.QtGui import QTextCursor, QTextBlockFormat
import markdown

from pygpt_net.item.ctx import CtxItem
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.ui.widget.textarea.output import ChatOutput
from pygpt_net.utils import trans


class Render:
    def __init__(self, window=None):
        """
        Render controller

        :param window: Window instance
        """
        self.window = window

    def clear(self):
        """Clear output"""
        self.get_output_node().clear()

    def clear_input(self):
        """Clear input"""
        self.get_input_node().clear()

    def reload(self):
        """Reload output"""
        self.window.controller.ctx.refresh_output()

    def end_of_stream(self):
        """Reload output"""
        # self.append("\n")  # append EOL
        pass

    def append_context(self):
        """Append context to output"""
        for item in self.window.core.ctx.items:
            self.append_context_item(item)

    def replace_code_tags(self, text):
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
        return text.strip().replace("\n", "<br>")

    def format_chunk(self, text: str) -> str:
        """
        Format chunk

        :param text: text to format
        :return: formatted text
        """
        return text

    def append_block(self):
        cursor = self.get_output_node().textCursor()
        cursor.movePosition(QTextCursor.End)
        block_format = QTextBlockFormat()
        block_format.setIndent(0)
        cursor.insertBlock(block_format)

    def to_end(self):
        cursor = self.get_output_node().textCursor()
        cursor.movePosition(QTextCursor.End)
        self.get_output_node().setTextCursor(cursor)

    def append_raw(self, text: str, type: str = "msg-bot"):
        """
        Append and format raw text to output

        :param text: text to append
        :param type: type of message
        """
        prefix = ""
        if type == "msg-user":
            prefix = "&gt; "
        text = prefix + text

        if type != "msg-user":  # markdown for bot messages
            text = self.pre_format_text(text)
            text = markdown.markdown(text.strip(), extensions=['fenced_code'])
        else:
            text = "<p>" + self.format_user_text(text) + "</p>"

        text = self.post_format_text(text)
        text = '<div class="{}">'.format(type) + text.strip() + "</div>"

        # reset formatting
        is_empty = not self.get_output_node().document().toPlainText().strip()
        if not is_empty:
            self.append_block()

        self.get_output_node().append(text)
        self.to_end()

    def append_chunk_start(self):
        """
        Append start of chunk to output
        """
        text = '<div class="msg-bot"></div>'
        self.get_output_node().append(text)
        cursor = self.get_output_node().textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml('<div class="msg-bot">&nbsp;</div>')  # fix for font change
        self.get_output_node().setTextCursor(cursor)

    def append_context_item(self, item: CtxItem):
        """
        Append context item to output

        :param item: context item
        """
        self.append_input(item)
        self.append_output(item)
        self.append_extra(item)

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
            ts = datetime.fromtimestamp(item.input_timestamp)
            hour = ts.strftime("%H:%M:%S")
            text = "{}{}: {}".format(name, hour, item.input)
        else:
            text = "{}".format(item.input)

        self.append_raw(text, "msg-user")

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
            ts = datetime.fromtimestamp(item.output_timestamp)
            hour = ts.strftime("%H:%M:%S")
            text = "{}{}: {}".format(name, hour, item.output)
        else:
            text = "{}".format(item.output)
        self.append_raw(text, "msg-bot")

    def append_extra(self, item: CtxItem):
        """
        Append extra data (images, files, etc.) to output

        :param item: context item
        """
        already_appended = []
        if len(item.images) > 0:
            for image in item.images:
                if image in already_appended:
                    continue
                try:
                    html = """
                    <img src="{image}" width="400" class="image">
                    <p><b>{prefix}:</b> <a href="{image}">{image}</a></p>""".format(prefix=trans('chat.prefix.img'), image=image)
                    self.get_output_node().append(html)
                    already_appended.append(image)
                except Exception as e:
                    pass
        if len(item.files) > 0:
            for file in item.files:
                if file in already_appended:
                    continue
                try:
                    html = """
                    <b>{prefix}:</b> <a href="{file}">{file}</a>""".format(prefix=trans('chat.prefix.file'), file=file)
                    self.get_output_node().append(html)
                    already_appended.append(file)
                except Exception as e:
                    pass
        if len(item.urls) > 0:
            for url in item.urls:
                if url in already_appended:
                    continue
                try:
                    html = """
                    <b>{prefix}:</b> <a href="{url}">{url}</a>""".format(prefix=trans('chat.prefix.url'), url=url)
                    self.get_output_node().append(html)
                    already_appended.append(url)
                except Exception as e:
                    pass

        # jump to end
        if len(already_appended) > 0:
            self.to_end()
            #self.append_block()

    def append_chunk(self, item: CtxItem, text_chunk: str, begin: bool = False):
        """
        Append output chunk to output

        :param item: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        if text_chunk is None or text_chunk == "":
            return
        if begin and self.is_timestamp_enabled() and item.output_timestamp is not None:
            name = ""
            if item.output_name is not None and item.output_name != "":
                name = item.output_name + " "
            ts = datetime.fromtimestamp(item.output_timestamp)
            hour = ts.strftime("%H:%M:%S")
            self.to_end()
            self.append_chunk_start()
            self.append_block()
            text_chunk = "{}{}: ".format(name, hour) + text_chunk
        elif begin:
            self.to_end()
            self.append_chunk_start()
            self.append_block()

        self.append(self.format_chunk(text_chunk), "")

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
