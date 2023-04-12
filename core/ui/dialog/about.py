#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.12 20:00:00                  #
# ================================================== #

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout

from core.ui.widgets import InfoDialog
from core.utils import trans


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
        pixmap = QPixmap('./data/logo.png')
        logo_label.setPixmap(pixmap)

        btn_www = QPushButton('WWW')
        btn_www.clicked.connect(lambda: self.window.controller.info.goto_website())

        btn_github = QPushButton('GitHub')
        btn_github.clicked.connect(lambda: self.window.controller.info.goto_github())

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(btn_www)
        buttons_layout.addWidget(btn_github)

        string = "PY-GPT\n" \
                 "-------------\n" \
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
                               self.window.author,
                               self.window.email)

        self.window.data['dialog.about.content'] = QLabel(string)

        layout = QVBoxLayout()
        layout.addWidget(logo_label)
        layout.addWidget(self.window.data['dialog.about.content'])
        layout.addLayout(buttons_layout)

        self.window.dialog['info.' + id] = InfoDialog(self.window, id)
        self.window.dialog['info.' + id].setLayout(layout)
        self.window.dialog['info.' + id].setWindowTitle(trans("dialog.about.title"))
