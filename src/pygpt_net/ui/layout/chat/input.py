#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.18 03:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QRadioButton, QCheckBox, QWidget, \
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
from pygpt_net.utils import trans
import pygpt_net.icons_rc


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

    def setup(self) -> QWidget:
        """
        Setup input

        :return: QWidget
        """
        input = self.setup_input()
        files = self.setup_attachments()
        files_uploaded = self.setup_attachments_uploaded()
        files_ctx = self.setup_attachments_ctx()

        # tabs
        self.window.ui.tabs['input'] = InputTabs(self.window)
        self.window.ui.tabs['input'].setMinimumHeight(self.min_height_input_tab)
        self.window.ui.tabs['input'].addTab(input, trans('input.tab'))
        self.window.ui.tabs['input'].addTab(files, trans('attachments.tab'))
        self.window.ui.tabs['input'].addTab(files_uploaded, trans('attachments_uploaded.tab'))
        self.window.ui.tabs['input'].addTab(files_ctx, trans('attachments_uploaded.tab'))
        self.window.ui.tabs['input'].currentChanged.connect(self.update_min_height)  # update min height on tab change

        self.window.ui.tabs['input'].setTabIcon(0, QIcon(":/icons/input.svg"))
        self.window.ui.tabs['input'].setTabIcon(1, QIcon(":/icons/attachment.svg"))
        self.window.ui.tabs['input'].setTabIcon(2, QIcon(":/icons/upload.svg"))
        self.window.ui.tabs['input'].setTabIcon(3, QIcon(":/icons/upload.svg"))

        # layout
        layout = QVBoxLayout()
        layout.addLayout(self.setup_header())
        layout.addWidget(self.window.ui.tabs['input'])
        layout.addLayout(self.setup_bottom())
        layout.setContentsMargins(0, 0, 0, 5)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def setup_input(self) -> QWidget:
        """
        Setup input tab

        :return: QWidget
        """
        # input textarea
        self.window.ui.nodes['input'] = ChatInput(self.window)
        self.window.ui.nodes['input'].setMinimumHeight(self.min_height_input)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['input'])
        layout.setContentsMargins(0, 0, 0, 0)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def setup_attachments(self) -> QWidget:
        """
        Setup attachments

        :return: QWidget
        """
        layout = QVBoxLayout()
        layout.addLayout(self.attachments.setup())
        layout.setContentsMargins(0, 0, 0, 0)

        widget = QWidget()
        widget.setLayout(layout)
        widget.setMinimumHeight(self.min_height_files_tab)
        return widget

    def setup_attachments_uploaded(self) -> QWidget:
        """
        Setup attachments uploaded

        :return: QWidget
        """
        layout = QVBoxLayout()
        layout.addLayout(self.attachments_uploaded.setup())
        layout.setContentsMargins(0, 0, 0, 0)

        widget = QWidget()
        widget.setLayout(layout)
        widget.setMinimumHeight(self.min_height_files_tab)
        return widget

    def setup_attachments_ctx(self) -> QWidget:
        """
        Setup attachments ctx

        :return: QWidget
        """
        layout = QVBoxLayout()
        layout.addLayout(self.attachments_ctx.setup())
        layout.setContentsMargins(0, 0, 0, 0)

        widget = QWidget()
        widget.setLayout(layout)
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
        # send with: enter
        self.window.ui.nodes['input.send_enter'] = QRadioButton(trans("input.radio.enter"))
        self.window.ui.nodes['input.send_enter'].clicked.connect(
            lambda: self.window.controller.chat.common.toggle_send_shift(
                1))

        # send with: shift + enter
        self.window.ui.nodes['input.send_shift_enter'] = QRadioButton(trans("input.radio.enter_shift"))
        self.window.ui.nodes['input.send_shift_enter'].clicked.connect(
            lambda: self.window.controller.chat.common.toggle_send_shift(
                2))

        # send with: none
        self.window.ui.nodes['input.send_none'] = QRadioButton(trans("input.radio.none"))
        self.window.ui.nodes['input.send_none'].clicked.connect(
            lambda: self.window.controller.chat.common.toggle_send_shift(
                0))

        # send clear
        self.window.ui.nodes['input.send_clear'] = QCheckBox(trans('input.send_clear'))
        self.window.ui.nodes['input.send_clear'].stateChanged.connect(
            lambda: self.window.controller.chat.common.toggle_send_clear(
                self.window.ui.nodes['input.send_clear'].isChecked()))

        # stream
        self.window.ui.nodes['input.stream'] = QCheckBox(trans('input.stream'))
        self.window.ui.nodes['input.stream'].stateChanged.connect(
            lambda: self.window.controller.chat.common.toggle_stream(self.window.ui.nodes['input.stream'].isChecked()))

        # send button
        self.window.ui.nodes['input.send_btn'] = QPushButton(trans("input.btn.send"))
        self.window.ui.nodes['input.send_btn'].clicked.connect(
            lambda: self.window.controller.chat.input.send_input())

        # stop button
        self.window.ui.nodes['input.stop_btn'] = QPushButton(trans("input.btn.stop"))
        self.window.ui.nodes['input.stop_btn'].setVisible(False)
        self.window.ui.nodes['input.stop_btn'].clicked.connect(
            lambda: self.window.controller.kernel.stop())

        # update button
        self.window.ui.nodes['input.update_btn'] = QPushButton(trans("input.btn.update"))
        self.window.ui.nodes['input.update_btn'].setVisible(False)
        self.window.ui.nodes['input.update_btn'].clicked.connect(
            lambda: self.window.controller.ctx.extra.edit_submit())

        # cancel button
        self.window.ui.nodes['input.cancel_btn'] = QPushButton(trans("input.btn.cancel"))
        self.window.ui.nodes['input.cancel_btn'].setVisible(False)
        self.window.ui.nodes['input.cancel_btn'].clicked.connect(
            lambda: self.window.controller.ctx.extra.edit_cancel())

        # layout
        self.window.ui.nodes['ui.input.buttons'] = QHBoxLayout()
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.stream'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_clear'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_enter'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_shift_enter'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_none'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_btn'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.stop_btn'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.cancel_btn'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.update_btn'])
        self.window.ui.nodes['ui.input.buttons'].setAlignment(Qt.AlignRight)

        return self.window.ui.nodes['ui.input.buttons']

    def update_min_height(self):
        """
        Update the minimum height of the input tab
        """
        idx = self.window.ui.tabs['input'].currentIndex()
        if idx == 0:
            self.window.ui.nodes['input'].setMinimumHeight(self.min_height_input)
            self.window.ui.tabs['input'].setMinimumHeight(self.min_height_input_tab)
        else:
            self.window.ui.nodes['input'].setMinimumHeight(self.min_height_files_tab)
            self.window.ui.tabs['input'].setMinimumHeight(self.min_height_files_tab + 60)
