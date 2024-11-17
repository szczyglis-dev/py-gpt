#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 03:00:00                  #
# ================================================== #

import os

from PySide6.QtGui import QPixmap, Qt, QIcon
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
        self.thanks = None

    def get_thanks(self) -> str:
        """
        Get people list

        :return: contributors and supporters list
        """
        return self.window.core.updater.get_fetch_thanks()

    def prepare_content(self) -> str:
        """
        Get info text

        :return: info text
        """
        llama_index_version = None
        langchain_version = None
        openai_version = None
        versions = True

        try:
            from llama_index.core import __version__ as llama_index_version
            from langchain import __version__ as langchain_version
            from openai.version import VERSION as openai_version
        except ImportError:
            pass

        lib_versions = ""
        if llama_index_version is None or langchain_version is None or openai_version is None:
            versions = False

        if versions:
            lib_versions = "OpenAI API: {}, Langchain: {}, Llama-index: {}\n\n".format(
                openai_version,
                langchain_version,
                llama_index_version,
            )

        platform = self.window.core.platforms.get_as_string()
        version = self.window.meta['version']
        build = self.window.meta['build']
        website = self.window.meta['website']
        github = self.window.meta['github']
        docs = self.window.meta['docs']
        author = self.window.meta['author']
        email = self.window.meta['email']

        label_version = trans("dialog.about.version")
        label_build = trans("dialog.about.build")
        label_website = trans("dialog.about.website")
        label_github = trans("dialog.about.github")
        label_docs = trans("dialog.about.docs")

        data = "{label_version}: {version}, {platform}\n" \
               "{label_build}: {build}\n" \
               "{lib_versions}" \
               "{label_website}: {website}\n" \
               "{label_github}: {github}\n" \
               "{label_docs}: {docs}\n\n" \
               "(c) 2024 {author}\n" \
               "{email}\n".format(
                label_version=label_version,
                version=version,
                platform=platform,
                label_build=label_build,
                build=build.replace('.', '-'),
                label_website=label_website,
                website=website,
                label_github=label_github,
                github=github,
                label_docs=label_docs,
                docs=docs,
                author=author,
                email=email,
                lib_versions=lib_versions,
            )
        return data

    def setup(self):
        """Setups about dialog"""
        id = 'about'

        logo_label = QLabel()
        path = os.path.abspath(os.path.join(self.window.core.config.get_app_path(), 'data', 'logo.png'))
        pixmap = QPixmap(path)
        logo_label.setPixmap(pixmap)

        self.window.ui.nodes['dialog.about.btn.website'] = QPushButton(QIcon(":/icons/home.svg"), trans('about.btn.website'))
        self.window.ui.nodes['dialog.about.btn.website'].clicked.connect(lambda: self.window.controller.dialogs.info.goto_website())
        self.window.ui.nodes['dialog.about.btn.website'].setCursor(Qt.PointingHandCursor)
        self.window.ui.nodes['dialog.about.btn.website'].setStyleSheet("font-size: 11px;")

        self.window.ui.nodes['dialog.about.btn.github'] = QPushButton(QIcon(":/icons/code.svg"), trans('about.btn.github'))
        self.window.ui.nodes['dialog.about.btn.github'].clicked.connect(lambda: self.window.controller.dialogs.info.goto_github())
        self.window.ui.nodes['dialog.about.btn.github'].setCursor(Qt.PointingHandCursor)

        self.window.ui.nodes['dialog.about.btn.support'] = QPushButton(QIcon(":/icons/favorite.svg"), trans('about.btn.support'))
        self.window.ui.nodes['dialog.about.btn.support'].clicked.connect(lambda: self.window.controller.dialogs.info.goto_donate())
        self.window.ui.nodes['dialog.about.btn.support'].setCursor(Qt.PointingHandCursor)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.window.ui.nodes['dialog.about.btn.support'])
        buttons_layout.addWidget(self.window.ui.nodes['dialog.about.btn.website'])
        buttons_layout.addWidget(self.window.ui.nodes['dialog.about.btn.github'])

        string = self.prepare_content()
        self.window.ui.nodes['dialog.about.content'] = QLabel(string)
        self.window.ui.nodes['dialog.about.content'].setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.window.ui.nodes['dialog.about.thanks'] = QLabel(trans('about.thanks'))
        self.window.ui.nodes['dialog.about.thanks'].setAlignment(Qt.AlignCenter)

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
        title.setAlignment(Qt.AlignCenter)

        self.window.ui.nodes['dialog.about.thanks.content'] = QPlainTextEdit()
        self.window.ui.nodes['dialog.about.thanks.content'].setReadOnly(True)
        self.window.ui.nodes['dialog.about.thanks.content'].setPlainText("")
        self.window.ui.nodes['dialog.about.thanks.content'].setStyleSheet("font-size: 11px;")

        layout = QVBoxLayout()
        layout.addWidget(logo_label)
        layout.addWidget(title)
        layout.addWidget(self.window.ui.nodes['dialog.about.content'])
        layout.addWidget(self.window.ui.nodes['dialog.about.thanks'])
        layout.addWidget(self.window.ui.nodes['dialog.about.thanks.content'])
        layout.addStretch(1)
        layout.addLayout(buttons_layout)

        self.window.ui.dialog['info.' + id] = InfoDialog(self.window, id)
        self.window.ui.dialog['info.' + id].setLayout(layout)
        self.window.ui.dialog['info.' + id].setWindowTitle(trans("dialog.about.title"))

    def prepare(self):
        """Update dialog content"""
        people = str(self.get_thanks())
        self.window.ui.nodes['dialog.about.thanks.content'].setPlainText(people)
        if people == "":
            self.window.ui.nodes['dialog.about.thanks'].hide()
            self.window.ui.nodes['dialog.about.thanks.content'].hide()
        else:
            self.window.ui.nodes['dialog.about.thanks'].show()
            self.window.ui.nodes['dialog.about.thanks.content'].show()
