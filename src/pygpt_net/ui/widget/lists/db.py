#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.17 01:00:00                  #
# ================================================== #

import json
import ast
from datetime import datetime

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QAbstractItemView, QApplication, QMenu, \
    QSizePolicy, QTableView, QHeaderView

class DatabaseTableModel(QAbstractTableModel):
    def __init__(self, data, headers, timestamp_columns=None, convert_timestamps=True):
        super().__init__()
        self._data = data
        self._headers = headers
        self._timestamp_columns = timestamp_columns or []
        self._convert_timestamps = convert_timestamps

    def data(self, index, role):
        if role == Qt.DisplayRole:
            value = self._data[index.row()][index.column()]
            if self._headers[index.column()] in self._timestamp_columns and self._convert_timestamps:
                try:
                    if value != "None" and value != 0:
                        value = datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        value = ""
                except Exception as e:
                    pass
            return value
        return None

    def rowCount(self, index=QModelIndex()):
        return len(self._data)

    def columnCount(self, index=QModelIndex()):
        return len(self._headers)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

class DatabaseList(QTableView):
    NAME = range(2)  # list of columns

    def __init__(self, window=None):
        """
        Database table records list

        :param window: Window instance
        """
        super(DatabaseList, self).__init__(window)
        self.window = window
        self.browser = None
        self.viewer = None
        self.viewer_index = None
        self.viewer_current = None
        self.viewer_current_id = None
        self.viewer_current_field = None
        self.selection = None
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.clicked.connect(self.onItemClicked)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda: self.create_context_menu(self)
        )

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
        if self.viewer is None:
            return
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
        pass

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

        def delete_row():
            index = parent.currentIndex()
            if index.isValid():
                id = index.sibling(index.row(), 0).data(
                    Qt.DisplayRole)

                # delete row from database
                # self.window.get_viewer().delete_row(id)
                self.window.ui.dialogs.database.viewer.delete_row(int(id))

        menu = QMenu()
        copy_action = menu.addAction("Copy value to clipboard")
        delete_action = menu.addAction("Delete row")
        copy_action.triggered.connect(copy_to_clipboard)
        delete_action.triggered.connect(delete_row)
        menu.exec_(QCursor.pos())

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: Event
        """
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        super(DatabaseList, self).mousePressEvent(event)

    def onItemClicked(self, index):
        """
        On item clicked

        :param index: Index
        """
        # update data viewer
        if self.viewer is None:
            return
        data = self.model().data(index, Qt.DisplayRole)
        id = index.sibling(index.row(), 0).data(
            Qt.DisplayRole)
        self.viewer.setPlainText(str(self.parse_view(data)))
        self.viewer_index = index
        self.viewer_current = data
        self.viewer_current_id = id
        self.viewer_current_field = self.model().headerData(index.column(), Qt.Horizontal, Qt.DisplayRole)
