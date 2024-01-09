#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.06 04:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QCheckBox, QWidget

from pygpt_net.ui.layout.chat.input import Input
from pygpt_net.ui.layout.chat.calendar import Calendar
from pygpt_net.ui.widget.audio.output import AudioOutput
from pygpt_net.ui.widget.tabs.output import OutputTabs
from pygpt_net.ui.widget.textarea.output import ChatOutput
from pygpt_net.ui.widget.textarea.notepad import NotepadOutput
from pygpt_net.ui.widget.filesystem.explorer import FileExplorer
from pygpt_net.utils import trans


class Output:
    def __init__(self, window=None):
        """
        Chat output UI

        :param window: Window instance
        """
        self.window = window
        self.input = Input(window)
        self.calendar = Calendar(window)

    def setup(self) -> QWidget:
        """
        Setup output

        :return: QWidget
        :rtype: QWidget
        """
        # chat output
        self.window.ui.nodes['output'] = ChatOutput(self.window)

        # file explorer
        path = os.path.join(self.window.core.config.path, 'output')
        self.window.ui.nodes['output_files'] = FileExplorer(self.window, path)

        # notepads
        num_notepads = self.window.controller.notepad.get_num_notepads()
        if num_notepads > 0:
            for i in range(1, num_notepads + 1):
                self.window.ui.notepad[i] = NotepadOutput(self.window)
                self.window.ui.notepad[i].id = i

        # tabs
        self.window.ui.tabs['output'] = OutputTabs(self.window)
        self.window.ui.tabs['output'].addTab(self.window.ui.nodes['output'], trans('output.tab.chat'))
        self.window.ui.tabs['output'].addTab(self.window.ui.nodes['output_files'], trans('output.tab.files'))

        # calendar
        calendar = self.calendar.setup()
        self.window.ui.tabs['output'].addTab(calendar, trans('output.tab.calendar'))

        # append notepads
        if num_notepads > 0:
            for i in range(1, num_notepads + 1):
                self.window.ui.tabs['output'].addTab(self.window.ui.notepad[i],
                                                     trans('output.tab.notepad') + " " + str(i))

        layout = QVBoxLayout()
        layout.addLayout(self.setup_header())
        layout.addWidget(self.window.ui.tabs['output'])
        layout.addLayout(self.setup_bottom())

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def setup_header(self) -> QHBoxLayout:
        """
        Setup header bar

        :return: QHBoxLayout
        :rtype: QHBoxLayout
        """
        self.window.ui.nodes['chat.label'] = QLabel('')
        self.window.ui.nodes['chat.label'].setStyleSheet(self.window.controller.theme.get_style('text_faded'))

        self.window.ui.nodes['chat.model'] = QLabel("")
        self.window.ui.nodes['chat.model'].setAlignment(Qt.AlignRight)
        self.window.ui.nodes['chat.model'].setStyleSheet(self.window.controller.theme.get_style('text_faded'))

        self.window.ui.nodes['chat.plugins'] = QLabel("")
        self.window.ui.nodes['chat.plugins'].setAlignment(Qt.AlignCenter)

        header = QHBoxLayout()
        # schedule plugins addon
        self.window.ui.plugin_addon['schedule'] = QLabel("")
        header.addWidget(self.window.ui.nodes['chat.label'])
        header.addWidget(self.window.ui.nodes['chat.plugins'])
        header.addWidget(self.window.ui.plugin_addon['schedule'])
        header.addWidget(self.window.ui.nodes['chat.model'])

        return header

    def setup_bottom(self) -> QHBoxLayout:
        """
        Setup bottom bar

        :return: QHBoxLayout
        :rtype: QHBoxLayout
        """
        # add timestamp checkbox
        self.window.ui.nodes['output.timestamp'] = QCheckBox(trans('output.timestamp'))
        self.window.ui.nodes['output.timestamp'].stateChanged.connect(
            lambda: self.window.controller.chat.common.toggle_timestamp(
                self.window.ui.nodes['output.timestamp'].isChecked()))

        # raw plain text checkbox
        self.window.ui.nodes['output.raw'] = QCheckBox(trans('output.raw'))
        self.window.ui.nodes['output.raw'].clicked.connect(
            lambda: self.window.controller.chat.common.toggle_raw(
                self.window.ui.nodes['output.raw'].isChecked()))

        # add inline vision checkbox
        self.window.ui.nodes['inline.vision'] = QCheckBox(trans('inline.vision'))
        self.window.ui.nodes['inline.vision'].clicked.connect(
            lambda: self.window.controller.chat.vision.toggle(
                self.window.ui.nodes['inline.vision'].isChecked()))
        self.window.ui.nodes['inline.vision'].setVisible(False)

        # tokens info
        self.window.ui.nodes['prompt.context'] = QLabel("")
        self.window.ui.nodes['prompt.context'].setAlignment(Qt.AlignRight)
        self.window.ui.nodes['prompt.context'].setStyleSheet(self.window.controller.theme.get_style('text_faded'))
        self.window.ui.nodes['prompt.context'].setToolTip(trans('tip.tokens.ctx'))

        # plugin audio output addon
        self.window.ui.plugin_addon['audio.output'] = AudioOutput(self.window)

        opts_layout = QHBoxLayout()
        opts_layout.setSpacing(2)  #
        opts_layout.setContentsMargins(0, 0, 0, 0)
        opts_layout.addWidget(self.window.ui.nodes['output.timestamp'])
        opts_layout.addWidget(self.window.ui.nodes['output.raw'])
        # opts_layout.addStretch(1)
        opts_layout.addWidget(self.window.ui.nodes['inline.vision'])
        opts_layout.addStretch(1)

        layout = QHBoxLayout()
        layout.addLayout(opts_layout)
        layout.addWidget(self.window.ui.plugin_addon['audio.output'])
        layout.addWidget(self.window.ui.nodes['prompt.context'])

        return layout
