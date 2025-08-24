#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QCheckBox, QWidget, QSizePolicy, \
    QGridLayout

from pygpt_net.ui.widget.audio.output import AudioOutput
from pygpt_net.ui.widget.element.labels import ChatStatusLabel, IconLabel, HelpLabel
from pygpt_net.ui.widget.tabs.layout import OutputLayout
from pygpt_net.utils import trans

from .explorer import Explorer
from .input import Input
from .calendar import Calendar
from .painter import Painter

class Output:
    def __init__(self, window=None):
        """
        Chat output UI

        :param window: Window instance
        """
        self.window = window
        self.explorer = Explorer(window)
        self.input = Input(window)
        self.calendar = Calendar(window)
        self.painter = Painter(window)

    def setup(self) -> QWidget:
        """
        Setup output

        :return: QWidget
        """
        self.window.ui.layout = OutputLayout(self.window)
        self.window.ui.nodes['output'] = {}
        self.window.ui.nodes['output_plain'] = {}

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.layout)
        layout.addLayout(self.setup_bottom())
        layout.setContentsMargins(0, 5, 0, 0)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def setup_bottom(self) -> QHBoxLayout:
        """
        Setup bottom status bar

        :return: QHBoxLayout
        """
        nodes = self.window.ui.nodes
        plugin_addon = self.window.ui.plugin_addon
        ctrl = self.window.controller
        tools = self.window.tools

        nodes['icon.video.capture'] = IconLabel(":/icons/webcam.svg", window=self.window)
        nodes['icon.video.capture'].setToolTip(trans("icon.video.capture"))
        nodes['icon.video.capture'].clicked.connect(lambda: ctrl.camera.toggle_capture())

        nodes['icon.audio.output'] = IconLabel(":/icons/volume.svg", window=self.window)
        nodes['icon.audio.output'].setToolTip(trans("icon.audio.output"))
        nodes['icon.audio.output'].clicked.connect(lambda: ctrl.plugins.toggle('audio_output'))

        nodes['icon.audio.input'] = IconLabel(":/icons/mic.svg", window=self.window)
        nodes['icon.audio.input'].setToolTip(trans("icon.audio.input"))
        nodes['icon.audio.input'].clicked.connect(lambda: ctrl.plugins.toggle('audio_input'))

        nodes['icon.interpreter'] = IconLabel(":/icons/code.svg", window=self.window)
        nodes['icon.interpreter'].setToolTip("Python Code Interpreter")
        nodes['icon.interpreter'].clicked.connect(lambda: tools.get("interpreter").toggle())

        nodes['icon.indexer'] = IconLabel(":/icons/db.svg", window=self.window)
        nodes['icon.indexer'].setToolTip("Indexer")
        nodes['icon.indexer'].clicked.connect(lambda: tools.get("indexer").toggle())

        min_policy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        nodes['chat.label'] = ChatStatusLabel("")
        nodes['chat.label'].setSizePolicy(min_policy)
        nodes['chat.label'].setWordWrap(False)

        nodes['chat.model'] = ChatStatusLabel("")
        nodes['chat.model'].setSizePolicy(min_policy)
        nodes['chat.model'].setWordWrap(False)

        nodes['chat.plugins'] = ChatStatusLabel("")
        nodes['chat.plugins'].setSizePolicy(min_policy)

        nodes['output.timestamp'] = QCheckBox(trans('output.timestamp'))
        nodes['output.timestamp'].toggled.connect(ctrl.chat.common.toggle_timestamp)

        nodes['output.raw'] = QCheckBox(trans('output.raw'))
        nodes['output.raw'].toggled.connect(ctrl.chat.common.toggle_raw)

        nodes['prompt.context'] = ChatStatusLabel("")
        nodes['prompt.context'].setToolTip(trans('tip.tokens.ctx'))
        nodes['prompt.context'].setSizePolicy(min_policy)

        nodes['input.counter'] = ChatStatusLabel("")
        nodes['input.counter'].setToolTip(trans('tip.tokens.input'))
        nodes['input.counter'].setWordWrap(False)

        plugin_addon['audio.output'] = AudioOutput(self.window)
        plugin_addon['schedule'] = ChatStatusLabel("")

        nodes['inline.vision'] = HelpLabel(trans('inline.vision'))
        nodes['inline.vision'].setVisible(False)
        nodes['inline.vision'].setContentsMargins(0, 0, 0, 0)

        opts_layout = QHBoxLayout()
        opts_layout.setContentsMargins(0, 0, 0, 0)
        opts_layout.addWidget(nodes['output.raw'])
        opts_layout.addWidget(nodes['output.timestamp'])
        opts_layout.addWidget(nodes['inline.vision'])
        opts_layout.setAlignment(Qt.AlignLeft)

        left_bar_layout = QHBoxLayout()
        left_bar_layout.addLayout(opts_layout)
        left_bar_layout.setContentsMargins(0, 0, 0, 0)

        nodes['anim.loading'] = QWidget()
        nodes['anim.loading'].hide()

        right_bar_layout = QHBoxLayout()
        right_bar_layout.addWidget(nodes['icon.video.capture'])
        right_bar_layout.addWidget(nodes['icon.audio.input'])
        right_bar_layout.addWidget(nodes['icon.audio.output'])
        right_bar_layout.addWidget(nodes['icon.interpreter'])
        right_bar_layout.addWidget(nodes['icon.indexer'])
        right_bar_layout.addWidget(plugin_addon['schedule'])
        right_bar_layout.addSpacing(6)
        right_bar_layout.addWidget(nodes['chat.plugins'])
        right_bar_layout.addSpacing(6)
        right_bar_layout.addWidget(nodes['chat.label'])
        right_bar_layout.addSpacing(12)
        right_bar_layout.addWidget(nodes['chat.model'])
        right_bar_layout.addSpacing(12)
        right_bar_layout.addWidget(nodes['prompt.context'])
        right_bar_layout.addSpacing(12)
        right_bar_layout.addWidget(nodes['input.counter'])
        right_bar_layout.setContentsMargins(0, 8, 20, 0)

        grid = QGridLayout()
        grid.addLayout(left_bar_layout, 0, 0)
        grid.addWidget(nodes['anim.loading'], 0, 1, alignment=Qt.AlignCenter)
        grid.addLayout(right_bar_layout, 0, 2, alignment=Qt.AlignRight)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 0)
        grid.setContentsMargins(0, 0, 0, 0)

        nodes['chat.footer'] = QWidget()
        nodes['chat.footer'].setLayout(grid)

        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(nodes['chat.footer'])
        bottom_layout.setContentsMargins(2, 0, 2, 0)
        return bottom_layout

    def set_fixed_size_policy(self, layout):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            w = item.widget()
            if w is not None:
                w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            else:
                l = item.layout()
                if l is not None:
                    self.set_fixed_size_policy(l)