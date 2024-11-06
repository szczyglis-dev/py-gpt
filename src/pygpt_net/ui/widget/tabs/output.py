#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QTabWidget, QMenu
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QIcon

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class OutputTabs(QTabWidget):
    def __init__(self, window=None):
        super(OutputTabs, self).__init__(window)
        self.window = window
        self.setMinimumHeight(1)
        self.owner = None
        self.setMovable(True)

    def setOwner(self, owner: Tab):
        """
        Set parent

        :param owner: parent tab instance
        """
        self.owner = owner

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: event
        """
        if event.button() == Qt.RightButton:
            idx = self.tabBar().tabAt(event.pos())
            tab = self.window.core.tabs.get_tab_by_index(idx)
            if tab is not None:
                if tab.type == Tab.TAB_NOTEPAD:
                    self.show_notepad_menu(idx, event.globalPos())  # notepad
                elif tab.type == Tab.TAB_CHAT:
                    self.show_chat_menu(idx, event.globalPos())  # chat
                elif tab.type == Tab.TAB_FILES:
                    self.show_files_menu(idx, event.globalPos())  # files
                else:
                    self.show_default_menu(idx, event.globalPos()) # default
        super(OutputTabs, self).mousePressEvent(event)

    def get_common_actions(self, index):
        """
        Get common actions

        :param index: index
        :return: dict
        """
        actions = {}
        actions['add_chat'] = QAction(QIcon(":/icons/add.svg"), trans('action.tab.add.chat'), self)
        actions['add_chat'].triggered.connect(
            lambda: self.add_tab(index, Tab.TAB_CHAT)
        )
        actions['add_notepad'] = QAction(QIcon(":/icons/add.svg"), trans('action.tab.add.notepad'), self)
        actions['add_notepad'].triggered.connect(
            lambda: self.add_tab(index, Tab.TAB_NOTEPAD)
        )
        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('action.rename'), self)
        actions['edit'].triggered.connect(
            lambda: self.rename_tab(index)
        )
        return actions

    def show_notepad_menu(self, index, global_pos):
        """
        Show notepad menu

        :param index: index
        :param global_pos: global position
        """
        context_menu = QMenu()
        actions = self.get_common_actions(index)
        actions['close'] = QAction(QIcon(":/icons/close.svg"), trans('action.tab.close'), self)
        actions['close'].triggered.connect(
            lambda: self.close_tab(index)
        )
        actions['close_all'] = QAction(QIcon(":/icons/close.svg"), trans('action.tab.close_all.notepad'), self)
        actions['close_all'].triggered.connect(
            lambda: self.close_all(Tab.TAB_NOTEPAD)
        )
        context_menu.addAction(actions['add_chat'])
        context_menu.addAction(actions['add_notepad'])
        context_menu.addAction(actions['edit'])
        context_menu.addAction(actions['close'])

        if self.window.core.tabs.count_by_type(Tab.TAB_NOTEPAD) > 1:
            context_menu.addAction(actions['close_all'])
        context_menu.exec(global_pos)

    def show_chat_menu(self, index, global_pos):
        """
        Show chat menu

        :param index: index
        :param global_pos: global position
        """
        context_menu = QMenu()
        actions = self.get_common_actions(index)
        actions['close'] = QAction(QIcon(":/icons/close.svg"), trans('action.tab.close'), self)
        actions['close'].triggered.connect(
            lambda: self.close_tab(index)
        )
        actions['close_all'] = QAction(QIcon(":/icons/close.svg"), trans('action.tab.close_all.chat'), self)
        actions['close_all'].triggered.connect(
            lambda: self.close_all(Tab.TAB_CHAT)
        )
        context_menu.addAction(actions['add_chat'])
        context_menu.addAction(actions['add_notepad'])
        context_menu.addAction(actions['edit'])

        # at least one chat tab must be open
        if self.window.core.tabs.count_by_type(Tab.TAB_CHAT) > 1:
            context_menu.addAction(actions['close'])

        if self.window.core.tabs.count_by_type(Tab.TAB_CHAT) > 1:
            context_menu.addAction(actions['close_all'])

        context_menu.exec(global_pos)

    def show_files_menu(self, index, global_pos):
        """
        Show files menu

        :param index: index
        :param global_pos: global position
        """
        context_menu = QMenu()
        actions = self.get_common_actions(index)
        actions['refresh'] = QAction(QIcon(":/icons/reload.svg"), trans('action.refresh'), self)
        actions['refresh'].triggered.connect(
            lambda: self.window.controller.files.update_explorer()
        )
        context_menu.addAction(actions['add_chat'])
        context_menu.addAction(actions['add_notepad'])
        context_menu.addAction(actions['refresh'])
        context_menu.addAction(actions['edit'])
        context_menu.exec(global_pos)

    def show_default_menu(self, index, global_pos):
        """
        Show default menu

        :param index: index
        :param global_pos: global position
        """
        context_menu = QMenu()
        actions = self.get_common_actions(index)
        context_menu.addAction(actions['add_chat'])
        context_menu.addAction(actions['add_notepad'])
        context_menu.addAction(actions['edit'])
        context_menu.exec(global_pos)

    @Slot()
    def rename_tab(self, index):
        """
        Rename tab
        :param index: index
        """
        self.window.controller.ui.tabs.rename(index)

    @Slot()
    def close_tab(self, index):
        """
        Close tab
        :param index: index
        """
        self.window.controller.ui.tabs.close(index)

    @Slot()
    def close_all(self, type):
        """
        Close all tabs
        :param type: type
        """
        self.window.controller.ui.tabs.close_all(type)

    @Slot()
    def add_tab(self, index, type):
        """
        Add tab
        :param index: index
        :param type: type
        """
        self.window.controller.ui.tabs.append(type, index)
