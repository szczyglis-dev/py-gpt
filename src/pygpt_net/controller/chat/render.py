#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.10 19:00:00                  #
# ================================================== #

from typing import Optional, List

from PySide6.QtCore import Slot, QTimer

from pygpt_net.core.events import RenderEvent
from pygpt_net.core.render.base import BaseRenderer
from pygpt_net.core.render.markdown.renderer import Renderer as MarkdownRenderer
from pygpt_net.core.render.plain.renderer import Renderer as PlainTextRenderer
from pygpt_net.core.render.web.renderer import Renderer as WebRenderer
from pygpt_net.core.tabs.tab import Tab
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

    def handle(self, event: RenderEvent):
        """
        Handle render event

        :param event: RenderEvent
        """
        name = event.name
        data = event.data
        if data is None:
            data = {}

        chunk = data.get("chunk", "")
        begin = data.get("begin", False)
        stream = data.get("stream", False)
        ctx = data.get("ctx")
        meta = data.get("meta")
        tool_data = data.get("tool_data")
        items = data.get("items")
        clear = data.get("clear", False)
        flush = data.get("flush", False)
        append = data.get("append", False)
        footer = data.get("footer", False)
        initialized = data.get("initialized", False)
        tab = data.get("tab")

        if name == RenderEvent.BEGIN:
            self.begin(meta, ctx, stream)
        elif name == RenderEvent.END:
            self.end(meta, ctx, stream)
        elif name == RenderEvent.RELOAD:
            self.reload()
        elif name == RenderEvent.RESET:
            self.reset(meta)
        elif name == RenderEvent.PREPARE:
            self.prepare()

        elif name == RenderEvent.STREAM_BEGIN:
            self.stream_begin(meta, ctx)
        elif name == RenderEvent.STREAM_APPEND:
            self.append_chunk(meta, ctx, chunk, begin)
        elif name == RenderEvent.STREAM_END:
            self.stream_end(meta, ctx)

        elif name == RenderEvent.ON_PAGE_LOAD:
            self.on_page_loaded(meta, tab)
        elif name ==RenderEvent.ON_THEME_CHANGE:
            self.on_theme_change()
        elif name == RenderEvent.ON_LOAD:
            self.on_load(meta)
        elif name == RenderEvent.ON_TS_ENABLE:
            self.on_enable_timestamp(live=initialized)
        elif name == RenderEvent.ON_TS_DISABLE:
            self.on_disable_timestamp(live=initialized)
        elif name == RenderEvent.ON_EDIT_ENABLE:
            self.on_enable_edit(live=initialized)
        elif name == RenderEvent.ON_EDIT_DISABLE:
            self.on_disable_edit(live=initialized)
        elif name == RenderEvent.ON_SWITCH:
            self.switch()

        elif name == RenderEvent.CLEAR_INPUT:
            self.clear_input()
        elif name == RenderEvent.CLEAR_OUTPUT:
            self.clear_output(meta)
        elif name == RenderEvent.CLEAR_ALL:
            self.clear_all()
        elif name == RenderEvent.CLEAR:
            self.clear(meta)

        elif name == RenderEvent.TOOL_UPDATE:
            self.tool_output_update(meta, tool_data)
        elif name == RenderEvent.TOOL_CLEAR:
            self.tool_output_clear(meta)
        elif name == RenderEvent.TOOL_BEGIN:
            self.tool_output_begin(meta)
        elif name == RenderEvent.TOOL_END:
            self.tool_output_end()

        elif name == RenderEvent.CTX_APPEND:
            self.append_context(meta, items, clear)
        elif name == RenderEvent.INPUT_APPEND:
            self.append_input(meta, ctx, flush, append)
        elif name == RenderEvent.OUTPUT_APPEND:
            self.append_output(meta, ctx)

        elif name == RenderEvent.EXTRA_APPEND:
            self.append_extra(meta, ctx, footer)
        elif name == RenderEvent.EXTRA_END:
            self.end_extra(meta, ctx)

        elif name == RenderEvent.ACTION_REGEN_SUBMIT:
            self.on_reply_submit(ctx)
        elif name == RenderEvent.ACTION_EDIT_SUBMIT:
            self.on_edit_submit(ctx)


    def get_pid(self, meta: CtxMeta) -> int:
        """
        Get PID for context meta

        :param meta: context meta
        :return: PID
        """
        return self.instance().get_pid(meta)

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
        :param stream: True if it is a stream
        """
        self.instance().begin(meta, ctx, stream)
        self.update()

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
        :param stream: True if it is a stream
        """
        self.instance().end(meta, ctx, stream)
        self.update()

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
        :param stream: True if it is a stream
        """
        self.instance().end_extra(meta, ctx, stream)
        self.update()

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
        self.instance().stream_begin(meta, ctx)
        self.update()

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
        self.instance().stream_end(meta, ctx)
        self.update()

    def clear_output(
            self,
            meta: Optional[CtxMeta] = None
    ):
        """
        Clear current active output

        :param meta: context meta
        """
        self.instance().clear_output(meta) # TODO: get meta id on load
        self.update()

    def clear_input(self):
        """Clear input"""
        self.instance().clear_input()

    def on_load(
            self,
            meta: Optional[CtxMeta] = None
    ):
        """
        On load (meta)

        :param meta: context meta
        """
        self.instance().on_load(meta)
        self.update()
        self.window.controller.ui.tabs.update_tooltip(meta.name)  # update tab tooltip

    def reset(
            self,
            meta: Optional[CtxMeta] = None
    ):
        """
        Reset current meta

        :param meta: Context meta
        """
        self.instance().reset(meta)  # TODO: get meta id on load
        self.update()

    def reload(self):
        """Reload current output"""
        self.instance().reload()  # TODO: or all outputs?
        self.update()

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
        self.instance().append_context(meta, items, clear)
        self.update()

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
        :param flush: True if flush output
        :param append: True to force append node
        """
        self.instance().append_input(meta, ctx, flush=flush, append=append)
        self.update()

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
        self.instance().append_output(meta, ctx)
        self.update()

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
        self.instance().append_extra(meta, ctx, footer)
        self.update()

    def append_chunk(
            self,
            meta: CtxMeta,
            ctx: CtxItem,
            text_chunk: str,
            begin: bool = False
    ):
        """
        Append output stream chunk to output
        
        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the stream
        """
        self.instance().append_chunk(meta, ctx, text_chunk, begin)
        self.update()

    def on_enable_edit(self, live: bool = True):
        """
        On enable edit icons - global

        :param live: True if live update
        """
        self.instance().on_enable_edit(live)
        self.update()

    def on_disable_edit(self, live: bool = True):
        """
        On disable edit icons - global

        :param live: True if live update
        """
        self.instance().on_disable_edit(live)
        self.update()

    def on_enable_timestamp(self, live: bool = True):
        """
        On enable timestamp - global

        :param live: True if live update
        """
        self.instance().on_enable_timestamp(live)
        self.update()

    def on_disable_timestamp(self, live: bool = True):
        """
        On disable timestamp - global

        :param live: True if live update
        """
        self.instance().on_disable_timestamp(live)
        self.update()

    def remove_item(self, id: int):
        """
        Remove item from output

        :param id: context item ID
        """
        self.instance().remove_item(id)
        self.update()

    def remove_items_from(self, id: int):
        """
        Remove item from output

        :param id: context item ID
        """
        self.instance().remove_items_from(id)
        self.update()

    def on_edit_submit(self, ctx: CtxItem):
        """
        On edit submit

        :param ctx: context item
        """
        self.instance().on_edit_submit(ctx)
        self.update()

    def on_remove_submit(self, ctx: CtxItem):
        """
        On remove submit

        :param ctx: context item
        """
        self.instance().on_remove_submit(ctx)
        self.update()

    def on_reply_submit(self, ctx: CtxItem):
        """
        On regenerate submit

        :param ctx: context item
        """
        self.instance().on_reply_submit(ctx)
        self.update()

    def on_page_loaded(
            self,
            meta: CtxMeta,
            tab: Optional[Tab] = None
    ):
        """
        On page loaded callback

        :param meta: context meta
        :param tab: Tab
        """
        self.instance().on_page_loaded(meta, tab)
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
        return self.instance().get_scroll_position()

    def set_scroll_position(self, position: int):
        """
        Set scroll position - active

        :param position: scroll position
        """
        self.instance().set_scroll_position(position)
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
        self.reset(meta)
        self.clear_output(meta)

    def clear_all(self):
        """Clear all"""
        self.instance().clear_all()
        self.update()

    def tool_output_append(
            self,
            meta: CtxMeta,
            content: str
    ):
        """
        Add tool output (append)

        :param meta: context meta
        :param content: content
        """
        self.instance().tool_output_append(meta, content)
        self.update()

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
        self.instance().tool_output_update(meta, content)
        self.update()

    def tool_output_clear(self, meta: CtxMeta):
        """
        Clear tool output

        :param meta: context meta
        """
        self.instance().tool_output_clear(meta)
        self.update()

    def tool_output_begin(self, meta: CtxMeta):
        """
        Begin tool output

        :param meta: context meta
        """
        self.instance().tool_output_begin(meta)
        self.update()

    def tool_output_end(self):
        """
        End tool output

        :param meta: context meta
        """
        self.instance().tool_output_end()
        self.update()

    def get_engine(self) -> str:
        """
        Get current render engine ID

        :return: engine name
        """
        return self.engine

    def switch(self):
        """
        Switch renderer (markdown/web <==> plain text) - active, TODO: remove from settings, leave only checkbox
        """
        plain = self.window.core.config.get('render.plain')
        if plain:
            self.window.controller.theme.markdown.clear()
            self.window.ui.nodes['output.timestamp'].setVisible(True)
            for pid in self.window.ui.nodes['output_plain']:
                if self.window.ui.nodes['output_plain'][pid] is not None:
                    self.window.ui.nodes['output'][pid].setVisible(False)
                    self.window.ui.nodes['output_plain'][pid].setVisible(True)
        else:
            self.window.ui.nodes['output.timestamp'].setVisible(False)
            self.window.controller.ctx.refresh()  # TODO: move to on_switch
            self.window.controller.theme.markdown.update(force=True)
            for pid in self.window.ui.nodes['output']:
                if self.window.ui.nodes['output'][pid] is not None:
                    self.window.ui.nodes['output'][pid].setVisible(True)
                    self.window.ui.nodes['output_plain'][pid].setVisible(False)

    def instance(self) -> BaseRenderer:
        """
        Get instance of current renderer

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

    @Slot(str, str)
    def handle_save_as(
            self,
            text: str,
            type: str = 'txt'
    ):
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
