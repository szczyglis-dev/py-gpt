#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.10 23:00:00                  #
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
        super(FindDialog, self).__init__(window)
        self.window = window
        self.id = id
        self.current = None

        self.input = FindInput(window, id)
        self.input.setMinimumWidth(400)
        self.counter = HelpLabel('0/0')
        self.counter.setAlignment(Qt.AlignCenter)
        self.counter.setMinimumWidth(70)
        self.counter.setMaximumWidth(70)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)  # always on top

        self.window.ui.nodes['dialog.find.input'] = self.input
        self.window.ui.nodes['dialog.find.counter'] = self.counter
        self.window.ui.nodes['dialog.find.btn.clear'] = QPushButton(trans('dialog.find.btn.clear'))
        self.window.ui.nodes['dialog.find.btn.clear'].clicked.connect(
            lambda: self.window.controller.finder.clear_input(),
        )
        self.window.ui.nodes['dialog.find.btn.find_prev'] = QPushButton(trans('dialog.find.btn.find_prev'))
        self.window.ui.nodes['dialog.find.btn.find_prev'].clicked.connect(
            lambda: self.window.controller.finder.prev(),
        )
        self.window.ui.nodes['dialog.find.btn.find_next'] = QPushButton(trans('dialog.find.btn.find_next'))
        self.window.ui.nodes['dialog.find.btn.find_next'].clicked.connect(
            lambda: self.window.controller.finder.next(),
        )

        bottom = QHBoxLayout()
        bottom.addWidget(self.window.ui.nodes['dialog.find.btn.clear'])
        bottom.addWidget(self.window.ui.nodes['dialog.find.btn.find_prev'])
        bottom.addWidget(self.window.ui.nodes['dialog.find.btn.find_next'])

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
            self.window.controller.finder.close(reset=False)
            self.close()
