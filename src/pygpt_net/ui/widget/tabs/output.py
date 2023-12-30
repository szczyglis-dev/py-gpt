#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.30 02:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QTabWidget, QMenu
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans


class OutputTabs(QTabWidget):
    def __init__(self, parent=None):
        super(OutputTabs, self).__init__(parent)
        self.window = parent

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            clicked_tab_index = self.tabBar().tabAt(event.pos())

            if clicked_tab_index > 1:
                self.show_context_menu(clicked_tab_index, event.globalPos())

        super(OutputTabs, self).mousePressEvent(event)

    def show_context_menu(self, index, global_pos):
        context_menu = QMenu()
        actions = {}
        actions['edit'] = QAction(QIcon.fromTheme("edit-edit"), trans('action.rename'), self)
        actions['edit'].triggered.connect(
            lambda: self.rename_tab(index))
        context_menu.addAction(actions['edit'])
        context_menu.exec(global_pos)

    @Slot()
    def rename_tab(self, index):
        self.window.controller.notepad.rename(index)
