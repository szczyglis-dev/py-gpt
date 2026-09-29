#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.26 12:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot, QTimer
from PySide6.QtGui import QPixmap, Qt, QIcon
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QPlainTextEdit

from pygpt_net.core.qt import safe_emit
from pygpt_net.ui.widget.dialog.info import InfoDialog
from pygpt_net.utils import trans


class AboutVersionsSignals(QObject):
    result = Signal(object)


class AboutVersionsWorker(QRunnable):
    """Load optional SDK versions without blocking the About dialog."""

    def __init__(self):
        super().__init__()
        self.signals = AboutVersionsSignals()

    @Slot()
    def run(self):
        versions = {}

        try:
            import platform
            versions['Python'] = platform.python_version()
        except Exception:
            versions['Python'] = '-'

        try:
            from openai.version import VERSION as openai_version
            versions['OpenAI SDK'] = openai_version
        except Exception:
            versions['OpenAI SDK'] = '-'

        try:
            from llama_index.core import __version__ as llama_index_version
            versions['LlamaIndex'] = llama_index_version
        except Exception:
            versions['LlamaIndex'] = '-'

        try:
            from anthropic import __version__ as anthropic_version
            versions['Anthropic SDK'] = anthropic_version
        except Exception:
            versions['Anthropic SDK'] = '-'

        try:
            from google.genai import __version__ as google_genai_version
            versions['Google SDK'] = google_genai_version
        except Exception:
            versions['Google SDK'] = '-'

        try:
            from xai_sdk import __version__ as xai_sdk_version
            versions['xAI SDK'] = xai_sdk_version
        except Exception:
            versions['xAI SDK'] = '-'

        safe_emit(self.signals, 'result', versions)


class About:

    COPYRIGHT_YEARS = "2022-2026"
    VERSION_KEYS = (
        'Python',
        'OpenAI SDK',
        'LlamaIndex',
        'Anthropic SDK',
        'Google SDK',
        'xAI SDK',
    )

    def __init__(self, window=None):
        """
        About dialog

        :param window: Window instance
        """
        self.window = window
        self.thanks = None
        self._lib_versions = None
        self._versions_worker = None

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

    def _get_versions_for_render(self) -> dict:
        if self._lib_versions is not None:
            return dict(self._lib_versions)
        return {key: '...' for key in self.VERSION_KEYS}

    def prepare_content(self) -> str:
        """
        Get info text. SDK versions are rendered from the async cache; before
        the first load each version slot contains a lightweight placeholder.

        :return: info text
        """
        versions_str = self.build_versions_str(
            self._get_versions_for_render(),
            break_after="LlamaIndex",
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

        data = f"{label_version}: {version}, {platform}\n" \
               f"{label_build}: {build.replace('.', '-')}\n\n" \
               f"{versions_str}\n\n" \
               f"{label_website}: {website}\n" \
               f"{label_github}: {github}\n" \
               f"{label_docs}: {docs}\n\n" \
               f"(c) {self.COPYRIGHT_YEARS} {author}\n" \
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

        content = QLabel()
        content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content.setWordWrap(True)
        content.setContentsMargins(2, 10, 2, 0)
        self.window.ui.nodes['dialog.about.content'] = content

        thanks = QLabel(trans('about.thanks'))
        thanks.setContentsMargins(2, 0, 2, 0)
        self.window.ui.nodes['dialog.about.thanks'] = thanks

        thanks_content = QPlainTextEdit()
        thanks_content.setReadOnly(True)
        thanks_content.setPlainText("")
        thanks_content.setStyleSheet("font-size: 11px;")
        self.window.ui.nodes['dialog.about.thanks.content'] = thanks_content

        layout = QVBoxLayout()
        layout.addWidget(logo_label)
        layout.addWidget(self.window.ui.nodes['dialog.about.content'])
        layout.addWidget(self.window.ui.nodes['dialog.about.thanks'])
        layout.addWidget(self.window.ui.nodes['dialog.about.thanks.content'])
        layout.addStretch(1)
        layout.addLayout(buttons_layout)

        self.window.ui.dialog['info.' + id] = InfoDialog(self.window, id)
        self.window.ui.dialog['info.' + id].setLayout(layout)
        self.window.ui.dialog['info.' + id].setWindowTitle(trans("dialog.about.title"))

    def _render_content(self):
        node = self.window.ui.nodes.get('dialog.about.content')
        if node is not None:
            node.setText(self.prepare_content())

    def _start_versions_load(self):
        if self._lib_versions is not None or self._versions_worker is not None:
            return

        worker = AboutVersionsWorker()
        self._versions_worker = worker
        worker.signals.result.connect(self._on_versions_loaded)
        QThreadPool.globalInstance().start(worker)

    @Slot(object)
    def _on_versions_loaded(self, versions):
        self._versions_worker = None

        loaded = {}
        if isinstance(versions, dict):
            for key in self.VERSION_KEYS:
                value = versions.get(key, '-')
                loaded[key] = str(value) if value not in (None, '') else '-'
        else:
            loaded = {key: '-' for key in self.VERSION_KEYS}

        self._lib_versions = loaded
        self._render_content()

    def prepare(self):
        """Update dialog content."""
        # Render immediately without importing SDK modules. Starting the worker
        # on the next event-loop turn lets the dialog become visible first.
        self._render_content()
        QTimer.singleShot(0, self._start_versions_load)

        people = str(self.get_thanks())
        self.window.ui.nodes['dialog.about.thanks.content'].setPlainText(people)
        if people == "":
            self.window.ui.nodes['dialog.about.thanks'].hide()
            self.window.ui.nodes['dialog.about.thanks.content'].hide()
        else:
            self.window.ui.nodes['dialog.about.thanks'].show()
            self.window.ui.nodes['dialog.about.thanks.content'].show()
