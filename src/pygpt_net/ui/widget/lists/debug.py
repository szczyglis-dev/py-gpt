#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
# ================================================== #
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QTreeView, QAbstractItemView, QApplication, QMenu


class DebugList(QTreeView):
    NAME = range(2)  # list of columns

    def __init__(self, window=None):
        """
        Select menu

        :param window: Window instance
        """
        super(DebugList, self).__init__(window)
        self.window = window
        self.selection = None
        self.setRootIsDecorated(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setWordWrap(True)

        self.setStyleSheet("""
        QTreeView::item {
            border-bottom: 1px solid #5d5d5d;
        }
        QTreeView::item:!selected:hover {
            /* color: red; */
            background-color: #000;
        }
        """)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda: self.create_context_menu(self))

    def create_context_menu(self, parent):
        def copy_to_clipboard():
            index = parent.currentIndex()
            if index.isValid():
                value = index.sibling(index.row(), 1).data(
                    Qt.DisplayRole)
                QApplication.clipboard().setText(value)

        menu = QMenu()
        copy_action = menu.addAction("Copy value to clipboard")
        copy_action.triggered.connect(copy_to_clipboard)

        menu.exec_(QCursor.pos())

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        super(DebugList, self).mousePressEvent(event)
