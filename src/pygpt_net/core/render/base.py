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

from typing import Optional, List

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.item.ctx import CtxItem, CtxMeta


class BaseRenderer:
    def __init__(self, window=None):
        """
        Base renderer

        :param window: Window instance
        """
        self.window = window
        self.tab = None

    def set_tab(self, tab: Tab):
        """
        Append tab

        :param tab: Tab
        """
        self.tab = tab

    def prepare(self):
        """
        Prepare renderer
        """
        pass

    def get_pid(self, meta: CtxMeta):
        """
        Get PID for context meta
        
        :param meta: context PID
        """
        pass

    def is_stream(self) -> bool:
        """
        Check if it is a stream

        :return: True if stream is enabled
        """
        return self.window.core.config.get("stream")

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
        :param stream: True if stream
        """
        pass

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
        :param stream: True if stream
        """
        pass

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
        :param stream: True if stream
        """
        pass

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

    def clear_output(
            self,
            meta: Optional[CtxMeta] = None
    ):
        """
        Clear output

        :param meta: context meta
        """
        pass

    def clear_input(self):
        """Clear input"""
        pass

    def reset(self, meta: CtxMeta = None):
        """
        Reset

        :param meta: context meta
        """
        pass

    def reload(self):
        """Reload all outputs, called externally only on theme change to redraw content"""
        pass

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
        pass

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
        pass

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
        pass

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
        pass

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
        :param ctx: context item
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

    def on_edit_submit(self, ctx: CtxItem):
        """
        On edit submit

        :param ctx: context item
        """
        self.window.controller.ctx.refresh(restore_model=False)  # allow model change

    def on_remove_submit(self, ctx: CtxItem):
        """
        On remove submit

        :param ctx: context item
        """
        pass

    def on_reply_submit(self, ctx: CtxItem):
        """
        On regenerate submit

        :param ctx: context item
        """
        self.window.controller.ctx.refresh(restore_model=False)  # allow model change

    def clear_all(self):
        """Clear all"""
        pass

    def on_load(self, meta: CtxMeta = None):
        """
        On load (meta)

        :param meta: context metam
        """
        pass

    def on_page_loaded(
            self,
            meta: Optional[CtxMeta] = None,
            tab: Optional[Tab] = None):
        """
        On page loaded callback

        :param meta: context meta
        :param tab: Tab
        """
        self.tab = tab

    def on_enable_edit(
            self,
            live: bool = True
    ):
        """
        On enable edit icons

        :param live: True if live update
        """
        if live:  # default behavior
            self.window.controller.ctx.refresh()

    def on_disable_edit(
            self,
            live: bool = True
    ):
        """
        On disable edit icons

        :param live: True if live update
        """
        if live:  # default behavior
            self.window.controller.ctx.refresh()

    def on_enable_timestamp(
            self,
            live: bool = True
    ):
        """
        On enable timestamp

        :param live: True if live update
        """
        if live:  # default behavior
            self.window.controller.ctx.refresh()

    def on_disable_timestamp(
            self,
            live: bool = True
    ):
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

    def tool_output_append(
            self,
            meta:
            CtxMeta,
            content: str
    ):
        """
        Add tool output (append)

        :param meta: context meta
        :param content: content
        """
        pass

    def tool_output_update(
            self,
            meta: CtxMeta,
            content: str
    ):
        """
        Replace tool output

        :param meta: context meta
        :param content: content
        """
        pass

    def tool_output_clear(
            self,
            meta: CtxMeta
    ):
        """
        Clear tool output

        :param meta: context meta
        """
        pass

    def tool_output_begin(
            self,
            meta: CtxMeta
    ):
        """
        Begin tool output

        :param meta: context meta
        """
        pass

    def tool_output_end(self):
        """End tool output"""
        pass
