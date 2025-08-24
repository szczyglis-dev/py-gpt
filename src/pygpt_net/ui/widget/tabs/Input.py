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

from PySide6.QtWidgets import QTabWidget, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans


class InputTabs(QTabWidget):
    def __init__(self, window=None):
        super().__init__(window)
        self.window = window
        self._attachments_tab_index = 1
        self._context_menu = QMenu(self)
        self._action_clear = QAction(QIcon(":/icons/delete.svg"), trans('attachments.btn.clear'), self)
        self._action_clear.triggered.connect(self._on_clear_triggered)
        self._context_menu.addAction(self._action_clear)

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: QMouseEvent
        """
        if event.button() == Qt.RightButton:
            tb = self.tabBar()
            pos_in_tabbar = tb.mapFrom(self, event.pos())
            if tb.tabAt(pos_in_tabbar) == self._attachments_tab_index:
                self.show_context_menu(event.globalPos())

        super().mousePressEvent(event)

    def show_context_menu(self, global_pos):
        """
        Show context menu for attachments tab

        :param global_pos: QPoint
        """
        self._action_clear.setText(trans('attachments.btn.clear'))
        self._context_menu.exec(global_pos)

    def _on_clear_triggered(self, checked=False):
        self.window.controller.attachment.clear()