#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 07:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QTabWidget, QMenu, QPushButton
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QIcon

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class AddButton(QPushButton):
    def __init__(self, window=None, column=None, tabs=None):
        super(AddButton, self).__init__(QIcon(":/icons/add.svg"), "", window)
        self.window = window
        self.column = column
        self.tabs = tabs
        self.setFixedSize(30, 25)
        self.setFlat(True)
        self.clicked.connect(
            lambda: self.window.controller.ui.tabs.new_tab(self.column.get_idx())
        )
        self.setObjectName('tab-add')
        self.setProperty('tabAdd', True)
        self.setToolTip(trans('action.tab.add.chat'))

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: event
        """
        if event.button() == Qt.RightButton:
            idx = 0
            column_idx = self.column.get_idx()
            self.show_menu(idx, column_idx, event.globalPos())
        super(AddButton, self).mousePressEvent(event)

    def show_menu(self, index: int, column_idx: int, global_pos):
        """
        Show context menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        context_menu.exec(global_pos)

    def prepare_menu(self, index: int, column_idx: int) -> QMenu:
        """
        Prepare and return context menu

        :param index: index
        :param column_idx: column index
        :return: menu
        """
        menu = QMenu(self)

        actions = {}
        actions['add_chat'] = QAction(QIcon(":/icons/add.svg"), trans('action.tab.add.chat'), self)
        actions['add_chat'].triggered.connect(
            lambda: self.tabs.add_tab(index, column_idx, Tab.TAB_CHAT)
        )
        actions['add_notepad'] = QAction(QIcon(":/icons/add.svg"), trans('action.tab.add.notepad'), self)
        actions['add_notepad'].triggered.connect(
            lambda: self.tabs.add_tab(index, column_idx, Tab.TAB_NOTEPAD)
        )

        # add chat, add notepad
        menu.addAction(actions['add_chat'])
        menu.addAction(actions['add_notepad'])

        # add tools submenu
        self.window.controller.tools.append_tab_menu(self, menu, index, column_idx)

        return menu

