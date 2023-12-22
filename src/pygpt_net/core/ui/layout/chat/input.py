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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QRadioButton, QCheckBox, \
    QTabWidget, QWidget

from ...status import Status
from ...attachments import Attachments
from ...attachments_uploaded import AttachmentsUploaded
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

    def setup(self):
        """
        Setup input

        :return: QWidget
        :rtype: QWidget
        """
        # input textarea
        self.window.ui.nodes['input'] = ChatInput(self.window)

        # status
        status = self.status.setup()
        status.setAlignment(Qt.AlignLeft)

        # send options
        self.window.ui.nodes['input.send_enter'] = QRadioButton(trans("input.radio.enter"))
        self.window.ui.nodes['input.send_enter'].clicked.connect(
            lambda: self.window.controller.input.toggle_send_shift(
                1))

        self.window.ui.nodes['input.send_shift_enter'] = QRadioButton(trans("input.radio.enter_shift"))
        self.window.ui.nodes['input.send_shift_enter'].clicked.connect(
            lambda: self.window.controller.input.toggle_send_shift(
                2))

        self.window.ui.nodes['input.send_none'] = QRadioButton(trans("input.radio.none"))
        self.window.ui.nodes['input.send_none'].clicked.connect(
            lambda: self.window.controller.input.toggle_send_shift(
                0))

        self.window.ui.nodes['input.send_clear'] = QCheckBox(trans('input.send_clear'))
        self.window.ui.nodes['input.send_clear'].stateChanged.connect(
            lambda: self.window.controller.input.toggle_send_clear(self.window.ui.nodes['input.send_clear'].isChecked()))

        self.window.ui.nodes['input.stream'] = QCheckBox(trans('input.stream'))
        self.window.ui.nodes['input.stream'].stateChanged.connect(
            lambda: self.window.controller.input.toggle_stream(self.window.ui.nodes['input.stream'].isChecked()))

        # send button
        self.window.ui.nodes['input.send_btn'] = QPushButton(trans("input.btn.send"))
        self.window.ui.nodes['input.send_btn'].clicked.connect(
            lambda: self.window.controller.input.user_send())

        # send button
        self.window.ui.nodes['input.stop_btn'] = QPushButton(trans("input.btn.stop"))
        self.window.ui.nodes['input.stop_btn'].setVisible(False)
        self.window.ui.nodes['input.stop_btn'].clicked.connect(
            lambda: self.window.controller.input.stop())

        # send layout (options + send button)
        self.window.ui.nodes['ui.input.buttons'] = QHBoxLayout()
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.stream'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_clear'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_enter'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_shift_enter'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_none'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.send_btn'])
        self.window.ui.nodes['ui.input.buttons'].addWidget(self.window.ui.nodes['input.stop_btn'])
        self.window.ui.nodes['ui.input.buttons'].setAlignment(Qt.AlignRight)

        # bottom layout (status + send layout)
        bottom_layout = QHBoxLayout()
        bottom_layout.addLayout(status)
        bottom_layout.addLayout(self.window.ui.nodes['ui.input.buttons'])

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

        # input tab
        input_tab = QWidget()
        input_layout = QVBoxLayout()
        input_layout.addWidget(self.window.ui.nodes['input'])
        input_layout.setContentsMargins(0, 0, 0, 0)
        self.window.ui.nodes['input'].setMinimumHeight(50)
        input_tab.setLayout(input_layout)

        # attachments tab
        attachments_layout = self.attachments.setup()
        attachment_uploaded_layout = self.attachments_uploaded.setup()

        input_tab_minimum_height = 80
        files_tabs_min_height = 120

        # files tab
        files_tab = QWidget()
        files_layout = QVBoxLayout()
        files_layout.addLayout(attachments_layout)
        files_tab.setLayout(files_layout)
        files_tab.setMinimumHeight(files_tabs_min_height)

        # files uploaded tab
        files_uploaded_tab = QWidget()
        files_uploaded_layout = QVBoxLayout()
        files_uploaded_layout.addLayout(attachment_uploaded_layout)
        files_uploaded_tab.setLayout(files_uploaded_layout)
        files_uploaded_tab.setMinimumHeight(files_tabs_min_height)

        # tabs (input + attachments)
        self.window.ui.tabs['input'] = QTabWidget()
        self.window.ui.tabs['input'].setMinimumHeight(input_tab_minimum_height)

        # add tabs
        self.window.ui.tabs['input'].addTab(input_tab, trans('input.tab'))
        self.window.ui.tabs['input'].addTab(files_tab, trans('attachments.tab'))
        self.window.ui.tabs['input'].addTab(files_uploaded_tab, trans('attachments_uploaded.tab'))
        self.window.ui.tabs['input'].currentChanged.connect(self.update_min_heigth)

        # full input layout
        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(self.window.ui.tabs['input'])
        layout.addLayout(bottom_layout)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def update_min_heigth(self):
        """
        Update the minimum height of the input tab
        """
        idx = self.window.ui.tabs['input'].currentIndex()
        if idx == 0:
            self.window.ui.nodes['input'].setMinimumHeight(50)
            self.window.ui.tabs['input'].setMinimumHeight(80)
        else:
            self.window.ui.nodes['input'].setMinimumHeight(120)
            self.window.ui.tabs['input'].setMinimumHeight(180)

