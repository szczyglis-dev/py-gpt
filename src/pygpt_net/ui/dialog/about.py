#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.19 18:00:00                  #
# ================================================== #

import os

from PySide6.QtGui import QPixmap, Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QPlainTextEdit

from pygpt_net.ui.widget.dialog.info import InfoDialog
from pygpt_net.utils import trans


class About:
    def __init__(self, window=None):
        """
        About dialog

        :param window: Window instance
        """
        self.window = window

    def get_contributors(self) -> list:
        """
        Get contributors list

        :return: contributors list
        """
        return [
            "kaneda2004",
            "moritz-t-w",
        ]

    def prepare_content(self) -> str:
        """
        Get info text
        :return: info text
        """
        platform = self.window.core.platforms.get_as_string()
        data = "{}: {}, {}\n" \
               "{}: {}\n" \
               "{}: {}\n" \
               "{}: {}\n" \
               "{}: {}\n\n" \
               "(c) 2024 {}\n" \
               "{}\n".format(trans("dialog.about.version"),
                             self.window.meta['version'],
                             platform,
                             trans("dialog.about.build"),
                             self.window.meta['build'],

                             trans("dialog.about.website"),
                             self.window.meta['website'],
                             trans("dialog.about.github"),
                             self.window.meta['github'],
                             trans("dialog.about.docs"),
                             self.window.meta['docs'],
                             self.window.meta['author'],
                             self.window.meta['email'])

        return data

    def setup(self):
        """Setups about dialog"""
        id = 'about'

        logo_label = QLabel()
        path = os.path.abspath(os.path.join(self.window.core.config.get_app_path(), 'data', 'logo.png'))
        pixmap = QPixmap(path)
        logo_label.setPixmap(pixmap)

        btn_www = QPushButton('WWW')
        btn_www.clicked.connect(lambda: self.window.controller.dialogs.info.goto_website())
        btn_www.setCursor(Qt.PointingHandCursor)

        btn_github = QPushButton('GitHub')
        btn_github.clicked.connect(lambda: self.window.controller.dialogs.info.goto_github())
        btn_github.setCursor(Qt.PointingHandCursor)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(btn_www)
        buttons_layout.addWidget(btn_github)

        string = self.prepare_content()
        self.window.ui.nodes['dialog.about.content'] = QLabel(string)
        self.window.ui.nodes['dialog.about.content'].setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.window.ui.nodes['dialog.about.thanks'] = QLabel(trans('about.thanks') + ":")

        title = QLabel("PyGPT")
        title.setContentsMargins(0, 0, 0, 0)
        title.setStyleSheet(
            "font-size: 16px; "
            "font-weight: bold; "
            "margin-bottom: 10px; "
            "margin-left: 0; "
            "margin-top: 10px; "
            "padding: 0;"
        )

        contributors = QPlainTextEdit()
        contributors.setReadOnly(True)
        contributors.setPlainText(", ".join(self.get_contributors()))

        layout = QVBoxLayout()
        layout.addWidget(logo_label)
        layout.addWidget(title)
        layout.addWidget(self.window.ui.nodes['dialog.about.content'])
        layout.addWidget(self.window.ui.nodes['dialog.about.thanks'])
        layout.addWidget(contributors)
        layout.addLayout(buttons_layout)

        self.window.ui.dialog['info.' + id] = InfoDialog(self.window, id)
        self.window.ui.dialog['info.' + id].setLayout(layout)
        self.window.ui.dialog['info.' + id].setWindowTitle(trans("dialog.about.title"))
