#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
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

    _STATE_EVENTS = (
        RenderEvent.STATE_IDLE,
        RenderEvent.STATE_BUSY,
        RenderEvent.STATE_ERROR,
    )

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
        self.renderer = None

    def setup(self) -> None:
        """Setup render"""
        self.engine = self.window.core.config.get("render.engine")
        if self.window.core.config.get('render.plain'):
            self.renderer = self.plaintext_renderer
        else:
            self.renderer = self.web_renderer if self.engine == "web" else self.markdown_renderer

    def prepare(self) -> None:
        """Prepare render"""
        self.markdown_renderer.prepare()
        self.plaintext_renderer.prepare()
        self.web_renderer.prepare()

    def handle(self, event: RenderEvent) -> None:
        """
        Handle render event

        :param event: RenderEvent
        """
        name = event.name
        data = event.data or {}

        if name == RenderEvent.BEGIN:
            self.begin(data.get("meta"), data.get("ctx"), data.get("stream", False))
        elif name == RenderEvent.END:
            self.end(data.get("meta"), data.get("ctx"), data.get("stream", False))
        elif name == RenderEvent.RELOAD:
            self.reload()
        elif name == RenderEvent.RESET:
            self.reset(data.get("meta"))
        elif name == RenderEvent.PREPARE:
            self.prepare()

        elif name == RenderEvent.STREAM_BEGIN:
            self.stream_begin(data.get("meta"), data.get("ctx"))
        elif name == RenderEvent.STREAM_APPEND:
            self.instance().append_chunk(
                data.get("meta"),
                data.get("ctx"),
                data.get("chunk", ""),
                data.get("begin", False),
            )
        elif name == RenderEvent.STREAM_NEXT:
            self.next_chunk(data.get("meta"), data.get("ctx"))
        elif name == RenderEvent.STREAM_END:
            self.stream_end(data.get("meta"), data.get("ctx"))

        elif name == RenderEvent.ON_PAGE_LOAD:
            self.on_page_loaded(data.get("meta"), data.get("tab"))
        elif name == RenderEvent.ON_THEME_CHANGE:
            self.on_theme_change()
        elif name == RenderEvent.ON_LOAD:
            self.on_load(data.get("meta"))
        elif name == RenderEvent.FRESH:
            self.fresh(data.get("meta"))
        elif name == RenderEvent.ON_TS_ENABLE:
            self.on_enable_timestamp(live=data.get("initialized", False))
        elif name == RenderEvent.ON_TS_DISABLE:
            self.on_disable_timestamp(live=data.get("initialized", False))
        elif name == RenderEvent.ON_EDIT_ENABLE:
            self.on_enable_edit(live=data.get("initialized", False))
        elif name == RenderEvent.ON_EDIT_DISABLE:
            self.on_disable_edit(live=data.get("initialized", False))
        elif name == RenderEvent.ON_SWITCH:
            self.switch()

        elif name == RenderEvent.CLEAR_INPUT:
            self.clear_input()
        elif name == RenderEvent.CLEAR_OUTPUT:
            self.clear_output(data.get("meta"))
        elif name == RenderEvent.CLEAR_ALL:
            self.clear_all()
        elif name == RenderEvent.CLEAR:
            self.clear(data.get("meta"))

        elif name == RenderEvent.TOOL_UPDATE:
            self.tool_output_update(data.get("meta"), data.get("tool_data"))
        elif name == RenderEvent.TOOL_CLEAR:
            self.tool_output_clear(data.get("meta"))
        elif name == RenderEvent.TOOL_BEGIN:
            self.tool_output_begin(data.get("meta"))
        elif name == RenderEvent.TOOL_END:
            self.tool_output_end()

        elif name == RenderEvent.CTX_APPEND:
            self.append_context(data.get("meta"), data.get("items"), data.get("clear", True))
        elif name == RenderEvent.INPUT_APPEND:
            self.append_input(
                data.get("meta"),
                data.get("ctx"),
                data.get("flush", True),
                data.get("append", False),
            )
        elif name == RenderEvent.OUTPUT_APPEND:
            self.append_output(data.get("meta"), data.get("ctx"))

        elif name == RenderEvent.EXTRA_APPEND:
            self.append_extra(data.get("meta"), data.get("ctx"), data.get("footer", False))
        elif name == RenderEvent.EXTRA_END:
            self.end_extra(data.get("meta"), data.get("ctx"))

        elif name == RenderEvent.LIVE_APPEND:
            self.append_live(
                data.get("meta"),
                data.get("ctx"),
                data.get("chunk", ""),
                data.get("begin", False),
            )
        elif name == RenderEvent.LIVE_CLEAR:
            self.clear_live(data.get("meta"), data.get("ctx"))

        elif name == RenderEvent.ACTION_REGEN_SUBMIT:
            self.on_reply_submit(data.get("ctx"))
        elif name == RenderEvent.ACTION_EDIT_SUBMIT:
            self.on_edit_submit(data.get("ctx"))

        elif name in self._STATE_EVENTS:
            meta = data.get("meta") or self.window.core.ctx.get_current_meta()
            self.on_state_changed(name, meta)

    def on_state_changed(self, state: str, meta: Optional[CtxMeta] = None) -> None:
        """
        Handle state change event

        :param state: State name
        :param meta: Context meta
        """
        self.instance().state_changed(state, meta)

    def append_live(self, meta: CtxMeta, ctx: CtxItem, text_chunk: str, begin: bool = False) -> None:
        """
        Append live text chunk to output

        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the stream
        """
        self.instance().append_live(meta, ctx, text_chunk, begin)

    def clear_live(self, meta: CtxMeta, ctx: CtxItem) -> None:
        """
        Clear live output

        :param meta: context meta
        :param ctx: context item
        """
        self.instance().clear_live(meta, ctx)
        self.update()

    def get_pid(self, meta: CtxMeta) -> int:
        """
        Get PID for context meta

        :param meta: context meta
        :return: PID
        """
        return self.instance().get_pid(meta)

    def begin(self, meta: CtxMeta, ctx: CtxItem, stream: bool = False) -> None:
        """
        Render begin

        :param meta: context meta
        :param ctx: context item
        :param stream: True if it is a stream
        """
        self.instance().begin(meta, ctx, stream)
        self.update()

    def end(self, meta: CtxMeta, ctx: CtxItem, stream: bool = False) -> None:
        """
        Render end

        :param meta: context meta
        :param ctx: context item
        :param stream: True if it is a stream
        """
        self.instance().end(meta, ctx, stream)
        self.update()

    def end_extra(self, meta: CtxMeta, ctx: CtxItem, stream: bool = False) -> None:
        """
        Render end extra

        :param meta: context meta
        :param ctx: context item
        :param stream: True if it is a stream
        """
        self.instance().end_extra(meta, ctx, stream)
        self.update()

    def stream_begin(self, meta: CtxMeta, ctx: CtxItem) -> None:
        """
        Render stream begin

        :param meta: context meta
        :param ctx: context item
        """
        self.instance().stream_begin(meta, ctx)
        self.update()

    def stream_end(self, meta: CtxMeta, ctx: CtxItem) -> None:
        """
        Render stream end

        :param meta: context meta
        :param ctx: context item
        """
        self.instance().stream_end(meta, ctx)
        self.update()

    def clear_output(self, meta: Optional[CtxMeta] = None) -> None:
        """
        Clear current active output

        :param meta: context meta
        """
        self.instance().clear_output(meta) # TODO: get meta id on load
        self.update()

    def clear_input(self) -> None:
        """Clear input"""
        self.instance().clear_input()

    def on_load(self, meta: Optional[CtxMeta] = None) -> None:
        """
        On load (meta)

        :param meta: context meta
        """
        self.instance().on_load(meta)
        self.update()
        self.window.controller.ui.tabs.update_tooltip(meta.name)  # update tab tooltip

    def fresh(self, meta: Optional[CtxMeta] = None) -> None:
        """
        On load (meta)

        :param meta: context meta
        """
        self.instance().fresh(meta)

    def reset(self, meta: Optional[CtxMeta] = None) -> None:
        """
        Reset current meta

        :param meta: Context meta
        """
        self.instance().reset(meta)  # TODO: get meta id on load
        self.update()

    def reload(self) -> None:
        """Reload current output"""
        self.instance().reload()  # TODO: or all outputs?
        self.update()

    def append_context(self, meta: CtxMeta, items: List[CtxItem], clear: bool = True) -> None:
        """
        Append all context to output

        :param meta: context meta
        :param items: context items
        :param clear: True if clear all output before append
        """
        self.instance().append_context(meta, items, clear)
        self.update()

    def append_input(self, meta: CtxMeta, ctx: CtxItem, flush: bool = True, append: bool = False) -> None:
        """
        Append text input to output

        :param meta: context meta
        :param ctx: context item
        :param flush: True if flush output
        :param append: True to force append node
        """
        self.instance().append_input(meta, ctx, flush=flush, append=append)
        self.update()

    def append_output(self, meta: CtxMeta, ctx: CtxItem) -> None:
        """
        Append text output to output

        :param meta: context meta
        :param ctx: context item
        """
        self.instance().append_output(meta, ctx)
        self.update()

    def append_extra(self, meta: CtxMeta, ctx: CtxItem, footer: bool = False) -> None:
        """
        Append extra data (images, files, etc.) to output

        :param meta: context meta
        :param ctx: context item
        :param footer: True if it is a footer
        """
        self.instance().append_extra(meta, ctx, footer)
        self.update()

    def append_chunk(self, meta: CtxMeta, ctx: CtxItem, text_chunk: str, begin: bool = False) -> None:
        """
        Append output stream chunk to output

        :param meta: context meta
        :param ctx: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the stream
        """
        self.instance().append_chunk(meta, ctx, text_chunk, begin)

    def next_chunk(self, meta: CtxMeta, ctx: CtxItem) -> None:
        """
        Flush current stream and start with new chunks

        :param meta: context meta
        :param ctx: context item
        """
        self.instance().next_chunk(meta, ctx)
        self.update()

    def on_enable_edit(self, live: bool = True) -> None:
        """
        On enable edit icons - global

        :param live: True if live update
        """
        self.instance().on_enable_edit(live)
        self.update()

    def on_disable_edit(self, live: bool = True) -> None:
        """
        On disable edit icons - global

        :param live: True if live update
        """
        self.instance().on_disable_edit(live)
        self.update()

    def on_enable_timestamp(self, live: bool = True) -> None:
        """
        On enable timestamp - global

        :param live: True if live update
        """
        self.instance().on_enable_timestamp(live)
        self.update()

    def on_disable_timestamp(self, live: bool = True) -> None:
        """
        On disable timestamp - global

        :param live: True if live update
        """
        self.instance().on_disable_timestamp(live)
        self.update()

    def remove_item(self, id: int) -> None:
        """
        Remove item from output

        :param id: context item ID
        """
        self.instance().remove_item(id)
        self.update()

    def remove_items_from(self, id: int) -> None:
        """
        Remove item from output

        :param id: context item ID
        """
        self.instance().remove_items_from(id)
        self.update()

    def on_edit_submit(self, ctx: CtxItem) -> None:
        """
        On edit submit

        :param ctx: context item
        """
        self.instance().on_edit_submit(ctx)
        self.update()

    def on_remove_submit(self, ctx: CtxItem) -> None:
        """
        On remove submit

        :param ctx: context item
        """
        self.instance().on_remove_submit(ctx)
        self.update()

    def on_reply_submit(self, ctx: CtxItem) -> None:
        """
        On regenerate submit

        :param ctx: context item
        """
        self.instance().on_reply_submit(ctx)
        self.update()

    def on_page_loaded(self, meta: CtxMeta, tab: Optional[Tab] = None) -> None:
        """
        On page loaded callback

        :param meta: context meta
        :param tab: Tab
        """
        self.instance().on_page_loaded(meta, tab)
        self.update()

    def on_theme_change(self) -> None:
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

    def set_scroll_position(self, position: int) -> None:
        """
        Set scroll position - active

        :param position: scroll position
        """
        self.instance().set_scroll_position(position)
        self.update()

    def update(self) -> None:
        """On update - active"""
        nodes = self.window.ui.nodes
        outputs = nodes.get('output')
        if not outputs:
            return
        for node in outputs.values():
            node.on_update()

    def clear(self, meta: CtxMeta) -> None:
        """
        Clear renderer

        :param meta: ctx meta instance
        """
        inst = self.instance()
        inst.reset(meta)
        inst.clear_output(meta)
        self.update()

    def clear_all(self) -> None:
        """Clear all"""
        self.instance().clear_all()
        self.update()

    def remove_pid(self, pid: int) -> None:
        """
        Remove PID from renderer

        :param pid: PID to remove
        """
        self.plaintext_renderer.remove_pid(pid)
        self.markdown_renderer.remove_pid(pid)
        self.web_renderer.remove_pid(pid)

    def tool_output_append(self, meta: CtxMeta, content: str) -> None:
        """
        Add tool output (append)

        :param meta: context meta
        :param content: content
        """
        self.instance().tool_output_append(meta, content)
        self.update()

    def tool_output_update(self, meta: CtxMeta, content: str) -> None:
        """
        Replace tool output

        :param meta: context meta
        :param content: content
        """
        self.instance().tool_output_update(meta, content)
        self.update()

    def tool_output_clear(self, meta: CtxMeta) -> None:
        """
        Clear tool output

        :param meta: context meta
        """
        self.instance().tool_output_clear(meta)
        self.update()

    def tool_output_begin(self, meta: CtxMeta) -> None:
        """
        Begin tool output

        :param meta: context meta
        """
        self.instance().tool_output_begin(meta)
        self.update()

    def tool_output_end(self) -> None:
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

    def switch(self) -> None:
        """
        Switch renderer (markdown/web <==> plain text) - active, TODO: remove from settings, leave only checkbox
        """
        plain = self.window.core.config.get('render.plain')
        nodes = self.window.ui.nodes
        if plain:
            self.window.controller.theme.markdown.clear()
            nodes['output.timestamp'].setVisible(True)
            outputs = nodes.get('output', {})
            outputs_plain = nodes.get('output_plain', {})
            for pid, w_plain in outputs_plain.items():
                w = outputs.get(pid)
                if w and w_plain:
                    w.setVisible(False)
                    w_plain.setVisible(True)
        else:
            nodes['output.timestamp'].setVisible(False)
            self.window.controller.theme.markdown.update(force=True)
            outputs = nodes.get('output', {})
            outputs_plain = nodes.get('output_plain', {})
            for pid, w in outputs.items():
                w_plain = outputs_plain.get(pid)
                if w and w_plain:
                    w.setVisible(True)
                    w_plain.setVisible(False)

        if plain:
            self.renderer = self.plaintext_renderer
        else:
            if self.engine == "web":
                self.renderer = self.web_renderer
            else:
                self.renderer = self.markdown_renderer

        self.window.controller.ctx.refresh()

    def instance(self) -> BaseRenderer:
        """
        Get instance of current renderer

        :return: Renderer instance
        """
        if self.renderer:
            return self.renderer
        if self.window.core.config.get('render.plain'):
            return self.plaintext_renderer
        else:
            if self.engine == "web":
                return self.web_renderer
            else:
                return self.markdown_renderer

    @Slot(str, str)
    def handle_save_as(self, text: str, type: str = 'txt') -> None:
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