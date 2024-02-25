#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.25 22:00:00                  #
# ================================================== #

import json
import ast
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QAbstractItemView, QApplication, QMenu, \
    QSizePolicy, QTableView, QHeaderView


class DebugList(QTableView):
    NAME = range(2)  # list of columns

    def __init__(self, window=None):
        """
        Debug list

        :param window: Window instance
        """
        super(DebugList, self).__init__(window)
        self.window = window
        self.viewer = None
        self.viewer_index = None
        self.viewer_current = None
        self.selection = None
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.clicked.connect(self.onItemClicked)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda: self.create_context_menu(self))

    def on_data_begin(self):
        """
        On data update begin
        """
        self.adjustColumns()

    def on_data_end(self):
        """
        On data update end
        """
        # update data viewer
        if self.viewer_index:
            new = self.model().data(self.viewer_index)
            if self.viewer_current != new:
                self.viewer.setPlainText(self.parse_view(new))
                self.viewer_current = new

    def parse_view(self, data):
        """
        Parse view, convert data to formatted JSON if needed

        :param data: Data
        """
        try:
            if data.startswith("{") or data.startswith("["):
                data = json.dumps(ast.literal_eval(data), indent=4)
        except Exception as e:
            pass
        return data

    def adjustColumns(self):
        """Adjust columns width"""
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

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
        # update data viewer
        data = self.model().data(index)
        self.viewer.setPlainText(self.parse_view(data))
        self.viewer_index = index
        self.viewer_current = data
