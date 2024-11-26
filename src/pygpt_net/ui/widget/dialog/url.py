#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.26 02:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QDialog, QLabel, QHBoxLayout, QVBoxLayout, QPushButton

from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans
from pygpt_net.ui.widget.textarea.url import UrlInput


class UrlDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Url dialog

        :param window: main window
        :param id: info window id
        """
        super(UrlDialog, self).__init__(window)
        self.window = window
        self.id = id
        self.current = None
        self.input = UrlInput(window, id)
        self.input.setMinimumWidth(400)

        self.window.ui.nodes['dialog.url.btn.update'] = QPushButton(trans('dialog.url.update'))
        self.window.ui.nodes['dialog.url.btn.update'].clicked.connect(
            lambda: self.window.controller.dialogs.confirm.accept_url(
                self.id,
                self.window.ui.dialog['url'].current,
                self.input.text()),
        )

        self.window.ui.nodes['dialog.url.btn.dismiss'] = QPushButton(trans('dialog.url.dismiss'))
        self.window.ui.nodes['dialog.url.btn.dismiss'].clicked.connect(
            lambda: self.window.controller.dialogs.confirm.dismiss_url())

        bottom = QHBoxLayout()
        bottom.addWidget(self.window.ui.nodes['dialog.url.btn.dismiss'])
        bottom.addWidget(self.window.ui.nodes['dialog.url.btn.update'])

        self.window.ui.nodes['dialog.url.label'] = QLabel(trans("dialog.url.title"))
        self.window.ui.nodes['dialog.url.tip'] = HelpLabel(trans("dialog.url.tip"))

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['dialog.url.label'])
        layout.addWidget(self.input)
        layout.addWidget(self.window.ui.nodes['dialog.url.tip'])
        layout.addLayout(bottom)

        self.setLayout(layout)
