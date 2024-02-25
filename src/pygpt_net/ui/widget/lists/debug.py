#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.25 17:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QCursor, QTextDocument
from PySide6.QtWidgets import QTreeView, QAbstractItemView, QApplication, QMenu, QStyledItemDelegate, \
    QSizePolicy


class DebugList(QTreeView):
    NAME = range(2)  # list of columns

    def __init__(self, window=None):
        """
        Debug list

        :param window: Window instance
        """
        super(DebugList, self).__init__(window)
        self.window = window
        self.selection = None
        self.setRootIsDecorated(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setItemDelegate(ExpandingDelegate(self))
        self.clicked.connect(self.onItemClicked)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.header().setStretchLastSection(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda: self.create_context_menu(self))
        self.setStyleSheet("""
        QTreeView::item {
            border-bottom: 1px solid #5d5d5d;
            height: auto;
        }
        """)

    def create_context_menu(self, parent):
        """
        Create context menu

        :param parent: Parent
        """
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
        """
        Mouse press event

        :param event: Event
        """
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        super(DebugList, self).mousePressEvent(event)

    def onItemClicked(self, index):
        """
        On item clicked

        :param index: Index
        """
        row = index.row()
        if row in self.itemDelegate().expandedRows:
            del self.itemDelegate().expandedRows[row]
        else:
            self.itemDelegate().expandedRows[row] = True
        self.update(index)
        self.model().dataChanged.emit(index, index)


class ExpandingDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        """
        Expanding delegate

        :param parent: Parent
        """
        super().__init__(parent)
        self.expandedRows = {}

    def paint(self, painter, option, index):
        """
        Paint

        :param painter: Painter
        :param option: Option
        :return:
        """
        super().paint(painter, option, index)

    def sizeHint(self, option, index):
        """
        Size hint

        :param option: Option
        :param index: Index
        """
        if index.row() in self.expandedRows:
            textDocument = QTextDocument()
            textDocument.setPlainText(str(index.data()))
            textDocument.setTextWidth(option.rect.width())
            return QSize(option.rect.width(), textDocument.size().height())
        else:
            return super().sizeHint(option, index)