class OutputTabs(QTabWidget):
    def __init__(self, window=None, column=None):
        super(OutputTabs, self).__init__(window)
        self.window = window
        self.active = True
        self.column = column
        self.setMinimumHeight(1)
        self.owner = None
        self.setMovable(True)
        self.init()

    def set_active(self, active: bool):
        """Set the active state of the tab bar."""
        self.active = active
        if self.active:
            self.setStyleSheet("QTabBar::tab { border-bottom-width: 2px; }")
        else:
            self.setStyleSheet("QTabBar::tab { border-bottom-width: 0px; }")

    def init(self):
        """Initialize"""
        # create the [+] button
        add_button = AddButton(self.window, self.column, self)

        # add the button to the top right corner of the tab bar
        self.setCornerWidget(add_button, corner=Qt.TopRightCorner)

        # connect signals
        self.currentChanged.connect(
            lambda: self.window.controller.ui.tabs.on_tab_changed(self.currentIndex(), self.column.get_idx())
        )
        self.tabBarClicked.connect(
            lambda: self.window.controller.ui.tabs.on_tab_clicked(self.currentIndex(), self.column.get_idx())
        )
        self.tabBarDoubleClicked.connect(
            lambda: self.window.controller.ui.tabs.on_tab_dbl_clicked(self.currentIndex(), self.column.get_idx())
        )
        self.tabCloseRequested.connect(
            lambda: self.window.controller.ui.tabs.on_tab_closed(self.currentIndex(), self.column.get_idx())
        )
        self.tabBar().tabMoved.connect(
            lambda: self.window.controller.ui.tabs.on_tab_moved(self.currentIndex(), self.column.get_idx())
        )

    def get_column(self):
        """
        Get column

        :return: OutputColumn
        """
        return self.column

    def setOwner(self, owner: Tab):
        """
        Set internal tab instance

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
            column_idx = self.column.get_idx()
            tab = self.window.core.tabs.get_tab_by_index(idx, column_idx)
            if tab is not None:
                if tab.type == Tab.TAB_NOTEPAD:
                    self.show_notepad_menu(idx, column_idx, event.globalPos())  # notepad
                elif tab.type == Tab.TAB_CHAT:
                    self.show_chat_menu(idx, column_idx, event.globalPos())  # chat
                elif tab.type == Tab.TAB_FILES:
                    self.show_files_menu(idx, column_idx, event.globalPos())  # files
                elif tab.type == Tab.TAB_TOOL:
                    self.show_tool_menu(idx, column_idx, event.globalPos())  # tool
                else:
                    self.show_default_menu(idx, column_idx, event.globalPos()) # default
        super(OutputTabs, self).mousePressEvent(event)

    def prepare_menu(self, index: int, column_idx: int) -> QMenu:
        """
        Prepare and return context menu

        :param index: index
        :param column_idx: column index
        :return: menu
        """
        menu = QMenu(self)

        actions = {}
        actions['add_chat'] = QAction(QIcon(":/icons/add.svg"), trans('action.tab.add.chat'), self)
        actions['add_chat'].triggered.connect(
            lambda: self.add_tab(index, column_idx, Tab.TAB_CHAT)
        )
        actions['add_notepad'] = QAction(QIcon(":/icons/add.svg"), trans('action.tab.add.notepad'), self)
        actions['add_notepad'].triggered.connect(
            lambda: self.add_tab(index, column_idx, Tab.TAB_NOTEPAD)
        )
        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('action.rename'), self)
        actions['edit'].triggered.connect(
            lambda: self.rename_tab(index, column_idx)
        )
        actions['move_right'] = QAction(QIcon(":/icons/forward"), trans('action.tab.move.right'), self)
        actions['move_right'].triggered.connect(
            lambda: self.window.controller.ui.tabs.move_tab(index, column_idx, 1)
        )
        actions['move_left'] = QAction(QIcon(":/icons/back"), trans('action.tab.move.left'), self)
        actions['move_left'].triggered.connect(
            lambda: self.window.controller.ui.tabs.move_tab(index, column_idx, 0)
        )

        # add chat, add notepad
        menu.addAction(actions['add_chat'])
        menu.addAction(actions['add_notepad'])

        # add tools submenu
        self.window.controller.tools.append_tab_menu(self, menu, index, column_idx)

        # rename tab
        menu.addAction(actions['edit'])

        # move tab left, move tab right
        if column_idx != 0:
            menu.addAction(actions['move_left'])
        if column_idx != 1:
            menu.addAction(actions['move_right'])

        return menu

    def show_notepad_menu(self, index: int, column_idx: int, global_pos):
        """
        Show notepad menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        actions = {}
        actions['close'] = QAction(QIcon(":/icons/close.svg"), trans('action.tab.close'), self)
        actions['close'].triggered.connect(
            lambda: self.close_tab(index, column_idx)
        )
        actions['close_all'] = QAction(QIcon(":/icons/close.svg"), trans('action.tab.close_all.notepad'), self)
        actions['close_all'].triggered.connect(
            lambda: self.close_all(Tab.TAB_NOTEPAD, column_idx)
        )
        context_menu.addAction(actions['close'])

        if self.window.core.tabs.count_by_type(Tab.TAB_NOTEPAD) > 1:
            context_menu.addAction(actions['close_all'])

        context_menu.exec(global_pos)

    def show_chat_menu(self, index: int, column_idx: int, global_pos):
        """
        Show chat menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        actions = {}
        actions['close'] = QAction(QIcon(":/icons/close.svg"), trans('action.tab.close'), self)
        actions['close'].triggered.connect(
            lambda: self.close_tab(index, column_idx)
        )
        actions['close_all'] = QAction(QIcon(":/icons/close.svg"), trans('action.tab.close_all.chat'), self)
        actions['close_all'].triggered.connect(
            lambda: self.close_all(Tab.TAB_CHAT, column_idx)
        )

        # at least one chat tab must be open
        if self.window.core.tabs.count_by_type(Tab.TAB_CHAT) > 1:
            context_menu.addAction(actions['close'])
            context_menu.addAction(actions['close_all'])

        context_menu.exec(global_pos)

    def show_files_menu(self, index: int, column_idx: int, global_pos):
        """
        Show files menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        actions = {}
        actions['refresh'] = QAction(QIcon(":/icons/reload.svg"), trans('action.refresh'), self)
        actions['refresh'].triggered.connect(
            lambda: self.window.controller.files.update_explorer()
        )
        context_menu.addAction(actions['refresh'])
        context_menu.exec(global_pos)

    def show_tool_menu(self, index: int, column_idx: int, global_pos):
        """
        Show tool menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        actions = {}
        actions['close'] = QAction(QIcon(":/icons/close.svg"), trans('action.tab.close'), self)
        actions['close'].triggered.connect(
            lambda: self.close_tab(index, column_idx)
        )
        context_menu.addAction(actions['close'])
        context_menu.exec(global_pos)

    def show_default_menu(self, index: int, column_idx: int, global_pos):
        """
        Show default menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        context_menu.exec(global_pos)

    @Slot()
    def rename_tab(self, index: int, column_idx: int):
        """
        Rename tab

        :param index: index
        :param column_idx: column index
        """
        self.window.controller.ui.tabs.rename(index, column_idx)

    @Slot()
    def close_tab(self, index: int, column_idx: int):
        """
        Close tab

        :param index: index
        :param column_idx: column index
        """
        self.window.controller.ui.tabs.close(index, column_idx)

    @Slot()
    def close_all(self, type, column_idx: int):
        """
        Close all tabs

        :param type: type
        :param column_idx: column index
        """
        self.window.controller.ui.tabs.close_all(type, column_idx)

    @Slot()
    def add_tab(self, index: int, column_idx: int, type: int, tool_id: str = None):
        """
        Add a new tab

        :param index: index
        :param column_idx: column index
        :param type: type
        :param tool_id: tool id
        """
        self.window.controller.ui.tabs.append(
            type=type,
            tool_id=tool_id,
            idx=index,
            column_idx=column_idx,
        )
