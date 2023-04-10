#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QRadioButton, QCheckBox

from core.ui.status import Status
from core.ui.widgets import ChatInput
from core.utils import trans


class Input:
    def __init__(self, window=None):
        """
        Input

        :param window: main UI window object
        """
        self.window = window
        self.status = Status(window)

    def setup(self):
        """
        Setup input

        :return: QVBoxLayout
        """
        # input textarea
        self.window.data['input'] = ChatInput(self.window)

        # status
        status_layout = self.status.setup()
        status_layout.setAlignment(Qt.AlignLeft)

        css_fix = "QRadioButton::indicator:checked { background-color: #1de9b6; } QRadioButton::indicator:unchecked { background-color: #3a3f45; }"

        # send options
        self.window.data['input.send_enter'] = QRadioButton(trans("input.radio.enter"))        
        self.window.data['input.send_enter'].setStyleSheet(css_fix) # windows style fix (without this checkboxes are invisible!)
        self.window.data['input.send_enter'].clicked.connect(
            lambda: self.window.controller.input.toggle_send_shift(
                not self.window.data['input.send_enter'].isChecked()))
        self.window.data['input.send_shift_enter'] = QRadioButton(trans("input.radio.enter_shift"))
        self.window.data['input.send_shift_enter'].setStyleSheet(css_fix) # windows style fix (without this checkboxes are invisible!)
        self.window.data['input.send_shift_enter'].clicked.connect(
            lambda: self.window.controller.input.toggle_send_shift(
                self.window.data['input.send_shift_enter'].isChecked()))
        self.window.data['input.send_clear'] = QCheckBox(trans('input.send_clear'))
        self.window.data['input.send_clear'].setStyleSheet("QCheckBox::indicator:checked { background-color: #1de9b6; } QCheckBox::indicator:unchecked { background-color: #3a3f45; }") # windows style fix (without this checkboxes are invisible!)
        self.window.data['input.send_clear'].stateChanged.connect(
            lambda: self.window.controller.input.toggle_send_clear(self.window.data['input.send_clear'].isChecked()))

        # send button
        self.window.data['input.send_btn'] = QPushButton(trans("input.btn.send"))
        self.window.data['input.send_btn'].clicked.connect(
            lambda: self.window.controller.input.send())

        # send layout
        send_layout = QHBoxLayout()
        send_layout.addWidget(self.window.data['input.send_clear'])
        send_layout.addWidget(self.window.data['input.send_enter'])
        send_layout.addWidget(self.window.data['input.send_shift_enter'])
        send_layout.addWidget(self.window.data['input.send_btn'])
        send_layout.setAlignment(Qt.AlignRight)

        # bottom layout
        bottom_layout = QHBoxLayout()
        bottom_layout.addLayout(status_layout)
        bottom_layout.addLayout(send_layout)

        # header
        self.window.data['input.label'] = QLabel(trans("input.label"))
        self.window.data['input.label'].setStyleSheet("font-weight: bold;")
        self.window.data['input.counter'] = QLabel("")

        header = QHBoxLayout()
        header.addWidget(self.window.data['input.label'])
        header.addWidget(self.window.data['input.counter'], alignment=Qt.AlignRight)

        # input layout
        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addWidget(self.window.data['input'])
        layout.addLayout(bottom_layout)

        return layout
