#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.07 23:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, QTimer

from pygpt_net.core.render.base import BaseRenderer
from pygpt_net.core.render.markdown.renderer import Renderer as MarkdownRenderer
from pygpt_net.core.render.plain.renderer import Renderer as PlainTextRenderer
from pygpt_net.core.render.web.renderer import Renderer as WebRenderer
from pygpt_net.core.text.utils import output_html2text, output_clean_html
from pygpt_net.item.ctx import CtxItem, CtxMeta


class Render:
    def __init__(self, window=None):
        """
        Render controller

        :param window: Window instance
        """
        self.window = window
        self.markdown_renderer = MarkdownRenderer(window)
        self.plaintext_renderer = PlainTextRenderer(window)
        self.web_renderer = WebRenderer(window)
        self.engine = None
        self.scroll = 0

    def setup(self):
        """Setup render"""
        self.engine = self.window.core.config.get("render.engine")

    def prepare(self):
        """Prepare render"""
        self.markdown_renderer.prepare()
        self.plaintext_renderer.prepare()
        self.web_renderer.prepare()

    def get_engine(self) -> str:
        """
        Get current render engine

        :return: engine name
        """
        return self.engine

    def get_renderer(self) -> BaseRenderer:
        """
        Get current renderer instance

        :return: Renderer instance
        """
        # get selected renderer
        if self.window.core.config.get('render.plain'):
            return self.plaintext_renderer
        else:
            if self.engine == "web":
                return self.web_renderer
            else:
                return self.markdown_renderer

    def switch(self, live: bool = True):
        """
        Switch renderer (markdown <==> plain text) - active, TODO: remove from settings, leave only checkbox

        :param live: True if live update
        """
        plain = self.window.core.config.get('render.plain')
        if plain:
            self.window.controller.theme.markdown.clear()
            for pid in self.window.ui.nodes['output_plain']:
                if self.window.ui.nodes['output'][pid] is not None:
                    self.window.ui.nodes['output'][pid].setVisible(False)
                    self.window.ui.nodes['output_plain'][pid].setVisible(True)
        else:
            self.window.controller.ctx.refresh()  # TODO: move to on_switch
            self.window.controller.theme.markdown.update(force=True)
            for pid in self.window.ui.nodes['output']:
                if self.window.ui.nodes['output'][pid] is not None:
                    self.window.ui.nodes['output'][pid].setVisible(True)
                    self.window.ui.nodes['output_plain'][pid].setVisible(False)

    def get_pid(self, meta: CtxMeta):
        """
        Get PID for context meta

        :param meta: context PID
        """
        self.get_renderer().get_pid(meta)

    def begin(self, meta: CtxMeta, ctx: CtxItem, stream: bool = False):
        """
        Render begin

        :param meta: context meta
        :param ctx: context item
        :param stream: True if it is a stream
        """
        self.get_renderer().begin(meta, ctx, stream)
        self.update()

    def end(self, meta: CtxMeta, ctx: CtxItem, stream: bool = False):
        """
        Render end

        :param meta: context meta
        :param ctx: context item
        :param stream: True if it is a stream
        """
        self.get_renderer().end(meta, ctx, stream)
        self.update()

    def end_extra(self, meta: CtxMeta, ctx: CtxItem, stream: bool = False):
        """
        Render end extra
        
        :param meta: context meta
        :param ctx: context item
        :param stream: True if it is a stream
        """
        self.get_renderer().end_extra(meta, ctx, stream)
        self.update()

    def stream_begin(self, meta: CtxMeta, ctx: CtxItem):
        """
        Render stream begin
        
        :param meta: context meta
        :param ctx: context item
        """
        self.get_renderer().stream_begin(meta, ctx)
        self.update()

    def stream_end(self, meta: CtxMeta, ctx: CtxItem):
        """
        Render stream end
        
        :param meta: context meta
        :param ctx: context item
        """
        self.get_renderer().stream_end(meta, ctx)
        self.update()

    def clear_output(self, meta: CtxMeta = None):
        """
        Clear current active output

        :param meta: Context meta
        """
        self.get_renderer().clear_output(meta) # TODO: get meta id on load
        self.update()

    def clear_input(self):
        """Clear input"""
        self.get_renderer().clear_input()

    def on_load(self, meta: CtxMeta = None):
        """
        On load (meta)

        :param meta: Context meta
        """
        self.get_renderer().on_load(meta)
        self.update()
        self.window.controller.ui.tabs.update_tooltip(meta.name)  # update tab tooltip

    def reset(self, meta: CtxMeta = None):
        """
        Reset current meta

        :param meta: Context meta
        """
        self.get_renderer().reset(meta)  # TODO: get meta id on load
        self.update()

    def reload(self):
        """Reload current output"""
        self.get_renderer().reload()  # TODO: or all outputs?
        self.update()

    def append_context(self, meta: CtxMeta, items: list, clear: bool = True):
        """
        Append all context to output

        :param meta: Context meta
        :param items: context items
        :param clear: True if clear all output before append
        """
        self.get_renderer().append_context(meta, items, clear)
        self.update()

    def append_input(self, meta: CtxMeta, ctx: CtxItem, flush: bool = True, append: bool = False):
        """
        Append text input to output
        
        :param meta: context meta
        :param ctx: context item
        :param flush: True if flush output
        :param append: True to force append node
        """
        self.get_renderer().append_input(meta, ctx, flush=flush, append=append)
        self.update()

    def append_output(self, meta: CtxMeta, ctx: CtxItem):
        """
        Append text output to output
        
        :param meta: context meta
        :param ctx: context item
        """
        self.get_renderer().append_output(meta, ctx)
        self.update()

    def append_extra(self, meta: CtxMeta, ctx: CtxItem, footer: bool = False):
        """
        Append extra data (images, files, etc.) to output
        
        :param meta: context meta
        :param ctx: context item
        :param footer: True if it is a footer
        """
        self.get_renderer().append_extra(meta, ctx, footer)
        self.update()

    def append_chunk(self, meta: CtxMeta, ctx: CtxItem, text_chunk: str, begin: bool = False):
        """
        Append output stream chunk to output
        
        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the stream
        """
        self.get_renderer().append_chunk(meta, ctx, text_chunk, begin)
        self.update()

    def on_enable_edit(self, live: bool = True):
        """
        On enable edit icons - global

        :param live: True if live update
        """
        self.get_renderer().on_enable_edit(live)
        self.update()

    def on_disable_edit(self, live: bool = True):
        """
        On disable edit icons - global

        :param live: True if live update
        """
        self.get_renderer().on_disable_edit(live)
        self.update()

    def on_enable_timestamp(self, live: bool = True):
        """
        On enable timestamp - global

        :param live: True if live update
        """
        self.get_renderer().on_enable_timestamp(live)
        self.update()

    def on_disable_timestamp(self, live: bool = True):
        """
        On disable timestamp - global

        :param live: True if live update
        """
        self.get_renderer().on_disable_timestamp(live)
        self.update()

    def remove_item(self, id: int):
        """
        Remove item from output

        :param id: context item ID
        """
        self.get_renderer().remove_item(id)
        self.update()

    def remove_items_from(self, id: int):
        """
        Remove item from output

        :param id: context item ID
        """
        self.get_renderer().remove_items_from(id)
        self.update()

    def on_edit_submit(self, ctx: CtxItem):
        """
        On edit submit

        :param ctx: context item
        """
        self.get_renderer().on_edit_submit(ctx)
        self.update()

    def on_remove_submit(self, ctx: CtxItem):
        """
        On remove submit

        :param ctx: context item
        """
        self.get_renderer().on_remove_submit(ctx)
        self.update()

    def on_reply_submit(self, ctx: CtxItem):
        """
        On regenerate submit

        :param ctx: context item
        """
        self.get_renderer().on_reply_submit(ctx)
        self.update()

    def on_page_loaded(self, meta: CtxMeta):
        """
        On page loaded callback

        :param meta: context item
        """
        self.get_renderer().on_page_loaded(meta)  # TODO: send ID with callback
        self.update()

    def on_theme_change(self):
        """On theme change - global"""
        if self.get_engine() == "web":
            self.web_renderer.on_theme_change()
        elif self.get_engine() == "legacy":
            self.markdown_renderer.on_theme_change()
        self.update()

    def get_scroll_position(self) -> int:
        """
        Get scroll position - active

        :return: scroll position
        """
        return self.get_renderer().get_scroll_position()

    def set_scroll_position(self, position: int):
        """
        Set scroll position - active

        :param position: scroll position
        """
        self.get_renderer().set_scroll_position(position)
        self.update()

    def update(self):
        """On update - active"""
        for pin in self.window.ui.nodes['output']:
            self.window.ui.nodes['output'][pin].on_update()

    def clear(self, meta: CtxMeta):
        """
        Clear renderer

        :param meta: ctx meta instance
        """
        self.window.controller.chat.render.reset(meta)
        self.window.controller.chat.render.clear_output(meta)

    def clear_all(self):
        """Clear all"""
        self.get_renderer().clear_all()
        self.update()

    def tool_output_append(self, meta: CtxMeta, content: str):
        """
        Add tool output (append)

        :param meta: context meta
        :param content: content
        """
        self.get_renderer().tool_output_append(meta, content)
        self.update()

    def tool_output_update(self, meta: CtxMeta, content: str):
        """
        Replace tool output

        :param meta: context meta
        :param content: content
        """
        self.get_renderer().tool_output_update(meta, content)
        self.update()

    def tool_output_clear(self, meta: CtxMeta):
        """
        Clear tool output

        :param meta: context meta
        """
        self.get_renderer().tool_output_clear(meta)
        self.update()

    def tool_output_begin(self, meta: CtxMeta):
        """
        Begin tool output

        :param meta: context meta
        """
        self.get_renderer().tool_output_begin(meta)
        self.update()

    def tool_output_end(self):
        """
        End tool output

        :param meta: context meta
        """
        self.get_renderer().tool_output_end()
        self.update()

    @Slot(str, str)
    def handle_save_as(self, text: str, type: str = 'txt'):
        """
        Handle save as signal  # TODO: move to another class

        :param text: Data to save
        :param type: File type
        """
        if type == 'html':
            text = output_clean_html(text)
        else:
            text = output_html2text(text)
        # fix: QTimer required here to prevent crash if signal emitted from WebEngine window
        QTimer.singleShot(0, lambda: self.window.controller.chat.common.save_text(text, type))

    @Slot(str)
    def handle_audio_read(self, text: str):
        """
        Handle audio read signal

        :param text: Text to read  # TODO: move to another class
        """
        self.window.controller.audio.read_text(text)
