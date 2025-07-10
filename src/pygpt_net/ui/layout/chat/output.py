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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QCheckBox, QWidget, QSizePolicy, QPushButton, \
    QGridLayout, QWidgetItem, QLayout

from pygpt_net.ui.widget.audio.output import AudioOutput
from pygpt_net.ui.widget.element.labels import ChatStatusLabel, IconLabel, HelpLabel
from pygpt_net.ui.widget.anims.loader import Loading
from pygpt_net.ui.widget.tabs.layout import OutputLayout

from .explorer import Explorer
from .input import Input
from .calendar import Calendar
from .painter import Painter

from pygpt_net.utils import trans
import pygpt_net.icons_rc



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
        # prepare columns
        self.window.ui.layout = OutputLayout(self.window)

        # create empty containers for chat output
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
        # video capture icon
        self.window.ui.nodes['icon.video.capture'] = IconLabel(":/icons/webcam.svg")
        self.window.ui.nodes['icon.video.capture'].setToolTip(trans("icon.video.capture"))
        self.window.ui.nodes['icon.video.capture'].clicked.connect(
            lambda:self.window.controller.camera.toggle_capture()
        )

        # audio output icon
        self.window.ui.nodes['icon.audio.output'] = IconLabel(":/icons/volume.svg")
        self.window.ui.nodes['icon.audio.output'].setToolTip(trans("icon.audio.output"))
        self.window.ui.nodes['icon.audio.output'].clicked.connect(
            lambda: self.window.controller.plugins.toggle('audio_output')
        )

        # audio input icon
        self.window.ui.nodes['icon.audio.input'] = IconLabel(":/icons/mic.svg")
        self.window.ui.nodes['icon.audio.input'].setToolTip(trans("icon.audio.input"))
        self.window.ui.nodes['icon.audio.input'].clicked.connect(
            lambda: self.window.controller.plugins.toggle('audio_input')
        )

        # interpreter icon
        self.window.ui.nodes['icon.interpreter'] = IconLabel(":/icons/code.svg")
        self.window.ui.nodes['icon.interpreter'].setToolTip("Python Code Interpreter")
        self.window.ui.nodes['icon.interpreter'].clicked.connect(
            lambda: self.window.tools.get("interpreter").toggle()
        )

        # indexer icon
        self.window.ui.nodes['icon.indexer'] = IconLabel(":/icons/db.svg")
        self.window.ui.nodes['icon.indexer'].setToolTip("Indexer")
        self.window.ui.nodes['icon.indexer'].clicked.connect(
            lambda: self.window.tools.get("indexer").toggle()
        )

        # mode
        self.window.ui.nodes['chat.label'] = ChatStatusLabel("")
        self.window.ui.nodes['chat.label'].setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.window.ui.nodes['chat.label'].setWordWrap(False)

        # model
        self.window.ui.nodes['chat.model'] = ChatStatusLabel("")
        self.window.ui.nodes['chat.model'].setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.window.ui.nodes['chat.model'].setWordWrap(False)

        # plugins
        self.window.ui.nodes['chat.plugins'] = ChatStatusLabel("")
        self.window.ui.nodes['chat.plugins'].setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        # timestamp
        self.window.ui.nodes['output.timestamp'] = QCheckBox(trans('output.timestamp'))
        self.window.ui.nodes['output.timestamp'].stateChanged.connect(
            lambda: self.window.controller.chat.common.toggle_timestamp(
                self.window.ui.nodes['output.timestamp'].isChecked())
        )

        # plain text
        self.window.ui.nodes['output.raw'] = QCheckBox(trans('output.raw'))
        self.window.ui.nodes['output.raw'].clicked.connect(
            lambda: self.window.controller.chat.common.toggle_raw(
                self.window.ui.nodes['output.raw'].isChecked())
        )

        """
        # edit icons
        self.window.ui.nodes['output.edit'] = QCheckBox(trans('output.edit'))
        self.window.ui.nodes['output.edit'].clicked.connect(
            lambda: self.window.controller.chat.common.toggle_edit_icons(
                self.window.ui.nodes['output.edit'].isChecked())
        )
        """

        # tokens
        self.window.ui.nodes['prompt.context'] = ChatStatusLabel("")
        self.window.ui.nodes['prompt.context'].setToolTip(trans('tip.tokens.ctx'))
        self.window.ui.nodes['prompt.context'].setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.window.ui.nodes['input.counter'] = ChatStatusLabel("")
        self.window.ui.nodes['input.counter'].setToolTip(trans('tip.tokens.input'))
        self.window.ui.nodes['input.counter'].setWordWrap(False)

        # plugin audio output addon
        self.window.ui.plugin_addon['audio.output'] = AudioOutput(self.window)

        # schedule
        self.window.ui.plugin_addon['schedule'] = ChatStatusLabel("")

        # inline vision
        self.window.ui.nodes['inline.vision'] = HelpLabel(trans('inline.vision'))
        self.window.ui.nodes['inline.vision'].setVisible(False)
        self.window.ui.nodes['inline.vision'].setContentsMargins(0, 0, 0, 0)

        opts_layout = QHBoxLayout()
        # opts_layout.setSpacing(2)  #
        opts_layout.setContentsMargins(0, 0, 0, 0)
        opts_layout.addWidget(self.window.ui.nodes['output.raw'])
        opts_layout.addWidget(self.window.ui.nodes['output.timestamp'])
        # opts_layout.addWidget(self.window.ui.nodes['output.edit'])
        
        opts_layout.addWidget(self.window.ui.nodes['inline.vision'])
        opts_layout.setAlignment(Qt.AlignLeft)

        left_layout = QHBoxLayout()
        left_layout.addLayout(opts_layout)
        left_layout.setContentsMargins(0, 0, 0, 0)

        right_layout = QHBoxLayout()
        right_layout.addWidget(self.window.ui.nodes['icon.video.capture'])
        right_layout.addWidget(self.window.ui.nodes['icon.audio.input'])
        right_layout.addWidget(self.window.ui.nodes['icon.audio.output'])
        right_layout.addWidget(self.window.ui.nodes['icon.interpreter'])
        right_layout.addWidget(self.window.ui.nodes['icon.indexer'])
        right_layout.addWidget(self.window.ui.plugin_addon['schedule'])
        right_layout.addWidget(QLabel(" "))
        right_layout.addWidget(self.window.ui.nodes['chat.plugins'])
        right_layout.addWidget(QLabel(" "))
        right_layout.addWidget(self.window.ui.nodes['chat.label'])
        right_layout.addWidget(QLabel("  "))
        right_layout.addWidget(self.window.ui.nodes['chat.model'])
        right_layout.addWidget(QLabel("  "))
        right_layout.addWidget(self.window.ui.nodes['prompt.context'])
        right_layout.addWidget(QLabel("  "))
        right_layout.addWidget(self.window.ui.nodes['input.counter'])
        right_layout.setContentsMargins(0, 8, 20, 0)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        self.window.ui.nodes['anim.loading'] = Loading()
        self.window.ui.nodes['anim.loading'].hide()

        grid = QGridLayout()

        left_layout = QHBoxLayout()
        left_layout.addWidget(left_widget)
        #left_layout.addStretch(1)
        left_layout.setContentsMargins(0, 0, 0, 0)

        center_layout = QHBoxLayout()
        #center_layout.addStretch()
        center_layout.addWidget(self.window.ui.nodes['anim.loading'])
        center_layout.addStretch()
        center_layout.setContentsMargins(20, 0, 0, 0)

        right_layout = QHBoxLayout()
        right_layout.addStretch(1)
        right_layout.addWidget(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        grid.addLayout(left_layout, 0, 0)
        grid.addLayout(center_layout, 0, 1, alignment=Qt.AlignCenter)
        grid.addLayout(right_layout, 0, 2, alignment=Qt.AlignRight)
        grid.setContentsMargins(0, 0, 0, 0)

        self.window.ui.nodes['chat.footer'] = QWidget()
        self.window.ui.nodes['chat.footer'].setLayout(grid)

        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(self.window.ui.nodes['chat.footer'])
        bottom_layout.setContentsMargins(2, 0, 2, 0)
        return bottom_layout

    def set_fixed_size_policy(self, layout):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if isinstance(item, QWidgetItem):
                widget = item.widget()
                if widget:
                    widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            elif isinstance(item, QLayout):
                self.set_fixed_size_policy(item)