#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.19 23:00:00                  #
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

        :return: True if stream is enabled
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

    def append_input(self, item: CtxItem, flush: bool = True, node: bool = False):
        """
        Append text input to output

        :param item: context item
        :param flush: True if flush
        :param node: True to force append node
        """
        pass

    def append_output(self, item: CtxItem):
        """
        Append text output to output

        :param item: context item
        """
        pass

    def append_extra(self, item: CtxItem, footer: bool = False):
        """
        Append extra data (images, files, etc.) to output

        :param item: context item
        :param footer: True if it is a footer
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

    def remove_item(self, id: int):
        """
        Remove item from output

        :param id: context item ID
        """
        pass

    def remove_items_from(self, id: int):
        """
        Remove item from output

        :param id: context item ID
        """
        pass

    def on_edit_submit(self, id: int):
        """
        On edit submit

        :param id: context item ID
        """
        self.window.controller.ctx.refresh(restore_model=False)  # allow model change

    def on_remove_submit(self, id: int):
        """
        On remove submit

        :param id: context item ID
        """
        pass

    def on_reply_submit(self, id: int):
        """
        On regenerate submit

        :param id: context item ID
        """
        self.window.controller.ctx.refresh(restore_model=False)  # allow model change

    def clear_all(self):
        """Clear all"""
        pass

    def on_page_loaded(self):
        """On page loaded callback"""
        pass

    def on_enable_edit(self, live: bool = True):
        """
        On enable edit icons

        :param live: True if live update
        """
        if live:  # default behavior
            self.window.controller.ctx.refresh()

    def on_disable_edit(self, live: bool = True):
        """
        On disable edit icons

        :param live: True if live update
        """
        if live:  # default behavior
            self.window.controller.ctx.refresh()

    def on_enable_timestamp(self, live: bool = True):
        """
        On enable timestamp

        :param live: True if live update
        """
        if live:  # default behavior
            self.window.controller.ctx.refresh()

    def on_disable_timestamp(self, live: bool = True):
        """
        On disable timestamp

        :param live: True if live update
        """
        if live:  # default behavior
            self.window.controller.ctx.refresh()

    def on_theme_change(self):
        """On theme change"""
        pass

    def get_scroll_position(self) -> int:
        """
        Get scroll position

        :return: scroll position
        """
        return 0

    def set_scroll_position(self, position: int):
        """
        Set scroll position

        :param position: scroll position
        """
        pass
