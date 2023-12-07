#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 22:00:00                  #
# ================================================== #
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QCheckBox, QWidget, QSplitter, QTabWidget

from ..ui.widgets import ChatOutput, NotepadOutput, FileExplorerWidget
from ..ui.input import Input
from ..utils import trans
from ..ui.highlighter import MarkdownHighlighter


class ChatBox:
    def __init__(self, window=None):
        """
        Chatbox UI

        :param window: main window object
        """
        self.window = window
        self.input = Input(window)

    def setup(self):
        """
        Setups chatbox

        :return: QSplitter
        """
        self.window.layout_input = self.input.setup()

        monofont = QFont()
        monofont.setFamily('monospace')

        self.window.data['output'] = ChatOutput(self.window)
        self.window.data['output'].setFont(monofont)

        # notepads
        self.window.data['notepad1'] = NotepadOutput(self.window)
        self.window.data['notepad2'] = NotepadOutput(self.window)
        self.window.data['notepad3'] = NotepadOutput(self.window)
        self.window.data['notepad4'] = NotepadOutput(self.window)
        self.window.data['notepad5'] = NotepadOutput(self.window)
        self.window.data['notepad1'].setFont(monofont)
        self.window.data['notepad2'].setFont(monofont)
        self.window.data['notepad3'].setFont(monofont)
        self.window.data['notepad4'].setFont(monofont)
        self.window.data['notepad5'].setFont(monofont)

        path = os.path.join(self.window.config.path, 'output')
        self.window.data['output_files'] = FileExplorerWidget(self.window, path)

        # markup highlighter
        self.window.data['output_highlighter'] = MarkdownHighlighter(self.window.data['output'])

        self.window.data['chat.model'] = QLabel("")
        self.window.data['chat.model'].setAlignment(Qt.AlignRight)
        context_layout = self.setup_context()

        self.window.data['chat.label'] = QLabel(trans("chatbox.label"))
        self.window.data['chat.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))

        self.window.data['chat.plugins'] = QLabel("")
        self.window.data['chat.plugins'].setAlignment(Qt.AlignCenter)

        header = QHBoxLayout()
        header.addWidget(self.window.data['chat.label'])
        header.addWidget(self.window.data['chat.plugins'])
        header.addWidget(self.window.data['chat.model'])

        # tabs
        self.window.tabs['output'] = QTabWidget()

        # add tabs
        self.window.tabs['output'].addTab(self.window.data['output'], trans('output.tab.chat'))
        self.window.tabs['output'].addTab(self.window.data['output_files'], trans('output.tab.files'))
        self.window.tabs['output'].addTab(self.window.data['notepad1'], trans('output.tab.notepad') + " 1")
        self.window.tabs['output'].addTab(self.window.data['notepad2'], trans('output.tab.notepad') + " 2")
        self.window.tabs['output'].addTab(self.window.data['notepad3'], trans('output.tab.notepad') + " 3")
        self.window.tabs['output'].addTab(self.window.data['notepad4'], trans('output.tab.notepad') + " 4")
        self.window.tabs['output'].addTab(self.window.data['notepad5'], trans('output.tab.notepad') + " 5")

        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(self.window.tabs['output'])
        layout.addLayout(context_layout)

        output_widget = QWidget()
        output_widget.setLayout(layout)

        input_widget = QWidget()
        input_widget.setLayout(self.window.layout_input)

        # main vertical splitter
        self.window.splitters['main.output'] = QSplitter(Qt.Vertical)
        self.window.splitters['main.output'].addWidget(output_widget)
        self.window.splitters['main.output'].addWidget(input_widget)
        self.window.splitters['main.output'].setStretchFactor(0, 4)
        self.window.splitters['main.output'].setStretchFactor(1, 1)

        return self.window.splitters['main.output']

    def setup_context(self):
        """
        Setups context

        :return: QHBoxLayout        
        """
        self.window.data['output.timestamp'] = QCheckBox(trans('output.timestamp'))
        self.window.data['output.timestamp'].setStyleSheet(
            self.window.controller.theme.get_style('checkbox'))  # Windows style fix
        self.window.data['output.timestamp'].stateChanged.connect(
            lambda: self.window.controller.output.toggle_timestamp(self.window.data['output.timestamp'].isChecked()))

        self.window.data['prompt.context'] = QLabel("")
        self.window.data['prompt.context'].setAlignment(Qt.AlignRight)

        layout = QHBoxLayout()
        layout.addWidget(self.window.data['output.timestamp'])
        layout.addWidget(self.window.data['prompt.context'])

        return layout
