#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.09 23:00:00                  #
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
        self.setMinimumHeight(1)

    def mousePressEvent(self, event):
        """
        Mouse press event
        :param event: event
        """
        if event.button() == Qt.RightButton:
            clicked_tab_index = self.tabBar().tabAt(event.pos())

            # notepad
            start = self.window.controller.notepad.start_tab_idx
            if clicked_tab_index >= start:
                idx = clicked_tab_index - (start - 1)
                self.show_notepad_menu(clicked_tab_index, event.globalPos())

            # files
            elif clicked_tab_index == 1:
                self.show_files_menu(clicked_tab_index, event.globalPos())

        super(OutputTabs, self).mousePressEvent(event)

    def show_notepad_menu(self, index, global_pos):
        """
        Show notepad menu

        :param index: index
        :param global_pos: global position
        """
        context_menu = QMenu()
        start = self.window.controller.notepad.start_tab_idx
        actions = {}
        idx = index - (start - 1)
        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('action.rename'), self)
        actions['edit'].triggered.connect(
            lambda: self.rename_tab(idx))
        context_menu.addAction(actions['edit'])
        context_menu.exec(global_pos)

    def show_files_menu(self, index, global_pos):
        """
        Show files menu

        :param index: index
        :param global_pos: global position
        """
        context_menu = QMenu()
        actions = {}
        actions['refresh'] = QAction(QIcon(":/icons/reload.svg"), trans('action.refresh'), self)
        actions['refresh'].triggered.connect(
            lambda: self.window.controller.files.update_explorer())
        context_menu.addAction(actions['refresh'])
        context_menu.exec(global_pos)

    @Slot()
    def rename_tab(self, index):
        """
        Rename tab
        :param index: index
        """
        self.window.controller.notepad.rename(index)
