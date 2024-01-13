#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 10:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QCheckBox, QWidget, QSizePolicy

from pygpt_net.ui.layout.chat.input import Input
from pygpt_net.ui.layout.chat.calendar import Calendar
from pygpt_net.ui.layout.chat.painter import Painter
from pygpt_net.ui.widget.audio.output import AudioOutput
from pygpt_net.ui.widget.tabs.output import OutputTabs
from pygpt_net.ui.widget.textarea.output import ChatOutput
from pygpt_net.ui.widget.textarea.notepad import NotepadWidget
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
        self.painter = Painter(window)

    def setup(self) -> QWidget:
        """
        Setup output

        :return: QWidget
        :rtype: QWidget
        """
        # chat output
        self.window.ui.nodes['output'] = ChatOutput(self.window)

        # index status data
        index_data = self.window.core.idx.get_idx_data()  # get all idx data

        # file explorer
        path = self.window.core.config.get_user_dir('data')
        self.window.ui.nodes['output_files'] = FileExplorer(self.window, path, index_data)

        # notepads
        num_notepads = self.window.controller.notepad.get_num_notepads()
        if num_notepads > 0:
            for i in range(1, num_notepads + 1):
                self.window.ui.notepad[i] = NotepadWidget(self.window)
                self.window.ui.notepad[i].id = i

        # tabs
        self.window.ui.tabs['output'] = OutputTabs(self.window)
        self.window.ui.tabs['output'].addTab(self.window.ui.nodes['output'], trans('output.tab.chat'))
        self.window.ui.tabs['output'].addTab(self.window.ui.nodes['output_files'], trans('output.tab.files'))

        # calendar
        calendar = self.calendar.setup()
        self.window.ui.tabs['output'].addTab(calendar, trans('output.tab.calendar'))

        # painter
        painter = self.painter.setup()
        self.window.ui.tabs['output'].addTab(painter, trans('output.tab.painter'))

        # append notepads
        if num_notepads > 0:
            for i in range(1, num_notepads + 1):
                title = trans('output.tab.notepad')
                if num_notepads > 1:
                    title += " " + str(i)
                self.window.ui.tabs['output'].addTab(self.window.ui.notepad[i], title)

        self.window.ui.tabs['output'].currentChanged.connect(self.window.controller.ui.output_tab_changed)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.tabs['output'])
        layout.addLayout(self.setup_bottom())

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def setup_bottom(self) -> QHBoxLayout:
        """
        Setup bottom bar

        :return: QHBoxLayout
        :rtype: QHBoxLayout
        """
        self.window.ui.nodes['chat.label'] = QLabel("")
        self.window.ui.nodes['chat.label'].setAlignment(Qt.AlignRight)
        self.window.ui.nodes['chat.label'].setStyleSheet(self.window.controller.theme.get_style('text_faded'))
        self.window.ui.nodes['chat.label'].setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.window.ui.nodes['chat.model'] = QLabel("")
        self.window.ui.nodes['chat.model'].setAlignment(Qt.AlignRight)
        self.window.ui.nodes['chat.model'].setStyleSheet(self.window.controller.theme.get_style('text_faded'))
        self.window.ui.nodes['chat.model'].setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.window.ui.nodes['chat.plugins'] = QLabel("")
        self.window.ui.nodes['chat.plugins'].setAlignment(Qt.AlignRight)
        self.window.ui.nodes['chat.plugins'].setStyleSheet(self.window.controller.theme.get_style('text_faded'))
        self.window.ui.nodes['chat.plugins'].setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

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
        self.window.ui.nodes['inline.vision'].setContentsMargins(0, 0, 0, 0)

        # tokens info
        self.window.ui.nodes['prompt.context'] = QLabel("")
        self.window.ui.nodes['prompt.context'].setAlignment(Qt.AlignRight)
        self.window.ui.nodes['prompt.context'].setStyleSheet(self.window.controller.theme.get_style('text_faded'))
        self.window.ui.nodes['prompt.context'].setToolTip(trans('tip.tokens.ctx'))
        self.window.ui.nodes['prompt.context'].setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        # plugin audio output addon
        self.window.ui.plugin_addon['audio.output'] = AudioOutput(self.window)
        self.window.ui.plugin_addon['schedule'] = QLabel("")
        self.window.ui.plugin_addon['schedule'].setAlignment(Qt.AlignRight)
        self.window.ui.plugin_addon['schedule'].setStyleSheet(self.window.controller.theme.get_style('text_faded'))

        opts_layout = QHBoxLayout()
        # opts_layout.setSpacing(2)  #
        opts_layout.setContentsMargins(0, 0, 0, 0)
        opts_layout.addWidget(self.window.ui.nodes['output.timestamp'])
        opts_layout.addWidget(self.window.ui.nodes['output.raw'])
        opts_layout.addWidget(self.window.ui.nodes['inline.vision'])
        opts_layout.setAlignment(Qt.AlignLeft)

        layout = QHBoxLayout()
        layout.addLayout(opts_layout)
        # layout.addWidget(self.window.ui.plugin_addon['audio.output'])
        layout.addStretch(1)
        layout.addWidget(self.window.ui.plugin_addon['schedule'])
        layout.addWidget(QLabel(" "))
        layout.addWidget(self.window.ui.nodes['chat.plugins'])
        layout.addWidget(QLabel(" "))
        layout.addWidget(self.window.ui.nodes['chat.label'])
        layout.addWidget(QLabel("  "))
        layout.addWidget(self.window.ui.nodes['chat.model'])
        layout.addWidget(QLabel("  "))
        layout.addWidget(self.window.ui.nodes['prompt.context'])
        layout.setContentsMargins(0, 0, 0, 0)

        self.window.ui.nodes['chat.footer'] = QWidget()
        self.window.ui.nodes['chat.footer'].setLayout(layout)

        final_layout = QVBoxLayout()
        final_layout.addWidget(self.window.ui.nodes['chat.footer'])
        final_layout.setContentsMargins(0, 0, 0, 0)

        return final_layout
