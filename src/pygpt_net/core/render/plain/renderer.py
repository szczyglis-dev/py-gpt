#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.28 00:00:00                  #
# ================================================== #

from datetime import datetime
from PySide6.QtGui import QTextCursor, QTextBlockFormat

from pygpt_net.core.render.base import BaseRenderer
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.ui.widget.textarea.output import ChatOutput
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Renderer(BaseRenderer):
    def __init__(self, window=None):
        super(Renderer, self).__init__(window)
        """
        Plain text renderer

        :param window: Window instance
        """
        self.window = window
        self.images_appended = []
        self.urls_appended = []
        self.buffer = ""
        self.is_cmd = False

    def begin(self, stream: bool = False):
        """
        Render begin

        :param stream: True if it is a stream
        """
        self.to_end()

    def end(self, stream: bool = False):
        """
        Render end

        :param stream: True if it is a stream
        """
        self.to_end()

    def end_extra(self, stream: bool = False):
        """
        Render end extra

        :param stream: True if it is a stream
        """
        self.to_end()

    def stream_begin(self):
        """Render stream begin"""
        pass  # do nothing

    def stream_end(self):
        """Render stream end"""
        pass  # do nothing

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

        i = 0
        for item in items:
            item.idx = i
            self.append_context_item(item)
            i += 1

    def append_input(self, item: CtxItem, flush: bool = True, node: bool = False):
        """
        Append text input to output

        :param item: context item
        :param flush: True if flush
        :param node: True to force append node
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

        # check if it is a command response
        is_cmd = False
        if item.input.strip().startswith("[") and item.input.strip().endswith("]"):
            is_cmd = True

        """
        # hidden internal call
        if item.internal and not is_cmd and item.idx > 0 and not item.input.strip().startswith("user: "):
            self.append_raw('>>>')
            return
        """

        self.append_raw(text.strip())
        self.to_end()

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
            text = '{}{} {}'.format(name, hour, item.output)
        else:
            text = "{}".format(item.output)
        self.append_raw(text.strip())
        self.to_end()

    def append_extra(self, item: CtxItem):
        """
        Append extra data (images, files, etc.) to output

        :param item: context item
        """
        appended = []

        # images
        c = len(item.images)
        if c > 0:
            n = 1
            for image in item.images:
                if image in appended or image in self.images_appended:
                    continue
                try:
                    appended.append(image)
                    self.append_raw(self.get_image_html(image, n, c))
                    self.images_appended.append(image)
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
                    self.append_raw(self.get_file_html(file, n, c))
                    n += 1
                except Exception as e:
                    pass

        # urls
        c = len(item.urls)
        if c > 0:
            urls_str = []
            n = 1
            for url in item.urls:
                if url in appended or url in self.urls_appended:
                    continue
                try:
                    appended.append(url)
                    urls_str.append(self.get_url_html(url, n, c))
                    self.urls_appended.append(url)
                    n += 1
                except Exception as e:
                    pass
            if urls_str:
                self.append_raw("\n" + "\n".join(urls_str))

        # docs json
        if self.window.core.config.get('ctx.sources'):
            if item.doc_ids is not None and len(item.doc_ids) > 0:
                try:
                    docs = self.get_docs_html(item.doc_ids)
                    self.get_output_node().append(docs)
                    self.to_end()
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

            text_chunk = "\n" + text_chunk

            self.append_block()
            self.append_chunk_start()

        self.buffer += raw_chunk
        self.append(self.format_chunk(text_chunk), "")

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
        prev_text = self.get_output_node().toPlainText()
        if prev_text != "":
            prev_text += "\n\n"
        new_text = prev_text + text.strip()
        self.get_output_node().setText(new_text)
        cur = self.get_output_node().textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)

    def append_chunk_start(self):
        """Append start of chunk to output"""
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

    def get_image_html(self, url: str, num: int = None, num_all: int = None) -> str:
        """
        Get image HTML

        :param url: URL to image
        :param num: number of image
        :param num_all: number of all images
        :return: HTML code
        """
        num_str = ""
        if num is not None and num_all is not None and num_all > 1:
            num_str = " [{}]".format(num)
        url, path = self.window.core.filesystem.extract_local_url(url)
        return """\n{prefix}{num}: {path}\n""".\
            format(prefix=trans('chat.prefix.img'),
                   path=path,
                   num=num_str)

    def get_url_html(self, url: str, num: int = None, num_all: int = None) -> str:
        """
        Get URL HTML

        :param url: external URL
        :param num: number of URL
        :param num_all: number of all URLs
        :return: HTML
        """
        num_str = ""
        if num is not None and num_all is not None and num_all > 1:
            num_str = " [{}]".format(num)
        return """{prefix}{num}: {url}""".\
            format(prefix=trans('chat.prefix.url'),
                   url=url,
                   num=num_str)

    def get_docs_html(self, docs: list) -> str:
        """
        Get Llama-index doc metadata HTML

        :param docs: list of document metadata
        :return: HTML code
        """
        html = ""
        html_sources = ""
        num = 1
        max = 3
        try:
            for item in docs:
                for uuid, doc_json in item.items():
                    """
                    Example doc (file metadata):
                    {'a2c7af6d-3c34-4c28-bf2d-6161e7fb525e': {
                        'file_path': '/home/user/.config/pygpt-net/data/my_cars.txt',
                        'file_name': '/home/user/.config/pygpt-net/data/my_cars.txt', 'file_type': 'text/plain',
                        'file_size': 28, 'creation_date': '2024-03-03', 'last_modified_date': '2024-03-03',
                        'last_accessed_date': '2024-03-03'}}
                    """
                    doc_parts = []
                    for key in doc_json:
                        doc_parts.append("{}: {}".format(key, doc_json[key]))
                    html_sources += "\n[{}] {}: {}".format(num, uuid, ", ".join(doc_parts))
                    num += 1
                if num >= max:
                    break
        except Exception as e:
            pass

        if html_sources != "":
            html += "\n----------\n{prefix}:\n".format(prefix=trans('chat.prefix.doc'))
            html += html_sources
        return html

    def get_file_html(self, url: str, num: int = None, num_all: int = None) -> str:
        """
        Get file HTML

        :param url: URL to file
        :param num: number of file
        :param num_all: number of all files
        :return: HTML
        """
        num_str = ""
        if num is not None and num_all is not None and num_all > 1:
            num_str = " [{}]".format(num)
        url, path = self.window.core.filesystem.extract_local_url(url)
        return """\n{prefix}{num}: {path}\n""".\
            format(prefix=trans('chat.prefix.file'),
                   path=path,
                   num=num_str)

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
                cur.insertText("\n")
        self.get_output_node().setTextCursor(cur)  # Update visible cursor

    def append_timestamp(self, text: str, item: CtxItem) -> str:
        """
        Append timestamp to text

        :param text: Input text
        :param item: Context item
        :return: Text with timestamp (if enabled)
        """
        if item is not None \
                and self.is_timestamp_enabled() \
                and item.input_timestamp is not None:
            ts = datetime.fromtimestamp(item.input_timestamp)
            hour = ts.strftime("%H:%M:%S")
            text = '{}: {}'.format(hour, text)
        return text

    def pre_format_text(self, text: str) -> str:
        """
        Post-format text

        :param text: text to format
        :return: formatted text
        """
        text = text.strip()
        text = text.replace("#~###~", "~###~")  # fix for #~###~ in text (previous versions)
        text = text.replace("# ~###~", "~###~")  # fix for # ~###~ in text (previous versions)
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
        return text

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
        return self.window.ui.nodes['output_plain']

    def get_input_node(self) -> ChatInput:
        """
        Get input node

        :return: input node
        """
        return self.window.ui.nodes['input']

    def clear_all(self):
        """Clear all"""
        self.get_output_node().clear()
        self.get_output_node().document().setDefaultStyleSheet("")
        self.get_output_node().setStyleSheet("")
        self.get_output_node().document().setMarkdown("")
        self.get_output_node().document().setHtml("")
        self.get_output_node().setPlainText("")
