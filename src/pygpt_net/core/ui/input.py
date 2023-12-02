#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.02 14:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QRadioButton, QCheckBox

from .status import Status
from .widgets import ChatInput
from ..utils import trans


class Input:
    def __init__(self, window=None):
        """
        Input UI

        :param window: main UI window object
        """
        self.window = window
        self.status = Status(window)

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
        self.window.data['input.send_enter'].setStyleSheet(
            self.window.controller.theme.get_style('radio'))  # Windows fix
        self.window.data['input.send_enter'].clicked.connect(
            lambda: self.window.controller.input.toggle_send_shift(
                not self.window.data['input.send_enter'].isChecked()))

        self.window.data['input.send_shift_enter'] = QRadioButton(trans("input.radio.enter_shift"))
        self.window.data['input.send_shift_enter'].setStyleSheet(
            self.window.controller.theme.get_style('radio'))  # Windows fix
        self.window.data['input.send_shift_enter'].clicked.connect(
            lambda: self.window.controller.input.toggle_send_shift(
                self.window.data['input.send_shift_enter'].isChecked()))

        self.window.data['input.send_clear'] = QCheckBox(trans('input.send_clear'))
        self.window.data['input.send_clear'].setStyleSheet(
            self.window.controller.theme.get_style('checkbox'))  # Windows fix
        self.window.data['input.send_clear'].stateChanged.connect(
            lambda: self.window.controller.input.toggle_send_clear(self.window.data['input.send_clear'].isChecked()))

        self.window.data['input.stream'] = QCheckBox(trans('input.stream'))
        self.window.data['input.stream'].setStyleSheet(
            self.window.controller.theme.get_style('checkbox'))  # Windows fix
        self.window.data['input.stream'].stateChanged.connect(
            lambda: self.window.controller.input.toggle_stream(self.window.data['input.stream'].isChecked()))

        # send button
        self.window.data['input.send_btn'] = QPushButton(trans("input.btn.send"))
        self.window.data['input.send_btn'].clicked.connect(
            lambda: self.window.controller.input.user_send())

        # send layout
        send_layout = QHBoxLayout()
        send_layout.addWidget(self.window.data['input.stream'])
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
        self.window.data['input.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))
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
