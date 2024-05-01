#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.01 17:00:00                  #
# ================================================== #

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QTreeView, QAbstractItemView


class BaseList(QTreeView):
    NAME = range(1)  # list of columns

    def __init__(self, window=None, id=None):
        """
        Select menu

        :param window: Window instance
        :param id: input id
        """
        super(BaseList, self).__init__(window)
        self.window = window
        self.id = id
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setIndentation(0)
        self.selection_locked = None
        self.selection = None
        self.unlocked = False
        self.clicked.connect(self.click)
        self.header().hide()

    def click(self, val):
        self.window.controller.mode.select(self.id)
        self.selection = self.selectionModel().selection()

    def lockSelection(self, selected=None, deselected=None):
        if self.selection is not None:
            self.selectionModel().select(self.selection, QItemSelectionModel.Select)

    def backup_selection(self):
        self.selection = self.selectionModel().selection()

    def restore_selection(self):
        if self.selection is not None:
            self.selectionModel().select(self.selection, QItemSelectionModel.Select)

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        super(BaseList, self).mousePressEvent(event)

    def focusOutEvent(self, event):
        pass

    def selectionCommand(self, index, event=None):
        """
        Selection command
        :param index: Index
        :param event: Event
        """
        # check tmp unlock
        if self.unlocked:
            return super().selectionCommand(index, event)

        if self.selection_locked is not None and self.selection_locked():
            return QItemSelectionModel.NoUpdate
        return super().selectionCommand(index, event)
