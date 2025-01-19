#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.19 02:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, Slot, QUrl, QObject, Signal
from PySide6.QtWidgets import QVBoxLayout, QCheckBox, QHBoxLayout

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.textarea.editor import BaseCodeEditor
from pygpt_net.ui.widget.textarea.html import HtmlOutput, CustomWebEnginePage

import pygpt_net.icons_rc
from pygpt_net.utils import trans


class ToolWidget:
    def __init__(self, window=None, tool=None):
        """
        HTML/JS canvas widget

        :param window: Window instance
        :param tool: Tool instance
        """
        self.window = window
        self.tool = tool  # tool instance
        self.output = None  # canvas output
        self.edit = None  # canvas edit
        self.btn_edit = None  # edit checkbox

    def set_tab(self, tab):
        """
        Set tab

        :param tab: Tab
        """
        self.output.set_tab(tab)
        self.edit.set_tab(tab)

    def setup(self) -> QVBoxLayout:
        """
        Setup widget body

        :return: QVBoxLayout
        """
        self.output = CanvasOutput(self.window)
        self.output.setPage(
            CustomWebEnginePage(self.window, self.output)
        )
        self.edit = CanvasEdit(self.window)
        self.edit.setVisible(False)
        self.edit.textChanged.connect(
            lambda: self.tool.save_output()
        )

        # edit checkbox
        self.btn_edit = QCheckBox(trans("html_canvas.btn.edit"))
        self.btn_edit.stateChanged.connect(
            lambda: self.tool.toggle_edit(self)
        )

        path = self.tool.get_current_path()
        path_label = HelpLabel(path)
        path_label.setMaximumHeight(30)
        path_label.setAlignment(Qt.AlignRight)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.btn_edit)
        bottom_layout.addWidget(path_label)

        output_layout = QVBoxLayout()
        output_layout.addWidget(self.output)
        output_layout.addWidget(self.edit)
        output_layout.setContentsMargins(0, 0, 0, 0)

        # connect signals
        self.output.signals.save_as.connect(
            self.tool.handle_save_as)
        self.output.signals.audio_read.connect(
            self.window.controller.chat.render.handle_audio_read)

        self.tool.signals.update.connect(self.set_output)
        self.tool.signals.reload.connect(self.load_output)

        layout = QVBoxLayout()
        layout.addLayout(output_layout)
        layout.addLayout(bottom_layout)
        return layout

    @Slot(str)
    def set_output(self, content: str):
        """
        Set output content

        :param content: Content
        """
        self.edit.setPlainText(content)

    @Slot(str)
    def load_output(self, path: str):
        """
        Load output content

        :param path: Content
        """
        self.output.setUrl(QUrl().fromLocalFile(path))

class CanvasOutput(HtmlOutput):
    def __init__(self, window=None):
        """
        HTML canvas output

        :param window: main window
        """
        super(CanvasOutput, self).__init__(window)
        self.window = window

class CanvasEdit(BaseCodeEditor):
    def __init__(self, window=None):
        """
        Python interpreter output

        :param window: main window
        """
        super(CanvasEdit, self).__init__(window)
        self.window = window
        self.setReadOnly(False)
        self.value = 12
        self.max_font_size = 42
        self.min_font_size = 8
        self.setProperty('class', 'interpreter-output')
        self.default_stylesheet = ""
        self.setStyleSheet(self.default_stylesheet)
        self.tab = None
        self.installEventFilter(self)

    def set_tab(self, tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if event.type() == event.Type.FocusIn:
            if self.tab is not None:
                col_idx = self.tab.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
        return super().eventFilter(source, event)


class ToolSignals(QObject):
    update = Signal(str)  # data
    reload = Signal(str)  # path
