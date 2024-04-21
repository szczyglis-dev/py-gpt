#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.20 06:00:00                  #
# ================================================== #

from pygpt_net.item.ctx import CtxItem


class BaseRenderer:
    def __init__(self, window=None):
        """
        Base renderer

        :param window: Window instance
        """
        self.window = window

    def is_stream(self) -> bool:
        """
        Check if it is a stream

        :return: True if it is a stream
        """
        return self.window.core.config.get("stream")

    def begin(self, stream: bool = False):
        """Render begin"""
        pass

    def end(self, stream: bool = False):
        """Render end"""
        pass

    def end_extra(self, stream: bool = False):
        """Render end extra"""
        pass

    def stream_begin(self):
        """Render stream begin"""
        pass  # do nothing

    def stream_end(self):
        """Render stream end"""
        pass  # do nothing    

    def clear_output(self):
        """Clear output"""
        pass

    def clear_input(self):
        """Clear input"""
        pass

    def reset(self):
        """Reset"""
        pass

    def reload(self):
        """Reload output, called externally only on theme change to redraw content"""
        pass

    def append_context(self, items: list, clear: bool = True):
        """
        Append all context to output

        :param items: Context items
        :param clear: True if clear all output before append
        """
        pass

    def append_input(self, item: CtxItem):
        """
        Append text input to output

        :param item: context item
        """
        pass

    def append_output(self, item: CtxItem):
        """
        Append text output to output

        :param item: context item
        """
        pass

    def append_extra(self, item: CtxItem):
        """
        Append extra data (images, files, etc.) to output

        :param item: context item
        """
        pass

    def append_chunk(self, item: CtxItem, text_chunk: str, begin: bool = False):
        """
        Append output chunk to output

        :param item: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        pass

    def clear_all(self):
        """Clear all"""
        pass

    def on_page_loaded(self):
        pass
