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
from PySide6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QPushButton

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.textarea.find import FindInput
from pygpt_net.utils import trans


class FindDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Find dialog

        :param window: main window
        :param id: info window id
        """
        super().__init__(window)
        self.window = window
        self.id = id
        self.current = None

        self.input = FindInput(window, id)
        self.input.setMinimumWidth(400)
        self.counter = HelpLabel('0/0')
        self.counter.setAlignment(Qt.AlignCenter)
        self.counter.setFixedWidth(70)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)

        nodes = self.window.ui.nodes
        nodes['dialog.find.input'] = self.input
        nodes['dialog.find.counter'] = self.counter

        btn_clear = QPushButton(trans('dialog.find.btn.clear'))
        btn_clear.clicked.connect(self.window.controller.finder.clear_input)
        nodes['dialog.find.btn.clear'] = btn_clear

        btn_prev = QPushButton(trans('dialog.find.btn.find_prev'))
        btn_prev.clicked.connect(self.window.controller.finder.prev)
        nodes['dialog.find.btn.find_prev'] = btn_prev

        btn_next = QPushButton(trans('dialog.find.btn.find_next'))
        btn_next.clicked.connect(self.window.controller.finder.next)
        nodes['dialog.find.btn.find_next'] = btn_next

        bottom = QHBoxLayout()
        bottom.addWidget(btn_clear)
        bottom.addWidget(btn_prev)
        bottom.addWidget(btn_next)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input)
        input_layout.addWidget(self.counter)

        layout = QVBoxLayout()
        layout.addLayout(input_layout)
        layout.addLayout(bottom)

        self.setLayout(layout)

    def closeEvent(self, event):
        """
        Close event

        :param event: event
        """
        self.window.controller.finder.close(reset=False)
        event.accept()

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)