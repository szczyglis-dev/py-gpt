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

from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.render.markdown.renderer import Renderer as MarkdownRenderer
from pygpt_net.core.render.plain.renderer import Renderer as PlainTextRenderer


class Render:
    def __init__(self, window=None):
        """
        Render controller

        :param window: Window instance
        """
        self.window = window
        self.markdown_renderer = MarkdownRenderer(window)
        self.plaintext_renderer = PlainTextRenderer(window)

    def get_renderer(self):
        """Get current renderer"""
        if self.window.core.config.get('render.plain'):
            return self.plaintext_renderer
        else:
            return self.markdown_renderer

    def begin(self, stream: bool = False):
        """
        Render begin

        :param stream: True if it is a stream
        """
        self.get_renderer().begin(stream)

    def end(self, stream: bool = False):
        """
        Render end

        :param stream: True if it is a stream
        """
        self.get_renderer().end(stream)

    def end_extra(self, stream: bool = False):
        """
        Render end extra

        :param stream: True if it is a stream
        """
        self.get_renderer().end_extra(stream)

    def stream_begin(self):
        """Render stream begin"""
        self.get_renderer().stream_begin()

    def stream_end(self):
        """Render stream end"""
        self.get_renderer().stream_end()

    def clear_output(self):
        """Clear output"""
        self.get_renderer().clear_output()

    def clear_input(self):
        """Clear input"""
        self.get_renderer().clear_input()

    def reset(self):
        """Reset"""
        self.get_renderer().reset()

    def reload(self):
        """Reload output"""
        self.get_renderer().reload()

    def append_context(self, items: list, clear: bool = True):
        """
        Append all context to output

        :param items: Context items
        :param clear: True if clear all output before append
        """
        self.get_renderer().append_context(items, clear)

    def append_input(self, item: CtxItem):
        """
        Append text input to output

        :param item: context item
        """
        self.get_renderer().append_input(item)

    def append_output(self, item: CtxItem):
        """
        Append text output to output

        :param item: context item
        """
        self.get_renderer().append_output(item)

    def append_extra(self, item: CtxItem):
        """
        Append extra data (images, files, etc.) to output

        :param item: context item
        """
        self.get_renderer().append_extra(item)

    def append_chunk(self, item: CtxItem, text_chunk: str, begin: bool = False):
        """
        Append output stream chunk to output

        :param item: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the stream
        """
        self.get_renderer().append_chunk(item, text_chunk, begin)

    def append_text(self, text: str):
        """
        Append custom text to input

        :param text: Text to append
        """
        self.get_renderer().append_text(text)

    def append_to_input(self, text: str):  # TODO move to input
        """
        Append text to input

        :param text: text to append
        """
        self.get_renderer().append_to_input(text)
