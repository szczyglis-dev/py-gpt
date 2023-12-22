#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 18:00:00                  #
# ================================================== #
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QCheckBox, QWidget, QSplitter, QTabWidget

from .widget.audio.output import AudioOutput
from .widget.textarea.output import ChatOutput
from .widget.textarea.notepad import NotepadOutput
from .widget.filesystem import FileExplorerWidget
from .input import Input
from .highlighter import MarkdownHighlighter
from ..utils import trans


class Output:
    def __init__(self, window=None):
        """
        Chatbox UI

        :param window: Window instance
        """
        self.window = window
        self.input = Input(window)

    def setup(self):
        """
        Setup output

        :return: QSplitter
        :rtype: QSplitter
        """
        self.window.layout_input = self.input.setup()

        self.window.ui.nodes['output'] = ChatOutput(self.window)

        # notepads
        self.window.ui.nodes['notepad1'] = NotepadOutput(self.window)
        self.window.ui.nodes['notepad2'] = NotepadOutput(self.window)
        self.window.ui.nodes['notepad3'] = NotepadOutput(self.window)
        self.window.ui.nodes['notepad4'] = NotepadOutput(self.window)
        self.window.ui.nodes['notepad5'] = NotepadOutput(self.window)

        path = os.path.join(self.window.config.path, 'output')
        self.window.ui.nodes['output_files'] = FileExplorerWidget(self.window, path)

        # markup highlighter
        self.window.ui.nodes['output_highlighter'] = MarkdownHighlighter(self.window.ui.nodes['output'])

        self.window.ui.nodes['chat.model'] = QLabel("")
        self.window.ui.nodes['chat.model'].setAlignment(Qt.AlignRight)
        self.window.ui.nodes['chat.model'].setStyleSheet(self.window.controller.theme.get_style('text_faded'))

        context_layout = self.setup_context()

        self.window.ui.nodes['chat.label'] = QLabel('')
        self.window.ui.nodes['chat.label'].setStyleSheet(self.window.controller.theme.get_style('text_faded'))

        self.window.ui.nodes['chat.plugins'] = QLabel("")
        self.window.ui.nodes['chat.plugins'].setAlignment(Qt.AlignCenter)

        header = QHBoxLayout()
        header.addWidget(self.window.ui.nodes['chat.label'])
        header.addWidget(self.window.ui.nodes['chat.plugins'])
        header.addWidget(self.window.ui.nodes['chat.model'])

        # tabs
        self.window.ui.tabs['output'] = QTabWidget()

        # add tabs
        self.window.ui.tabs['output'].addTab(self.window.ui.nodes['output'], trans('output.tab.chat'))
        self.window.ui.tabs['output'].addTab(self.window.ui.nodes['output_files'], trans('output.tab.files'))
        self.window.ui.tabs['output'].addTab(self.window.ui.nodes['notepad1'], trans('output.tab.notepad') + " 1")
        self.window.ui.tabs['output'].addTab(self.window.ui.nodes['notepad2'], trans('output.tab.notepad') + " 2")
        self.window.ui.tabs['output'].addTab(self.window.ui.nodes['notepad3'], trans('output.tab.notepad') + " 3")
        self.window.ui.tabs['output'].addTab(self.window.ui.nodes['notepad4'], trans('output.tab.notepad') + " 4")
        self.window.ui.tabs['output'].addTab(self.window.ui.nodes['notepad5'], trans('output.tab.notepad') + " 5")

        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(self.window.ui.tabs['output'])
        layout.addLayout(context_layout)

        output_widget = QWidget()
        output_widget.setLayout(layout)

        input_widget = QWidget()
        input_widget.setLayout(self.window.layout_input)

        # main vertical splitter
        self.window.ui.splitters['main.output'] = QSplitter(Qt.Vertical)
        self.window.ui.splitters['main.output'].addWidget(output_widget)
        self.window.ui.splitters['main.output'].addWidget(input_widget)
        self.window.ui.splitters['main.output'].setStretchFactor(0, 4)
        self.window.ui.splitters['main.output'].setStretchFactor(1, 1)

        return self.window.ui.splitters['main.output']

    def setup_context(self):
        """
        Setup context

        :return: QHBoxLayout
        :rtype: QHBoxLayout
        """
        self.window.ui.nodes['output.timestamp'] = QCheckBox(trans('output.timestamp'))
        self.window.ui.nodes['output.timestamp'].stateChanged.connect(
            lambda: self.window.controller.output.toggle_timestamp(self.window.ui.nodes['output.timestamp'].isChecked()))

        self.window.ui.nodes['prompt.context'] = QLabel("")
        self.window.ui.nodes['prompt.context'].setAlignment(Qt.AlignRight)

        # plugin audio output addon
        self.window.ui.plugin_addon['audio.output'] = AudioOutput(self.window)

        layout = QHBoxLayout()
        layout.addWidget(self.window.ui.nodes['output.timestamp'])
        layout.addWidget(self.window.ui.plugin_addon['audio.output'])
        layout.addWidget(self.window.ui.nodes['prompt.context'])

        return layout
