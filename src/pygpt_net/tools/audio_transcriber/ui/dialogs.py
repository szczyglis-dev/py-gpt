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
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel, QVBoxLayout, QCheckBox, QMenuBar

from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.ui.widget.textarea.editor import CodeEditor
from pygpt_net.utils import trans


class AudioTranscribe:

    def __init__(self, window=None):
        """
        Audio Transcribe dialog

        :param window: Window instance
        """
        self.window = window
        self.menu_bar = None
        self.file_menu = None
        self.actions = {}

    def setup_menu(self, parent=None) -> QMenuBar:
        """Setup audio transcriber dialog menu"""
        self.menu_bar = QMenuBar(parent)
        self.file_menu = self.menu_bar.addMenu(trans("menu.file"))
        t = self.window.tools.get("transcriber")

        self.actions["open"] = QAction(QIcon(":/icons/folder.svg"), trans("action.open"), self.menu_bar)
        self.actions["open"].triggered.connect(lambda checked=False, t=t: t.open_file())

        self.actions["save_as"] = QAction(QIcon(":/icons/save.svg"), trans("action.save_as"), self.menu_bar)
        self.actions["save_as"].triggered.connect(lambda checked=False, t=t: t.save_as_file())

        self.actions["exit"] = QAction(QIcon(":/icons/logout.svg"), trans("menu.file.exit"), self.menu_bar)
        self.actions["exit"].triggered.connect(lambda checked=False, t=t: t.close())

        self.file_menu.addAction(self.actions["open"])
        self.file_menu.addAction(self.actions["save_as"])
        self.file_menu.addAction(self.actions["exit"])
        return self.menu_bar

    def setup(self):
        """Setup transcriber dialog"""
        id = 'audio.transcribe'
        u = self.window.ui
        t = self.window.tools.get("transcriber")

        u.dialog['audio.transcribe'] = AudioTranscribeDialog(self.window)
        dlg = u.dialog['audio.transcribe']

        u.editor[id] = CodeEditor(self.window)
        u.editor[id].setReadOnly(False)
        u.editor[id].setProperty('class', 'code-editor')

        u.nodes['audio.transcribe.convert_video'] = QCheckBox(trans("audio.transcribe.auto_convert"))
        u.nodes['audio.transcribe.convert_video'].setChecked(True)
        u.nodes['audio.transcribe.convert_video'].clicked.connect(lambda checked=False, t=t: t.toggle_auto_convert())

        u.nodes['audio.transcribe.clear'] = QPushButton(trans("dialog.logger.btn.clear"))
        u.nodes['audio.transcribe.clear'].clicked.connect(self.clear)

        u.nodes['audio.transcribe.open'] = QPushButton(trans("audio.transcribe.open"))
        u.nodes['audio.transcribe.open'].clicked.connect(lambda checked=False, t=t: t.open_file())

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(u.nodes['audio.transcribe.clear'])
        bottom_layout.addWidget(u.nodes['audio.transcribe.open'])

        u.nodes['audio.transcribe.title'] = HelpLabel(trans("audio.transcribe.tip"))
        u.nodes['audio.transcribe.status'] = QLabel("...")
        u.nodes['audio.transcribe.status'].setAlignment(Qt.AlignCenter)
        u.nodes['audio.transcribe.status'].setWordWrap(True)

        layout = QVBoxLayout()
        layout.setMenuBar(self.setup_menu(dlg))
        layout.addWidget(u.editor[id])
        layout.addWidget(u.nodes['audio.transcribe.title'])
        layout.addLayout(bottom_layout)
        layout.addWidget(u.nodes['audio.transcribe.convert_video'])
        layout.addWidget(u.nodes['audio.transcribe.status'])

        dlg.setLayout(layout)
        dlg.setWindowTitle(trans("audio.transcribe.title"))

    def clear(self):
        """Clear transcribe dialog"""
        self.window.tools.get("transcriber").clear()


class AudioTranscribeDialog(BaseDialog):
    def __init__(self, window=None, id=None):
        """
        Audio Transcribe Dialog

        :param window: main window
        :param id: configurator id
        """
        super(AudioTranscribeDialog, self).__init__(window, id)
        self.window = window
        self.id = id  # id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.cleanup()
        super(AudioTranscribeDialog, self).closeEvent(event)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key press event
        """
        if event.key() == Qt.Key_Escape:
            self.cleanup()
            self.close()
        else:
            super(AudioTranscribeDialog, self).keyPressEvent(event)

    def cleanup(self):
        """
        Cleanup on close
        """
        self.window.tools.get("transcriber").on_close()