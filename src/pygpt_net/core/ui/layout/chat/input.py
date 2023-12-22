#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 19:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QRadioButton, QCheckBox, \
    QTabWidget, QWidget

from .attachments import Attachments
from .attachments_uploaded import AttachmentsUploaded
from ..status import Status
from ...widget.audio.input import AudioInput
from ...widget.textarea.input import ChatInput
from ....utils import trans


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

        # min heights
        self.min_height_files_tab = 120
        self.min_height_input_tab = 80

    def setup(self):
        """
        Setup input

        :return: QWidget
        :rtype: QWidget
        """
        input = self.setup_input()
        files = self.setup_attachments()
        files_uploaded = self.setup_attachments_uploaded()

        # tabs
        self.window.ui.tabs['input'] = QTabWidget()
        self.window.ui.tabs['input'].setMinimumHeight(self.min_height_input_tab)
        self.window.ui.tabs['input'].addTab(input, trans('input.tab'))
        self.window.ui.tabs['input'].addTab(files, trans('attachments.tab'))
        self.window.ui.tabs['input'].addTab(files_uploaded, trans('attachments_uploaded.tab'))
        self.window.ui.tabs['input'].currentChanged.connect(self.update_min_height)

        # layout
        layout = QVBoxLayout()
        layout.addLayout(self.setup_header())
        layout.addWidget(self.window.ui.tabs['input'])
        layout.addLayout(self.setup_bottom())

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def setup_input(self):
        """
        Setup input tab

        :return: QWidget
        :rtype: QWidget
        """
        # input textarea
        self.window.ui.nodes['input'] = ChatInput(self.window)
        self.window.ui.nodes['input'].setMinimumHeight(50)

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['input'])
        layout.setContentsMargins(0, 0, 0, 0)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def setup_attachments(self):
        """
        Setup attachments tab

        :return: QWidget
        :rtype: QWidget
        """
        layout = QVBoxLayout()
        layout.addLayout(self.attachments.setup())

        widget = QWidget()
        widget.setLayout(layout)
        widget.setMinimumHeight(self.min_height_files_tab)
        return widget

    def setup_attachments_uploaded(self):
        """
        Setup attachments uploaded tab

        :return: QWidget
        :rtype: QWidget
        """
        layout = QVBoxLayout()
        layout.addLayout(self.attachments_uploaded.setup())

        widget = QWidget()
        widget.setLayout(layout)
        widget.setMinimumHeight(self.min_height_files_tab)
        return widget

    def setup_header(self):
        """
        Setup input header

        :return: QHBoxLayout
        :rtype: QHBoxLayout
        """
        # header (input label + input counter)
        self.window.ui.nodes['input.label'] = QLabel(trans("input.label"))
        self.window.ui.nodes['input.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        self.window.ui.nodes['input.counter'] = QLabel("")

        # plugin audio input addon
        self.window.ui.plugin_addon['audio.input'] = AudioInput(self.window)

        header = QHBoxLayout()
        header.addWidget(self.window.ui.nodes['input.label'])
        header.addWidget(self.window.ui.plugin_addon['audio.input'])
        header.addWidget(self.window.ui.nodes['input.counter'], alignment=Qt.AlignRight)

        return header

    def setup_bottom(self):
        """
        Setup input bottom

        :return: QHBoxLayout
        :rtype: QHBoxLayout
        """
        layout = QHBoxLayout()
        layout.addLayout(self.status.setup())
        layout.addLayout(self.setup_buttons())

        return layout

    def setup_buttons(self):
        """
        Setup input buttons

        :return: QHBoxLayout
        :rtype: QHBoxLayout
        """
        # send with: enter
        self.window.ui.nodes['input.send_enter'] = QRadioButton(trans("input.radio.enter"))
        self.window.ui.nodes['input.send_enter'].clicked.connect(
            lambda: self.window.controller.input.toggle_send_shift(
                1))

        # send with: shift + enter
        self.window.ui.nodes['input.send_shift_enter'] = QRadioButton(trans("input.radio.enter_shift"))
        self.window.ui.nodes['input.send_shift_enter'].clicked.connect(
            lambda: self.window.controller.input.toggle_send_shift(
                2))

        # send with: none
        self.window.ui.nodes['input.send_none'] = QRadioButton(trans("input.radio.none"))
        self.window.ui.nodes['input.send_none'].clicked.connect(
            lambda: self.window.controller.input.toggle_send_shift(
                0))

        # send clear
        self.window.ui.nodes['input.send_clear'] = QCheckBox(trans('input.send_clear'))
        self.window.ui.nodes['input.send_clear'].stateChanged.connect(
            lambda: self.window.controller.input.toggle_send_clear(
                self.window.ui.nodes['input.send_clear'].isChecked()))

        # stream
        self.window.ui.nodes['input.stream'] = QCheckBox(trans('input.stream'))
        self.window.ui.nodes['input.stream'].stateChanged.connect(
            lambda: self.window.controller.input.toggle_stream(self.window.ui.nodes['input.stream'].isChecked()))

        # send button
        self.window.ui.nodes['input.send_btn'] = QPushButton(trans("input.btn.send"))
        self.window.ui.nodes['input.send_btn'].clicked.connect(
            lambda: self.window.controller.input.user_send())

        # stop button
        self.window.ui.nodes['input.stop_btn'] = QPushButton(trans("input.btn.stop"))
        self.window.ui.nodes['input.stop_btn'].setVisible(False)
        self.window.ui.nodes['input.stop_btn'].clicked.connect(
            lambda: self.window.controller.input.stop())

        # layout
        self.window.ui.nodes['ui.input.buttons'] = QHBoxLayout()
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.stream'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_clear'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_enter'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_shift_enter'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_none'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_btn'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.stop_btn'])
        self.window.ui.nodes['ui.input.buttons'].setAlignment(Qt.AlignRight)

        return self.window.ui.nodes['ui.input.buttons']

    def update_min_height(self):
        """
        Update the minimum height of the input tab
        """
        idx = self.window.ui.tabs['input'].currentIndex()
        if idx == 0:
            self.window.ui.nodes['input'].setMinimumHeight(50)
            self.window.ui.tabs['input'].setMinimumHeight(self.min_height_input_tab)
        else:
            self.window.ui.nodes['input'].setMinimumHeight(self.min_height_files_tab)
            self.window.ui.tabs['input'].setMinimumHeight(180)
