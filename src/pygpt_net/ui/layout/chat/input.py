#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.31 16:00:00                  #
# ================================================== #

from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QRadioButton, QCheckBox, QWidget, \
    QGridLayout

from pygpt_net.ui.layout.chat.attachments import Attachments
from pygpt_net.ui.layout.chat.attachments_uploaded import AttachmentsUploaded
from pygpt_net.ui.layout.chat.attachments_ctx import AttachmentsCtx
from pygpt_net.ui.layout.status import Status
from pygpt_net.ui.widget.audio.bar import OutputBar
from pygpt_net.ui.widget.audio.input import AudioInput
from pygpt_net.ui.widget.audio.input_button import AudioInputButton
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.tabs.Input import InputTabs
from pygpt_net.ui.widget.textarea.input import ChatInput
from pygpt_net.ui.widget.textarea.input_extra import ExtraInput
from pygpt_net.utils import trans


class Input:
    def __init__(self, window=None):
        """
        Input UI

        :param window: Window instance
        """
        self.window = window
        self.status = Status(window)
        self.attachments = Attachments(window)
        self.attachments_uploaded = AttachmentsUploaded(window)
        self.attachments_ctx = AttachmentsCtx(window)

        # min height
        self.min_height_files_tab = 120
        self.min_height_input_tab = 80
        self.min_height_input = 50
        self.prev_input_splitter_value = 0

    def setup(self) -> QWidget:
        """
        Setup input

        :return: QWidget
        """
        input = self.setup_input()
        input_extra = self.setup_input_extra()
        files = self.setup_attachments()
        files_uploaded = self.setup_attachments_uploaded()
        files_ctx = self.setup_attachments_ctx()

        self.window.ui.tabs['input'] = InputTabs(self.window)
        tabs = self.window.ui.tabs['input']
        tabs.setMinimumHeight(self.min_height_input_tab)
        tabs.addTab(input, trans('input.tab'))
        tabs.addTab(files, trans('attachments.tab'))
        tabs.addTab(files_uploaded, trans('attachments_uploaded.tab'))
        tabs.addTab(files_ctx, trans('attachments_uploaded.tab'))
        tabs.addTab(input_extra, trans('input.tab.extra'))
        tabs.currentChanged.connect(self.update_min_height)

        tabs.setTabIcon(0, QIcon(":/icons/input.svg"))
        upload_icon = QIcon(":/icons/upload.svg")
        tabs.setTabIcon(1, QIcon(":/icons/attachment.svg"))
        tabs.setTabIcon(2, upload_icon)
        tabs.setTabIcon(3, upload_icon)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addLayout(self.setup_header())
        layout.addWidget(tabs)
        layout.addLayout(self.setup_bottom())
        layout.setContentsMargins(0, 0, 0, 5)
        return widget

    def setup_input(self) -> QWidget:
        """
        Setup input tab

        :return: QWidget
        """
        self.window.ui.nodes['input'] = ChatInput(self.window)
        self.window.ui.nodes['input'].setMinimumHeight(self.min_height_input)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self.window.ui.nodes['input'])
        layout.setContentsMargins(0, 0, 0, 0)
        return widget

    def setup_input_extra(self) -> QWidget:
        """
        Setup input tab (extra)

        :return: QWidget
        """
        self.window.ui.nodes['input_extra'] = ExtraInput(self.window)
        self.window.ui.nodes['input_extra'].setMinimumHeight(self.min_height_input)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self.window.ui.nodes['input_extra'])
        layout.setContentsMargins(0, 0, 0, 0)
        return widget

    def setup_attachments(self) -> QWidget:
        """
        Setup attachments

        :return: QWidget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addLayout(self.attachments.setup())
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setMinimumHeight(self.min_height_files_tab)
        return widget

    def setup_attachments_uploaded(self) -> QWidget:
        """
        Setup attachments uploaded

        :return: QWidget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addLayout(self.attachments_uploaded.setup())
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setMinimumHeight(self.min_height_files_tab)
        return widget

    def setup_attachments_ctx(self) -> QWidget:
        """
        Setup attachments ctx

        :return: QWidget
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addLayout(self.attachments_ctx.setup())
        layout.setContentsMargins(0, 0, 0, 0)
        widget.setMinimumHeight(self.min_height_files_tab)
        return widget

    def setup_header(self) -> QHBoxLayout:
        """
        Setup input header

        :return: QHBoxLayout
        """
        # header (input label + input counter)
        self.window.ui.nodes['input.label'] = HelpLabel(trans("input.label"))

        # plugin audio input addon
        self.window.ui.plugin_addon['audio.input'] = AudioInput(self.window)
        self.window.ui.plugin_addon['audio.input.btn'] = AudioInputButton(self.window)

        self.window.ui.plugin_addon['audio.input'].setVisible(False)
        self.window.ui.plugin_addon['audio.input.btn'].setVisible(False)

        grid = QGridLayout()

        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(self.window.ui.plugin_addon['audio.input'])
        center_layout.addWidget(self.window.ui.plugin_addon['audio.input.btn'])
        center_layout.addStretch()
        grid.addLayout(center_layout, 0, 1, alignment=Qt.AlignCenter)

        grid.setContentsMargins(0, 0, 0, 0)
        return grid

    def setup_bottom(self) -> QHBoxLayout:
        """
        Setup input bottom

        :return: QHBoxLayout
        """
        self.window.ui.plugin_addon['audio.output.bar'] = OutputBar(self.window)
        layout = QHBoxLayout()
        layout.addLayout(self.status.setup())
        layout.addWidget(self.window.ui.plugin_addon['audio.output.bar'], alignment=Qt.AlignCenter)
        layout.addLayout(self.setup_buttons())
        layout.setContentsMargins(2, 0, 2, 0)
        return layout

    def setup_buttons(self) -> QHBoxLayout:
        """
        Setup input buttons

        :return: QHBoxLayout
        """
        nodes = self.window.ui.nodes
        controller = self.window.controller

        nodes['input.send_enter'] = QRadioButton(trans("input.radio.enter"))
        nodes['input.send_enter'].toggled.connect(partial(self._on_send_mode_toggled, 1))

        nodes['input.send_shift_enter'] = QRadioButton(trans("input.radio.enter_shift"))
        nodes['input.send_shift_enter'].toggled.connect(partial(self._on_send_mode_toggled, 2))

        nodes['input.send_none'] = QRadioButton(trans("input.radio.none"))
        nodes['input.send_none'].toggled.connect(partial(self._on_send_mode_toggled, 0))

        nodes['input.send_clear'] = QCheckBox(trans('input.send_clear'))
        nodes['input.send_clear'].toggled.connect(controller.chat.common.toggle_send_clear)

        nodes['input.stream'] = QCheckBox(trans('input.stream'))
        nodes['input.stream'].toggled.connect(controller.chat.common.toggle_stream)

        nodes['input.send_btn'] = QPushButton(trans("input.btn.send"))
        nodes['input.send_btn'].clicked.connect(controller.chat.input.send_input)

        nodes['input.stop_btn'] = QPushButton(trans("input.btn.stop"))
        nodes['input.stop_btn'].setVisible(False)
        nodes['input.stop_btn'].clicked.connect(controller.chat.common.handle_stop)

        nodes['input.update_btn'] = QPushButton(trans("input.btn.update"))
        nodes['input.update_btn'].setVisible(False)
        nodes['input.update_btn'].clicked.connect(controller.ctx.extra.edit_submit)

        nodes['input.cancel_btn'] = QPushButton(trans("input.btn.cancel"))
        nodes['input.cancel_btn'].setVisible(False)
        nodes['input.cancel_btn'].clicked.connect(controller.ctx.extra.edit_cancel)

        nodes['ui.input.buttons'] = QHBoxLayout()
        nodes['ui.input.buttons'].addWidget(nodes['input.stream'])
        nodes['ui.input.buttons'].addWidget(nodes['input.send_clear'])
        nodes['ui.input.buttons'].addWidget(nodes['input.send_enter'])
        nodes['ui.input.buttons'].addWidget(nodes['input.send_shift_enter'])
        nodes['ui.input.buttons'].addWidget(nodes['input.send_none'])
        nodes['ui.input.buttons'].addWidget(nodes['input.send_btn'])
        nodes['ui.input.buttons'].addWidget(nodes['input.stop_btn'])
        nodes['ui.input.buttons'].addWidget(nodes['input.cancel_btn'])
        nodes['ui.input.buttons'].addWidget(nodes['input.update_btn'])
        nodes['ui.input.buttons'].setAlignment(Qt.AlignRight)

        return nodes['ui.input.buttons']

    def _on_send_mode_toggled(self, mode: int, checked: bool):
        if checked:
            self.window.controller.chat.common.toggle_send_shift(mode)

    def update_min_height(self):
        """
        Update the minimum height of the input tab
        """
        tabs = self.window.ui.tabs['input']
        nodes = self.window.ui.nodes
        splitters = self.window.ui.splitters
        controller_ui = self.window.controller.ui

        idx = tabs.currentIndex()
        if idx == 0 or idx == 4:
            # nodes['input'].setMinimumHeight(self.min_height_input)
            tabs.setMinimumHeight(self.min_height_input_tab)
            sizes = controller_ui.splitter_output_size_input
            if sizes and sizes != [0, 0]:
                splitters['main.output'].setSizes(sizes)
        else:
            sizes = controller_ui.splitter_output_size_files
            if sizes and controller_ui.splitter_output_size_input != [0, 0]:
                splitters['main.output'].setSizes(sizes)
            # nodes['input'].setMinimumHeight(self.min_height_files_tab)
            tabs.setMinimumHeight(self.min_height_files_tab + 90)