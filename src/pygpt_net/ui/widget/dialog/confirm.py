#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.27 09:30:00                  #
# ================================================== #

import sys
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QLabel, QHBoxLayout, QVBoxLayout, QPushButton

from pygpt_net.utils import trans


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
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)  # always on top

        # Buttons
        self.window.ui.nodes['dialog.confirm.btn.yes'] = QPushButton(trans('dialog.confirm.yes'))
        self.window.ui.nodes['dialog.confirm.btn.yes'].clicked.connect(
            lambda: self.window.controller.dialogs.confirm.accept(self.type, self.id, self.parent_object))

        self.window.ui.nodes['dialog.confirm.btn.no'] = QPushButton(trans('dialog.confirm.no'))
        self.window.ui.nodes['dialog.confirm.btn.no'].clicked.connect(
            lambda: self.window.controller.dialogs.confirm.dismiss(self.type, self.id))

        # Always make the neutral action (No/Cancel) the default/active one.
        # This ensures Enter triggers the safe option by default.
        self._apply_neutral_default()

        # Bottom button row with platform-specific ordering
        # Windows: affirmative on the left, neutral on the right
        # Linux/macOS: neutral on the left, affirmative on the right
        bottom = QHBoxLayout()
        if self._affirmative_on_left():
            bottom.addWidget(self.window.ui.nodes['dialog.confirm.btn.yes'])
            bottom.addWidget(self.window.ui.nodes['dialog.confirm.btn.no'])
        else:
            bottom.addWidget(self.window.ui.nodes['dialog.confirm.btn.no'])
            bottom.addWidget(self.window.ui.nodes['dialog.confirm.btn.yes'])

        self.layout = QVBoxLayout()
        self.message = QLabel("")
        self.message.setContentsMargins(10, 10, 10, 10)
        self.message.setAlignment(Qt.AlignCenter)
        self.message.setMinimumWidth(400)
        self.message.setWordWrap(True)
        self.layout.addWidget(self.message)
        self.layout.addLayout(bottom)
        self.setLayout(self.layout)

    def _affirmative_on_left(self) -> bool:
        """
        Decide button order depending on the platform.
        Returns True on Windows, False otherwise (Linux/macOS).
        """
        return sys.platform.startswith('win')

    def closeEvent(self, event):
        """
        Close event handler

        :param event: close event
        """
        self.window.controller.dialogs.confirm.dismiss(self.type, self.id)
        super(ConfirmDialog, self).closeEvent(event)

    def showEvent(self, event):
        """
        Ensure neutral button is default/active on every show.

        Using a single-shot timer defers focus/default restoration until
        after the dialog becomes visible, which prevents focus being stolen
        by the window manager.
        """
        super(ConfirmDialog, self).showEvent(event)
        QTimer.singleShot(0, self._apply_neutral_default)

    def _apply_neutral_default(self):
        """
        Set the neutral action (No/Cancel) as default and active.
        Always called on construction and each time the dialog is shown.
        """
        btn_no = self.window.ui.nodes.get('dialog.confirm.btn.no')
        btn_yes = self.window.ui.nodes.get('dialog.confirm.btn.yes')
        if not btn_no or not btn_yes:
            return

        # Make sure affirmative button cannot become default by leftover state
        btn_yes.setAutoDefault(False)
        btn_yes.setDefault(False)

        # Make neutral (No/Cancel) the active default and take focus
        btn_no.setAutoDefault(True)
        btn_no.setDefault(True)
        btn_no.setFocus()