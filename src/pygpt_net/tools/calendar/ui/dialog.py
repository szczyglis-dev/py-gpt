#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
"""Single Calendar dialog with an independent month-grid session."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QVBoxLayout


class CalendarDialog(QDialog):
    def __init__(self, tool):
        super().__init__(tool.window)
        self.tool = tool
        self._released = False
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowIcon(QIcon(tool.tab_icon))
        tool.add_lang_mapping(self, tool.tab_title, setter='setWindowTitle')
        self.resize(800, 850)
        self.widget = tool.new_frontend(parent=self)
        QVBoxLayout(self).addWidget(self.widget)
        tool.register_surface(self.widget.session, self.widget, dialog_id=tool.dialog_id)

    def release(self):
        if self._released:
            return
        self._released = True
        self.widget.on_delete()
        self.tool.window.ui.dialog.pop(self.tool.dialog_id, None)
        if self.tool.dialog is self:
            self.tool.dialog = None

    def closeEvent(self, event):
        super().closeEvent(event)
        if event.isAccepted():
            self.release()

    def done(self, result):
        self.release()
        super().done(result)
