#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.21 02:00:00                  #
# ================================================== #

import os

from PySide6.QtGui import QPixmap, Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QPlainTextEdit

from pygpt_net.ui.widget.dialog.info import InfoDialog
from pygpt_net.utils import trans


class About:

    RELEASE_YEAR = 2026

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

    def build_versions_str(self, lib_versions: dict, break_after: str = "LlamaIndex") -> str:
        parts = []
        line = []
        for k, v in lib_versions.items():
            line.append(f"{k}: {v}")
            if k == break_after:
                parts.append(", ".join(line))
                line = []
        if line:
            parts.append(", ".join(line))
        return "\n".join(parts)

    def prepare_content(self) -> str:
        """
        Get info text

        :return: info text
        """
        lib_versions = {}

        try:
            import platform
            lib_versions['Python'] = platform.python_version()
        except ImportError:
            pass

        try:
            from openai.version import VERSION as openai_version
            lib_versions['OpenAI API'] = openai_version
        except ImportError:
            pass

        try:
            from llama_index.core import __version__ as llama_index_version
            lib_versions['LlamaIndex'] = llama_index_version
        except ImportError:
            pass

        try:
            from anthropic import __version__ as anthropic_version
            lib_versions['Anthropic API'] = anthropic_version
        except ImportError:
            pass

        try:
            from google.genai import __version__ as google_genai_version
            lib_versions['Google API'] = google_genai_version
        except ImportError:
            pass

        try:
            from xai_sdk import __version__ as xai_sdk_version
            lib_versions['xAI API'] = xai_sdk_version
        except ImportError:
            pass

        versions_str = ""
        if lib_versions:
            versions_str = self.build_versions_str(lib_versions, break_after="LlamaIndex")

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

        data = f"{label_version}: {version}, {platform}\n" \
               f"{label_build}: {build.replace('.', '-')}\n\n" \
               f"{versions_str}\n\n" \
               f"{label_website}: {website}\n" \
               f"{label_github}: {github}\n" \
               f"{label_docs}: {docs}\n\n" \
               f"(c) {self.RELEASE_YEAR} {author}\n" \
               f"{email}\n"
        return data

    def setup(self):
        """Setups about dialog"""
        id = 'about'

        logo_label = QLabel()
        path = os.path.abspath(os.path.join(self.window.core.config.get_app_path(), 'data', 'logo.png'))
        pixmap = QPixmap(path)
        logo_label.setPixmap(pixmap)

        btn_web = QPushButton(QIcon(":/icons/home.svg"), trans('about.btn.website'))
        btn_web.clicked.connect(lambda: self.window.controller.dialogs.info.goto_website())
        btn_web.setCursor(Qt.PointingHandCursor)
        btn_web.setStyleSheet("font-size: 11px;")
        self.window.ui.nodes['dialog.about.btn.website'] = btn_web

        btn_git = QPushButton(QIcon(":/icons/code.svg"), trans('about.btn.github'))
        btn_git.clicked.connect(lambda: self.window.controller.dialogs.info.goto_github())
        btn_git.setCursor(Qt.PointingHandCursor)
        self.window.ui.nodes['dialog.about.btn.github'] = btn_git


        btn_support = QPushButton(QIcon(":/icons/favorite.svg"), trans('about.btn.support'))
        btn_support.clicked.connect(lambda: self.window.controller.dialogs.info.goto_donate())
        btn_support.setCursor(Qt.PointingHandCursor)
        self.window.ui.nodes['dialog.about.btn.support'] = btn_support

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.window.ui.nodes['dialog.about.btn.support'])
        buttons_layout.addWidget(self.window.ui.nodes['dialog.about.btn.website'])
        buttons_layout.addWidget(self.window.ui.nodes['dialog.about.btn.github'])

        string = self.prepare_content()
        content = QLabel(string)
        content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content.setWordWrap(True)
        self.window.ui.nodes['dialog.about.content'] = content

        thanks = QLabel(trans('about.thanks'))
        thanks.setAlignment(Qt.AlignCenter)
        self.window.ui.nodes['dialog.about.thanks'] = thanks

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

        thanks_content = QPlainTextEdit()
        thanks_content.setReadOnly(True)
        thanks_content.setPlainText("")
        thanks_content.setStyleSheet("font-size: 11px;")
        self.window.ui.nodes['dialog.about.thanks.content'] = thanks_content

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
