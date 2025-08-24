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

from PySide6.QtWidgets import QTabWidget, QMenu, QPushButton
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QIcon, QGuiApplication

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans

_ICON_CACHE = {}

def icon(path: str) -> QIcon:
    if QGuiApplication.instance() is None:
        return QIcon()
    cached = _ICON_CACHE.get(path)
    if cached is None:
        cached = QIcon(path)
        _ICON_CACHE[path] = cached
    return cached

ICON_PATH_ADD = ':/icons/add.svg'
ICON_PATH_EDIT = ':/icons/edit.svg'
ICON_PATH_CLOSE = ':/icons/close.svg'
ICON_PATH_RELOAD = ':/icons/reload.svg'
ICON_PATH_FORWARD = ':/icons/forward'
ICON_PATH_BACK = ':/icons/back'


class AddButton(QPushButton):
    def __init__(self, window=None, column=None, tabs=None):
        super(AddButton, self).__init__(icon(ICON_PATH_ADD), "", window)
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
        menu.setAttribute(Qt.WA_DeleteOnClose, True)

        add_chat = QAction(icon(ICON_PATH_ADD), trans('action.tab.add.chat'), menu)
        add_chat.triggered.connect(
            lambda: self.tabs.add_tab(index, column_idx, Tab.TAB_CHAT)
        )
        add_notepad = QAction(icon(ICON_PATH_ADD), trans('action.tab.add.notepad'), menu)
        add_notepad.triggered.connect(
            lambda: self.tabs.add_tab(index, column_idx, Tab.TAB_NOTEPAD)
        )

        menu.addAction(add_chat)
        menu.addAction(add_notepad)

        self.window.controller.tools.append_tab_menu(self, menu, index, column_idx, self.tabs)

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
        self.currentChanged.connect(self._on_current_changed)
        self.tabBarClicked.connect(self._on_tabbar_clicked)
        self.tabBarDoubleClicked.connect(self._on_tabbar_dbl_clicked)
        self.tabCloseRequested.connect(self._on_tab_close_requested)
        self.tabBar().tabMoved.connect(self._on_tab_moved)

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
        menu.setAttribute(Qt.WA_DeleteOnClose, True)

        add_chat = QAction(icon(ICON_PATH_ADD), trans('action.tab.add.chat'), menu)
        add_chat.triggered.connect(
            lambda: self.add_tab(index, column_idx, Tab.TAB_CHAT)
        )
        add_notepad = QAction(icon(ICON_PATH_ADD), trans('action.tab.add.notepad'), menu)
        add_notepad.triggered.connect(
            lambda: self.add_tab(index, column_idx, Tab.TAB_NOTEPAD)
        )
        edit = QAction(icon(ICON_PATH_EDIT), trans('action.rename'), menu)
        edit.triggered.connect(
            lambda: self.rename_tab(index, column_idx)
        )
        move_right = QAction(icon(ICON_PATH_FORWARD), trans('action.tab.move.right'), menu)
        move_right.triggered.connect(
            lambda: self.window.controller.ui.tabs.move_tab(index, column_idx, 1)
        )
        move_left = QAction(icon(ICON_PATH_BACK), trans('action.tab.move.left'), menu)
        move_left.triggered.connect(
            lambda: self.window.controller.ui.tabs.move_tab(index, column_idx, 0)
        )

        menu.addAction(add_chat)
        menu.addAction(add_notepad)

        self.window.controller.tools.append_tab_menu(self, menu, index, column_idx, self)

        menu.addAction(edit)

        if column_idx != 0:
            menu.addAction(move_left)
        if column_idx != 1:
            menu.addAction(move_right)

        return menu

    def show_notepad_menu(self, index: int, column_idx: int, global_pos):
        """
        Show notepad menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        close_act = QAction(icon(ICON_PATH_CLOSE), trans('action.tab.close'), context_menu)
        close_act.triggered.connect(
            lambda: self.close_tab(index, column_idx)
        )
        close_all_act = QAction(icon(ICON_PATH_CLOSE), trans('action.tab.close_all.notepad'), context_menu)
        close_all_act.triggered.connect(
            lambda: self.close_all(Tab.TAB_NOTEPAD, column_idx)
        )
        context_menu.addAction(close_act)

        if self.window.core.tabs.count_by_type(Tab.TAB_NOTEPAD) > 1:
            context_menu.addAction(close_all_act)

        context_menu.exec(global_pos)

    def show_chat_menu(self, index: int, column_idx: int, global_pos):
        """
        Show chat menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        close_act = QAction(icon(ICON_PATH_CLOSE), trans('action.tab.close'), context_menu)
        close_act.triggered.connect(
            lambda: self.close_tab(index, column_idx)
        )
        close_all_act = QAction(icon(ICON_PATH_CLOSE), trans('action.tab.close_all.chat'), context_menu)
        close_all_act.triggered.connect(
            lambda: self.close_all(Tab.TAB_CHAT, column_idx)
        )

        # at least one chat tab must be open
        if self.window.core.tabs.count_by_type(Tab.TAB_CHAT) > 1:
            context_menu.addAction(close_act)
            context_menu.addAction(close_all_act)

        context_menu.exec(global_pos)

    def show_files_menu(self, index: int, column_idx: int, global_pos):
        """
        Show files menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        refresh = QAction(icon(ICON_PATH_RELOAD), trans('action.refresh'), context_menu)
        refresh.triggered.connect(
            lambda: self.window.controller.files.update_explorer()
        )
        context_menu.addAction(refresh)
        context_menu.exec(global_pos)

    def show_tool_menu(self, index: int, column_idx: int, global_pos):
        """
        Show tool menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        close_act = QAction(icon(ICON_PATH_CLOSE), trans('action.tab.close'), context_menu)
        close_act.triggered.connect(
            lambda: self.close_tab(index, column_idx)
        )
        context_menu.addAction(close_act)
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

    @Slot(int)
    def _on_current_changed(self, _idx: int):
        self.window.controller.ui.tabs.on_tab_changed(self.currentIndex(), self.column.get_idx())

    @Slot(int)
    def _on_tabbar_clicked(self, _idx: int):
        self.window.controller.ui.tabs.on_tab_clicked(self.currentIndex(), self.column.get_idx())

    @Slot(int)
    def _on_tabbar_dbl_clicked(self, _idx: int):
        self.window.controller.ui.tabs.on_tab_dbl_clicked(self.currentIndex(), self.column.get_idx())

    @Slot(int)
    def _on_tab_close_requested(self, _idx: int):
        self.window.controller.ui.tabs.on_tab_closed(self.currentIndex(), self.column.get_idx())

    @Slot(int, int)
    def _on_tab_moved(self, _from: int, _to: int):
        self.window.controller.ui.tabs.on_tab_moved(self.currentIndex(), self.column.get_idx())

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