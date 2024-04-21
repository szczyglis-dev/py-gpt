#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.21 19:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, QTimer

from pygpt_net.core.render.base import BaseRenderer
from pygpt_net.core.render.markdown.renderer import Renderer as MarkdownRenderer
from pygpt_net.core.render.plain.renderer import Renderer as PlainTextRenderer
from pygpt_net.core.render.web.renderer import Renderer as WebRenderer
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
        self.web_renderer = WebRenderer(window)
        self.engine = None

    def setup(self):
        """Setup render"""
        self.engine = self.window.core.config.get("render.engine")
        if self.engine == "web":
            self.connect_signals()

    def connect_signals(self):
        """Connect signals"""
        signals = self.web_renderer.get_output_node().signals
        signals.save_as.connect(self.handle_save_as)
        signals.audio_read.connect(self.handle_audio_read)

    def get_engine(self):
        """Get current engine"""
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

    def switch(self):
        """Switch renderer"""
        plain = self.window.core.config.get('render.plain')
        if plain:
            self.window.controller.theme.markdown.clear()
            if self.window.ui.nodes['output'] is not None:
                if self.window.ui.nodes['output'].isVisible():
                    self.window.ui.nodes['output'].setVisible(False)
                    self.window.ui.nodes['output_plain'].setVisible(True)
        else:
            self.window.controller.ctx.refresh()
            self.window.controller.theme.markdown.update(force=True)
            if self.window.ui.nodes['output_plain'].isVisible():
                if self.window.ui.nodes['output'] is not None:
                    self.window.ui.nodes['output'].setVisible(True)
                    self.window.ui.nodes['output_plain'].setVisible(False)

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

    def append_extra(self, item: CtxItem, footer: bool = False):
        """
        Append extra data (images, files, etc.) to output

        :param item: context item
        :param footer: True if it is a footer
        """
        self.get_renderer().append_extra(item, footer)
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

    def on_page_loaded(self):
        """On page loaded callback"""
        self.get_renderer().on_page_loaded()
        self.update()

    def update(self):
        """On update"""
        self.window.ui.nodes['output'].on_update()

    def clear_all(self):
        """Clear all"""
        self.get_renderer().clear_all()
        self.update()

    @Slot(str)
    def handle_save_as(self, text: str):
        """
        Handle save as signal

        :param text: Text to save
        """
        # fix: QTimer required here to prevent crash if signal emitted from WebEngine window
        QTimer.singleShot(0, lambda: self.window.controller.chat.common.save_text(text))

    @Slot(str)
    def handle_audio_read(self, text: str):
        """
        Handle audio read signal

        :param text: Text to read
        """
        self.window.controller.audio.read_text(text)