#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.16 16:00:00                  #
# ================================================== #

import os
import webbrowser

from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QPixmap, QAction, QIcon, QCursor
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QPushButton, QPlainTextEdit, QHBoxLayout, QCheckBox, \
    QLineEdit, QToolTip

from pygpt_net.ui.widget.element.labels import TitleLabel
from pygpt_net.utils import trans
import pygpt_net.icons_rc


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

        # www
        self.www = QPushButton(trans('update.download'))
        self.www.setCursor(Qt.PointingHandCursor)
        self.www.clicked.connect(
            lambda: self.window.controller.dialogs.info.goto_update())

        # snap store
        self.snap_store = QPushButton(trans('update.snap'))
        self.snap_store.setCursor(Qt.PointingHandCursor)
        self.snap_store.clicked.connect(
            lambda: self.window.controller.dialogs.info.goto_snap())

        self.changelog = QPlainTextEdit()
        self.changelog.setReadOnly(True)
        self.changelog.setMinimumHeight(200)

        logo_label = QLabel()
        path = os.path.abspath(
            os.path.join(self.window.core.config.get_app_path(), 'data', 'logo.png'))
        pixmap = QPixmap(path)
        logo_label.setPixmap(pixmap)

        buttons = QHBoxLayout()
        buttons.addWidget(self.www)
        buttons.addWidget(self.snap_store)

        # checkbox startup
        self.checkbox_startup = QCheckBox(trans("updater.check.launch"))
        self.checkbox_startup.stateChanged.connect(
            lambda: self.window.controller.launcher.toggle_update_check(
                self.checkbox_startup.isChecked()))

        if self.window.core.config.get('updater.check.launch'):
            self.checkbox_startup.setChecked(True)
        else:
            self.checkbox_startup.setChecked(False)

        # update cmd/buttons
        self.cmd = UpdateCmdLabel(self.window, "")
        self.download_file = QPushButton("Download")
        self.download_file.setCursor(Qt.PointingHandCursor)
        self.download_file.clicked.connect(
            lambda: self.start_download())
        self.download_link = ""

        # info upgrade now
        self.info_upgrade = QLabel(trans("update.info.upgrade"))
        self.info_upgrade.setWordWrap(True)
        self.info_upgrade.setAlignment(Qt.AlignCenter)
        self.info_upgrade.setStyleSheet("font-size: 12px; margin: 0px 0px 5px 0px;")
        self.info_upgrade.setMaximumHeight(40)

        # layout
        self.layout = QVBoxLayout()
        self.message = QLabel("")
        self.message.setStyleSheet("margin: 10px 0px 10px 0px;")
        self.info = TitleLabel(trans("update.info"))
        self.info.setWordWrap(True)
        self.info.setAlignment(Qt.AlignCenter)
        self.info.setStyleSheet("font-weight: bold; font-size: 12px; margin: 10px 0px 10px 0px;")
        self.info.setMaximumHeight(60)
        self.layout.addWidget(logo_label)
        self.layout.addWidget(self.info)
        self.layout.addWidget(self.info_upgrade)
        self.layout.addWidget(self.cmd)
        self.layout.addWidget(self.download_file)
        self.layout.addWidget(self.message)
        self.layout.addWidget(self.changelog, 1)
        self.layout.addWidget(self.checkbox_startup)
        self.layout.addLayout(buttons)
        self.layout.addStretch()
        self.setLayout(self.layout)

    def start_download(self):
        """
        Download file
        """
        webbrowser.open(self.download_link)

    def set_data(
            self,
            is_new: bool,
            version: str,
            build: str,
            changelog: str,
            download_windows: str,
            download_linux: str
    ):
        """
        Set update data

        :param is_new: is new version
        :param version: version
        :param build: build
        :param changelog: changelog
        :param download_windows: download link for windows
        :param download_linux: download link for linux
        """
        # prepare data
        info = trans("update.info")
        if not is_new:
            info = trans('update.info.none')
        txt = trans('update.new_version') + ": " \
            + str(version) + " (" + trans('update.released') + ": " + str(build) + ")"
        txt += "\n" + trans('update.current_version') + ": " + self.window.meta['version']

        self.info.setText(info)
        self.changelog.setPlainText(changelog)
        self.message.setText(txt)

        # show / hide upgrade info
        if is_new:
            self.info_upgrade.setVisible(True)
        else:
            self.info_upgrade.setVisible(False)

        # check platform
        self.cmd.setVisible(False)
        self.download_file.setVisible(False)
        self.snap_store.setVisible(False)
        if self.window.core.platforms.is_snap():  # snap
            self.cmd.setText("sudo snap refresh pygpt")
            self.cmd.setVisible(True)
        elif self.window.core.config.is_compiled():  # compiled
            if self.window.core.platforms.is_windows():
                self.download_link = download_windows
                self.download_file.setText("{} .msi ({})".format(trans("action.download"), version))
            elif self.window.core.platforms.is_linux():
                self.download_link = download_linux
                self.download_file.setText("{} .tar.gz ({})".format(trans("action.download"), version))
            self.download_file.setVisible(True)
        else:  # pip
            self.cmd.setText("pip install --upgrade pygpt-net")
            self.cmd.setVisible(True)

        # show snap store button
        if self.window.core.platforms.is_linux():
            self.snap_store.setVisible(True)


class UpdateCmdLabel(QLineEdit):
    def __init__(self, window=None, text: str = ""):
        """
        Command label

        :param window: main window
        :param text: text
        """
        super(UpdateCmdLabel, self).__init__(window)
        self.window = window
        self.setStyleSheet(
            "font-weight: bold;"
            "font-size: 14px;"
            "padding: 5px;"
            "background: #020202;"
            "color: #fff;"
            "text-align: center;"
        )
        self.setText(text)
        self.setAlignment(Qt.AlignCenter)
        self.setReadOnly(True)
        self.action = QAction(self)
        self.action.setIcon(QIcon(":/icons/copy.svg"))
        self.action.triggered.connect(self.copy_to_clipboard)
        self.addAction(self.action, QLineEdit.TrailingPosition)

    def copy_to_clipboard(self):
        """Copy to clipboard"""
        self.selectAll()
        self.copy()
        self.deselect()
        self.action.setIcon(QIcon(":/icons/check.svg"))
        QToolTip.showText(QCursor.pos(), trans("clipboard.copied"), self, QRect(), 2000)
        timer = QTimer()
        timer.singleShot(2000, self.reset_icon)

    def reset_icon(self):
        """Reset icon"""
        self.action.setIcon(QIcon(":/icons/copy.svg"))
