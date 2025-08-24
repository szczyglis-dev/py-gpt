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

from PySide6.QtCore import QItemSelectionModel, QPoint
from PySide6.QtGui import QAction, QIcon, Qt
from PySide6.QtWidgets import QMenu

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans


class AssistantList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Presets select menu

        :param window: main window
        :param id: input id
        """
        super(AssistantList, self).__init__(window)
        self.window = window
        self.id = id
        self.doubleClicked.connect(self.dblclick)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.restore_after_ctx_menu = True
        self._backup_selection = None

    def click(self, val):
        self.window.controller.assistant.select(val.row())

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.assistant.editor.edit(val.row())

    def show_context_menu(self, pos: QPoint):
        """
        Context menu event

        :param pos: QPoint
        """
        global_pos = self.viewport().mapToGlobal(pos)
        item = self.indexAt(pos)

        actions = {}
        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('assistant.action.edit'), self)
        actions['edit'].triggered.connect(
            lambda checked=False, item=item: self.action_edit(item))

        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('assistant.action.delete'), self)
        actions['delete'].triggered.connect(
            lambda checked=False, item=item: self.action_delete(item))

        menu = QMenu(self)
        menu.addAction(actions['edit'])
        menu.addAction(actions['delete'])

        idx = item.row()
        if idx >= 0:
            #self.window.controller.assistant.select(item.row())
            menu.exec_(global_pos)

        # store previous scroll position
        self.store_scroll_position()

        # restore selection if it was backed up
        if self.restore_after_ctx_menu:
            if self._backup_selection is not None:
                self.selectionModel().clearSelection()
                for idx in self._backup_selection:
                    self.selectionModel().select(
                        idx, QItemSelectionModel.Select | QItemSelectionModel.Rows
                    )
                self._backup_selection = None

        # restore scroll position
        self.restore_after_ctx_menu = True
        self.restore_scroll_position()

    def action_edit(self, item):
        """
        Edit action handler

        :param item: list item
        """
        idx = item.row()
        if idx >= 0:
            self.restore_after_ctx_menu = False  # do not restore selection after context menu
            self.window.controller.assistant.editor.edit(idx)

    def action_delete(self, item):
        """
        Delete action handler

        :param item: list item
        """
        idx = item.row()
        if idx >= 0:
            self.restore_after_ctx_menu = False  # do not restore selection after context menu
            self.window.controller.assistant.delete(idx)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            if not index.isValid():
                return
            super().mousePressEvent(event)
        elif event.button() == Qt.RightButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                self._backup_selection = list(self.selectionModel().selectedIndexes())
                self.selectionModel().clearSelection()
                self.selectionModel().select(
                    index, QItemSelectionModel.Select | QItemSelectionModel.Rows
                )
            event.accept()
        else:
            super().mousePressEvent(event)

    def selectionCommand(self, index, event=None):
        """
        Selection command
        :param index: Index
        :param event: Event
        """
        return super().selectionCommand(index, event)
