#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.11 23:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QRadioButton, QCheckBox, \
    QTabWidget, QWidget

from .status import Status
from .attachments import Attachments
from .attachments_uploaded import AttachmentsUploaded
from .widget.textarea import ChatInput
from ..utils import trans


class Input:
    def __init__(self, window=None):
        """
        Input UI

        :param window: main UI window object
        """
        self.window = window
        self.status = Status(window)
        self.attachments = Attachments(window)
        self.attachments_uploaded = AttachmentsUploaded(window)

    def setup(self):
        """
        Setups input

        :return: QVBoxLayout
        """
        # input textarea
        self.window.data['input'] = ChatInput(self.window)

        # status
        status_layout = self.status.setup()
        status_layout.setAlignment(Qt.AlignLeft)

        # send options
        self.window.data['input.send_enter'] = QRadioButton(trans("input.radio.enter"))
        self.window.data['input.send_enter'].clicked.connect(
            lambda: self.window.controller.input.toggle_send_shift(
                1))

        self.window.data['input.send_shift_enter'] = QRadioButton(trans("input.radio.enter_shift"))
        self.window.data['input.send_shift_enter'].clicked.connect(
            lambda: self.window.controller.input.toggle_send_shift(
                2))

        self.window.data['input.send_none'] = QRadioButton(trans("input.radio.none"))
        self.window.data['input.send_none'].clicked.connect(
            lambda: self.window.controller.input.toggle_send_shift(
                0))

        self.window.data['input.send_clear'] = QCheckBox(trans('input.send_clear'))
        self.window.data['input.send_clear'].stateChanged.connect(
            lambda: self.window.controller.input.toggle_send_clear(self.window.data['input.send_clear'].isChecked()))

        self.window.data['input.stream'] = QCheckBox(trans('input.stream'))
        self.window.data['input.stream'].stateChanged.connect(
            lambda: self.window.controller.input.toggle_stream(self.window.data['input.stream'].isChecked()))

        # send button
        self.window.data['input.send_btn'] = QPushButton(trans("input.btn.send"))
        self.window.data['input.send_btn'].clicked.connect(
            lambda: self.window.controller.input.user_send())

        # send button
        self.window.data['input.stop_btn'] = QPushButton(trans("input.btn.stop"))
        self.window.data['input.stop_btn'].setVisible(False)
        self.window.data['input.stop_btn'].clicked.connect(
            lambda: self.window.controller.input.stop())

        # send layout (options + send button)
        self.window.data['ui.input.buttons'] = QHBoxLayout()
        self.window.data['ui.input.buttons'].addWidget(self.window.data['input.stream'])
        self.window.data['ui.input.buttons'].addWidget(self.window.data['input.send_clear'])
        self.window.data['ui.input.buttons'].addWidget(self.window.data['input.send_enter'])
        self.window.data['ui.input.buttons'].addWidget(self.window.data['input.send_shift_enter'])
        self.window.data['ui.input.buttons'].addWidget(self.window.data['input.send_none'])
        self.window.data['ui.input.buttons'].addWidget(self.window.data['input.send_btn'])
        self.window.data['ui.input.buttons'].addWidget(self.window.data['input.stop_btn'])
        self.window.data['ui.input.buttons'].setAlignment(Qt.AlignRight)

        # bottom layout (status + send layout)
        bottom_layout = QHBoxLayout()
        bottom_layout.addLayout(status_layout)
        bottom_layout.addLayout(self.window.data['ui.input.buttons'])

        # header (input label + input counter)
        self.window.data['input.label'] = QLabel(trans("input.label"))
        self.window.data['input.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        self.window.data['input.counter'] = QLabel("")

        header = QHBoxLayout()
        header.addWidget(self.window.data['input.label'])
        header.addWidget(self.window.data['input.counter'], alignment=Qt.AlignRight)

        # input tab
        input_tab = QWidget()
        input_layout = QVBoxLayout()
        input_layout.addWidget(self.window.data['input'])
        input_tab.setLayout(input_layout)

        # attachments tab
        attachments_layout = self.attachments.setup()
        attachment_uploaded_layout = self.attachments_uploaded.setup()

        # files tab
        files_tab = QWidget()
        files_layout = QVBoxLayout()
        files_layout.addLayout(attachments_layout)
        files_tab.setLayout(files_layout)

        # files uploaded tab
        files_uploaded_tab = QWidget()
        files_uploaded_layout = QVBoxLayout()
        files_uploaded_layout.addLayout(attachment_uploaded_layout)
        files_uploaded_tab.setLayout(files_uploaded_layout)

        # tabs (input + attachments)
        self.window.tabs['input'] = QTabWidget()

        # add tabs
        self.window.tabs['input'].addTab(input_tab, trans('input.tab'))
        self.window.tabs['input'].addTab(files_tab, trans('attachments.tab'))
        self.window.tabs['input'].addTab(files_uploaded_tab, trans('attachments_uploaded.tab'))

        # full input layout
        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(self.window.tabs['input'])
        layout.addLayout(bottom_layout)

        return layout
