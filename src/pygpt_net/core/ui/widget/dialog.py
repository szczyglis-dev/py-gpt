#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QHBoxLayout, QDialogButtonBox, QVBoxLayout, QPushButton, QPlainTextEdit

from ...utils import trans
from .textarea import RenameInput


class DebugDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Debug window dialog

        :param window: Window instance
        :param id: debug window id
        """
        super(DebugDialog, self).__init__(window)
        self.window = window
        self.id = id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.window.debugger.active[self.id] = False
        self.window.controller.debug.update_menu()


class InfoDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Info window dialog

        :param window: main window
        :param id: info window id
        """
        super(InfoDialog, self).__init__(window)
        self.window = window
        self.id = id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.window.info.active[self.id] = False
        self.window.controller.info.update_menu()


class RenameDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Rename dialog

        :param window: main window
        :param id: info window id
        """
        super(RenameDialog, self).__init__(window)
        self.window = window
        self.id = id
        self.current = None
        self.input = RenameInput(window, id)
        self.input.setMinimumWidth(400)

        self.window.data['dialog.rename.btn.update'] = QPushButton(trans('dialog.rename.update'))
        self.window.data['dialog.rename.btn.update'].clicked.connect(
            lambda: self.window.controller.confirm.accept_rename(self.id, self.window.dialog['rename'].current,
                                                                 self.input.text()))

        self.window.data['dialog.rename.btn.dismiss'] = QPushButton(trans('dialog.rename.dismiss'))
        self.window.data['dialog.rename.btn.dismiss'].clicked.connect(
            lambda: self.window.controller.confirm.dismiss_rename())

        bottom = QHBoxLayout()
        bottom.addWidget(self.window.data['dialog.rename.btn.dismiss'])
        bottom.addWidget(self.window.data['dialog.rename.btn.update'])

        self.window.data['dialog.rename.label'] = QLabel(trans("dialog.rename.title"))

        layout = QVBoxLayout()
        layout.addWidget(self.window.data['dialog.rename.label'])
        layout.addWidget(self.input)
        layout.addLayout(bottom)

        self.setLayout(layout)


class EditorDialog(QDialog):
    def __init__(self, window=None, id=None, data_id=None):
        """
        EditorDialog

        :param window: main window
        :param id: configurator id
        :param data_id: data id
        """
        super(EditorDialog, self).__init__(window)
        self.window = window
        self.id = id
        self.data_id = data_id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        pass
        # self.window.settings.active[self.id] = False
        # self.window.controller.settings.close(self.id)
        # self.window.controller.settings.update()


class AlertDialog(QDialog):
    def __init__(self, window=None):
        """
        Alert dialog

        :param window: main window
        """
        super(AlertDialog, self).__init__(window)
        self.window = window
        self.setWindowTitle(trans('alert.title'))

        QBtn = QDialogButtonBox.Ok

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)

        self.layout = QVBoxLayout()
        self.message = QPlainTextEdit()
        self.message.setReadOnly(True)
        self.message.setMaximumWidth(400)
        self.layout.addWidget(self.message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class UpdateDialog(QDialog):
    def __init__(self, window=None):
        """
        Update dialog

        :param window: main window
        """
        super(UpdateDialog, self).__init__(window)
        self.window = window
        self.setParent(window)
        self.setWindowTitle(trans('update.title'))

        download = QPushButton(trans('update.download'))
        download.setCursor(Qt.PointingHandCursor)
        download.clicked.connect(
            lambda: self.window.controller.info.goto_update())

        self.changelog = QPlainTextEdit()
        self.changelog.setReadOnly(True)
        self.changelog.setMinimumHeight(200)

        logo_label = QLabel()
        path = os.path.abspath(
            os.path.join(self.window.config.get_root_path(), 'data', 'logo.png'))
        pixmap = QPixmap(path)
        logo_label.setPixmap(pixmap)

        self.layout = QVBoxLayout()
        self.message = QLabel("")
        info = QLabel(trans("update.info"))
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet(self.window.controller.theme.get_style('text_bold'))
        info.setStyleSheet("font-weight: bold; font-size: 12px; margin: 20px 0px 20px 0px;")
        info.setMaximumHeight(50)
        self.layout.addWidget(logo_label)
        self.layout.addWidget(info)
        self.layout.addWidget(self.message)
        self.layout.addWidget(self.changelog, 1)
        self.layout.addWidget(download)
        self.layout.addStretch()
        self.setLayout(self.layout)


class ConfirmDialog(QDialog):
    def __init__(self, window=None, type=None, id=None, parent_object=None):
        """
        Confirm dialog

        :param window: main window
        :param type: confirm type
        :param id: confirm id
        """
        super(ConfirmDialog, self).__init__(window)
        self.window = window
        self.type = type
        self.id = id
        self.parent_object = parent_object
        self.setWindowTitle(trans('dialog.confirm.title'))

        btn_yes = QPushButton(trans('dialog.confirm.yes'))
        btn_yes.clicked.connect(
            lambda: self.window.controller.confirm.accept(self.type, self.id, self.parent_object))

        btn_no = QPushButton(trans('dialog.confirm.no'))
        btn_no.clicked.connect(
            lambda: self.window.controller.confirm.dismiss(self.type, self.id))

        bottom = QHBoxLayout()
        bottom.addWidget(btn_no)
        bottom.addWidget(btn_yes)

        self.layout = QVBoxLayout()
        self.message = QLabel("")
        self.message.setContentsMargins(10, 10, 10, 10)
        self.message.setAlignment(Qt.AlignCenter)
        self.message.setMinimumWidth(400)
        self.layout.addWidget(self.message)
        self.layout.addLayout(bottom)
        self.setLayout(self.layout)


class FileEditorDialog(QDialog):
    def __init__(self, window=None):
        """
        File editor dialog

        :param window: main window
        """
        super(FileEditorDialog, self).__init__(window)
        self.window = window
        self.file = None

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.window.settings.active['editor'] = False
        self.window.controller.settings.close('editor')
        self.window.controller.settings.update()


class LoggerDialog(QDialog):
    def __init__(self, window=None):
        """
        Logger dialog

        :param window: main window
        """
        super(LoggerDialog, self).__init__(window)
        self.window = window

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.window.controller.debug.is_logger = False
        self.window.controller.debug.logger_close()
        self.window.controller.debug.update()


class GeneratedImageDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Image dialog

        :param window: main window
        :param id: info window id
        """
        super(GeneratedImageDialog, self).__init__(window)
        self.window = window
        self.id = id