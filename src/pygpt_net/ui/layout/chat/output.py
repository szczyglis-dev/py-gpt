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

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QCheckBox, QWidget, QSizePolicy

from pygpt_net.ui.layout.chat.input import Input
from pygpt_net.ui.layout.chat.calendar import Calendar
from pygpt_net.ui.layout.chat.painter import Painter
from pygpt_net.ui.widget.audio.output import AudioOutput
from pygpt_net.ui.widget.element.labels import ChatStatusLabel, IconLabel
from pygpt_net.ui.widget.tabs.output import OutputTabs
from pygpt_net.ui.widget.textarea.output import ChatOutput
from pygpt_net.ui.widget.filesystem.explorer import FileExplorer
from pygpt_net.utils import trans
import pygpt_net.icons_rc


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
        # chat plain-text output
        self.window.ui.nodes['output_plain'] = ChatOutput(self.window)

        # chat web output
        if self.window.core.config.get("render.engine") == "web":
            from pygpt_net.ui.widget.textarea.web import ChatWebOutput, CustomWebEnginePage
            self.window.ui.nodes['output'] = ChatWebOutput(self.window)
            self.window.ui.nodes['output'].setPage(
                CustomWebEnginePage(self.window, self.window.ui.nodes['output'])
            )
        else:
            # chat legacy output
            self.window.ui.nodes['output'] = ChatOutput(self.window)

        # disable at start
        self.window.ui.nodes['output_plain'].setVisible(False)
        self.window.ui.nodes['output'].setVisible(False)

        # index status data
        index_data = self.window.core.idx.get_idx_data()  # get all idx data

        # file explorer
        path = self.window.core.config.get_user_dir('data')
        self.window.ui.nodes['output_files'] = FileExplorer(self.window, path, index_data)

        # render engines layout
        output_layout = QVBoxLayout()
        output_layout.addWidget(self.window.ui.nodes['output_plain'])
        output_layout.addWidget(self.window.ui.nodes['output'])
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_widget = QWidget()
        output_widget.setLayout(output_layout)

        # tabs
        self.window.ui.tabs['output'] = OutputTabs(self.window)
        self.window.ui.tabs['output'].addTab(output_widget, trans('output.tab.chat'))
        self.window.ui.tabs['output'].addTab(self.window.ui.nodes['output_files'], trans('output.tab.files'))

        # calendar
        calendar = self.calendar.setup()
        self.window.ui.tabs['output'].addTab(calendar, trans('output.tab.calendar'))

        # painter
        painter = self.painter.setup()
        self.window.ui.tabs['output'].addTab(painter, trans('output.tab.painter'))

        self.window.ui.tabs['output'].currentChanged.connect(self.window.controller.ui.output_tab_changed)

        self.window.ui.tabs['output'].setTabIcon(0, QIcon(":/icons/chat.svg"))
        self.window.ui.tabs['output'].setTabIcon(1, QIcon(":/icons/folder_filled.svg"))
        self.window.ui.tabs['output'].setTabIcon(2, QIcon(":/icons/schedule.svg"))
        self.window.ui.tabs['output'].setTabIcon(3, QIcon(":/icons/brush.svg"))

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.tabs['output'])
        layout.addLayout(self.setup_bottom())

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def setup_bottom(self) -> QHBoxLayout:
        """
        Setup bottom status bar

        :return: QHBoxLayout
        :rtype: QHBoxLayout
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
        self.window.ui.nodes['icon.interpreter'].setToolTip("Python code interpreter")
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

        # edit icons
        self.window.ui.nodes['output.edit'] = QCheckBox(trans('output.edit'))
        self.window.ui.nodes['output.edit'].clicked.connect(
            lambda: self.window.controller.chat.common.toggle_edit_icons(
                self.window.ui.nodes['output.edit'].isChecked())
        )

        # inline vision
        self.window.ui.nodes['inline.vision'] = QCheckBox(trans('inline.vision'))
        self.window.ui.nodes['inline.vision'].clicked.connect(
            lambda: self.window.controller.chat.vision.toggle(
                self.window.ui.nodes['inline.vision'].isChecked())
        )
        self.window.ui.nodes['inline.vision'].setVisible(False)
        self.window.ui.nodes['inline.vision'].setContentsMargins(0, 0, 0, 0)
        self.window.ui.nodes['inline.vision'].setToolTip(trans('vision.checkbox.tooltip'))

        # tokens
        self.window.ui.nodes['prompt.context'] = ChatStatusLabel("")
        self.window.ui.nodes['prompt.context'].setToolTip(trans('tip.tokens.ctx'))
        self.window.ui.nodes['prompt.context'].setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        # plugin audio output addon
        self.window.ui.plugin_addon['audio.output'] = AudioOutput(self.window)

        # schedule
        self.window.ui.plugin_addon['schedule'] = ChatStatusLabel("")

        opts_layout = QHBoxLayout()
        # opts_layout.setSpacing(2)  #
        opts_layout.setContentsMargins(0, 0, 0, 0)
        opts_layout.addWidget(self.window.ui.nodes['output.timestamp'])
        opts_layout.addWidget(self.window.ui.nodes['output.edit'])
        opts_layout.addWidget(self.window.ui.nodes['output.raw'])
        opts_layout.addWidget(self.window.ui.nodes['inline.vision'])
        opts_layout.setAlignment(Qt.AlignLeft)

        layout = QHBoxLayout()
        layout.addLayout(opts_layout)
        # layout.addWidget(self.window.ui.plugin_addon['audio.output'])
        layout.addStretch(1)
        layout.addWidget(self.window.ui.nodes['icon.video.capture'])
        layout.addWidget(self.window.ui.nodes['icon.audio.input'])
        layout.addWidget(self.window.ui.nodes['icon.audio.output'])
        layout.addWidget(self.window.ui.nodes['icon.interpreter'])
        layout.addWidget(self.window.ui.nodes['icon.indexer'])
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
