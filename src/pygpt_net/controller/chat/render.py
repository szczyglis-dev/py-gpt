#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.10 23:00:00                  #
# ================================================== #

from pygpt_net.core.render.base import BaseRenderer
from pygpt_net.core.render.markdown.renderer import Renderer as MarkdownRenderer
from pygpt_net.core.render.plain.renderer import Renderer as PlainTextRenderer
from pygpt_net.item.ctx import CtxItem


class Render:
    def __init__(self, window=None):
        """
        Render controller

        :param window: Window instance
        """
        self.window = window
        self.markdown_renderer = MarkdownRenderer(window)
        self.plaintext_renderer = PlainTextRenderer(window)

    def get_renderer(self) -> BaseRenderer:
        """
        Get current renderer instance

        :return: Renderer instance
        """
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
        self.update()

    def end(self, stream: bool = False):
        """
        Render end

        :param stream: True if it is a stream
        """
        self.get_renderer().end(stream)
        self.update()

    def end_extra(self, stream: bool = False):
        """
        Render end extra

        :param stream: True if it is a stream
        """
        self.get_renderer().end_extra(stream)
        self.update()

    def stream_begin(self):
        """Render stream begin"""
        self.get_renderer().stream_begin()
        self.update()

    def stream_end(self):
        """Render stream end"""
        self.get_renderer().stream_end()
        self.update()

    def clear_output(self):
        """Clear output"""
        self.get_renderer().clear_output()
        self.update()

    def clear_input(self):
        """Clear input"""
        self.get_renderer().clear_input()

    def reset(self):
        """Reset"""
        self.get_renderer().reset()
        self.update()

    def reload(self):
        """Reload output"""
        self.get_renderer().reload()
        self.update()

    def append_context(self, items: list, clear: bool = True):
        """
        Append all context to output

        :param items: Context items
        :param clear: True if clear all output before append
        """
        self.get_renderer().append_context(items, clear)
        self.update()

    def append_input(self, item: CtxItem):
        """
        Append text input to output

        :param item: context item
        """
        self.get_renderer().append_input(item)
        self.update()

    def append_output(self, item: CtxItem):
        """
        Append text output to output

        :param item: context item
        """
        self.get_renderer().append_output(item)
        self.update()

    def append_extra(self, item: CtxItem):
        """
        Append extra data (images, files, etc.) to output

        :param item: context item
        """
        self.get_renderer().append_extra(item)
        self.update()

    def append_chunk(self, item: CtxItem, text_chunk: str, begin: bool = False):
        """
        Append output stream chunk to output

        :param item: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the stream
        """
        self.get_renderer().append_chunk(item, text_chunk, begin)
        self.update()

    def update(self):
        """On update"""
        self.window.ui.nodes['output'].on_update()
