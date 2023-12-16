#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.08 22:00:00                  #
# ================================================== #
import os

from PySide6.QtGui import QPixmap, Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QPlainTextEdit, QSizePolicy

from ..widget.dialog import InfoDialog
from ...utils import trans


class About:
    def __init__(self, window=None):
        """
        About dialog

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """Setups about dialog"""
        id = 'about'

        logo_label = QLabel()
        path = os.path.abspath(os.path.join(self.window.config.get_root_path(), 'data', 'logo.png'))
        pixmap = QPixmap(path)
        logo_label.setPixmap(pixmap)

        btn_www = QPushButton('WWW')
        btn_www.clicked.connect(lambda: self.window.controller.info.goto_website())
        btn_www.setCursor(Qt.PointingHandCursor)

        btn_github = QPushButton('GitHub')
        btn_github.clicked.connect(lambda: self.window.controller.info.goto_github())
        btn_github.setCursor(Qt.PointingHandCursor)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(btn_www)
        buttons_layout.addWidget(btn_github)

        string = "{}: {}\n" \
                 "{}: {}\n" \
                 "{}: {}\n" \
                 "{}: {}\n" \
                 "{}: {}\n\n" \
                 "(c) 2023 {}\n" \
                 "{}\n".format(trans("dialog.about.version"),
                               self.window.version,
                               trans("dialog.about.build"),
                               self.window.build,

                               trans("dialog.about.website"),
                               self.window.website,
                               trans("dialog.about.github"),
                               self.window.github,
                               trans("dialog.about.docs"),
                               self.window.docs,
                               self.window.author,
                               self.window.email)

        self.window.data['dialog.about.content'] = QLabel(string)

        title = QLabel("PyGPT")
        title.setContentsMargins(0, 0, 0, 0)
        title.setStyleSheet(
            "font-size: 16px; font-weight: bold; margin-bottom: 10px; margin-left: 0; margin-top: 10px; padding: 0;")

        thx_textarea = QPlainTextEdit()
        thx_textarea.setReadOnly(True)
        thx_textarea.setPlainText("kaneda2004")

        layout = QVBoxLayout()
        layout.addWidget(logo_label)
        layout.addWidget(title)
        layout.addWidget(self.window.data['dialog.about.content'])
        layout.addWidget(QLabel(trans('about.thanks') + ":"))
        layout.addWidget(thx_textarea)
        layout.addLayout(buttons_layout)

        self.window.dialog['info.' + id] = InfoDialog(self.window, id)
        self.window.dialog['info.' + id].setLayout(layout)
        self.window.dialog['info.' + id].setWindowTitle(trans("dialog.about.title"))
