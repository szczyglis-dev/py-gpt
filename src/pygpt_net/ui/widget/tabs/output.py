#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.29 14:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QTabWidget, QMenu
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QIcon

from pygpt_net.utils import trans
import pygpt_net.icons_rc


class OutputTabs(QTabWidget):
    def __init__(self, window=None):
        super(OutputTabs, self).__init__(window)
        self.window = window

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            start = self.window.controller.notepad.start_tab_idx
            clicked_tab_index = self.tabBar().tabAt(event.pos())

            if clicked_tab_index >= start:
                idx = clicked_tab_index - (start - 1)
                self.show_context_menu(clicked_tab_index, event.globalPos())

        super(OutputTabs, self).mousePressEvent(event)

    def show_context_menu(self, index, global_pos):
        context_menu = QMenu()
        start = self.window.controller.notepad.start_tab_idx
        actions = {}
        idx = index - (start - 1)
        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('action.rename'), self)
        actions['edit'].triggered.connect(
            lambda: self.rename_tab(idx))
        context_menu.addAction(actions['edit'])
        context_menu.exec(global_pos)

    @Slot()
    def rename_tab(self, index):
        self.window.controller.notepad.rename(index)
