#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 23:00:00                  #
# ================================================== #

from datetime import datetime
from PySide6.QtGui import QTextCursor

from pygpt_net.item.ctx import CtxItem
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.ui.widget.textarea.output import ChatOutput


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

    def append_context(self):
        """Append context to output"""
        for item in self.window.core.ctx.items:
            self.append_context_item(item)

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
            self.append("{}{}: > {}\n".format(name, hour, item.input))
        else:
            self.append("> {}\n".format(item.input))

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
            self.append("{}{}: {}".format(name, hour, item.output) + "\n")
        else:
            self.append(item.output + "\n")

    def append_extra(self, item: CtxItem):
        """
        Append extra data (images, files, etc.) to output

        :param item: context item
        """
        # self.append("SPECIAL:" + "\n")

        if len(item.images) > 0:
            for image in item.images:
                html = """
                <img src="{image}" width="400">""".format(image=image)
                self.get_output_node().append(html)
                self.append("\n")
        if len(item.files) > 0:
            for file in item.files:
                html = """
                <a href="{file}">{file}</a>""".format(file=file)
                self.get_output_node().append(html)
                self.append("\n")
        if len(item.urls) > 0:
            for url in item.urls:
                html = """
                <a href="{url}">{url}</a>""".format(url=url)
                self.get_output_node().append(html)
                self.append("\n")

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
            self.append("{}{}: ".format(name, hour), "")

        self.append(text_chunk, "")

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
                cur.insertBlock()
        self.get_output_node().setTextCursor(cur)  # Update visible cursor

    def append_text(self, text: str):
        """
        Append custom text to output

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
