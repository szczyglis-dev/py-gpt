#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.09 23:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QTabWidget, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans
import pygpt_net.icons_rc


class InputTabs(QTabWidget):
    def __init__(self, window=None):
        super(InputTabs, self).__init__(window)
        self.window = window

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: QMouseEvent
        """
        if event.button() == Qt.RightButton:
            if self.tabBar().tabAt(event.pos()) == 1:  # attachments tab
                self.show_context_menu(event.globalPos())

        super(InputTabs, self).mousePressEvent(event)

    def show_context_menu(self, global_pos):
        """
        Show context menu for attachments tab

        :param global_pos: QPoint
        """
        context_menu = QMenu(self)
        actions = {}
        actions['clear'] = QAction(QIcon(":/icons/delete.svg"), trans('attachments.btn.clear'), self)
        actions['clear'].triggered.connect(
            lambda: self.window.controller.attachment.clear())
        context_menu.addAction(actions['clear'])
        context_menu.exec(global_pos)
