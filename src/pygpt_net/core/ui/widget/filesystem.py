#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.08 22:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QCursor, QResizeEvent
from PySide6.QtWidgets import QTreeView, QMenu, QWidget, QVBoxLayout, QFileSystemModel, QHeaderView

from ...utils import trans


class FileExplorerWidget(QWidget):
    def __init__(self, window, directory):
        super().__init__()

        self.window = window
        self.model = QFileSystemModel()
        self.model.setRootPath(directory)

        self.treeView = QTreeView()
        self.treeView.setModel(self.model)
        self.treeView.setRootIndex(self.model.index(directory))

        layout = QVBoxLayout()
        layout.addWidget(self.treeView)
        self.setLayout(layout)

        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.openContextMenu)
        self.treeView.setColumnWidth(0, self.width() / 2)

        self.header = self.treeView.header()
        self.header.setStretchLastSection(True)

        self.column_proportion = 0.5
        self.adjustColumnWidths()

    def adjustColumnWidths(self):
        total_width = self.treeView.width()
        first_column_width = int(total_width * self.column_proportion)
        self.treeView.setColumnWidth(0, first_column_width)
        for column in range(1, self.model.columnCount()):
            self.treeView.setColumnWidth(column, (total_width - first_column_width) // (self.model.columnCount() - 1))

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.adjustColumnWidths()

    def openContextMenu(self, position):
        indexes = self.treeView.selectedIndexes()
        if indexes:
            index = indexes[0]
            path = self.model.filePath(index)

            actions = {}
            actions['open_dir'] = QAction(QIcon.fromTheme("system-file-manager"), trans('action.open_dir'), self)
            actions['open_dir'].triggered.connect(
                lambda: self.action_open_dir(path))

            actions['rename'] = QAction(QIcon.fromTheme("edit-edit"), trans('action.rename'), self)
            actions['rename'].triggered.connect(
                lambda: self.action_rename(path))

            actions['delete'] = QAction(QIcon.fromTheme("edit-delete"), trans('action.delete'), self)
            actions['delete'].triggered.connect(
                lambda: self.action_delete(path))

            menu = QMenu(self)
            menu.addAction(actions['rename'])
            menu.addAction(actions['open_dir'])
            menu.addAction(actions['delete'])

            menu.exec(QCursor.pos())

    def action_open_dir(self, path):
        """
        Open dir action handler

        :param event: mouse event
        """
        self.window.controller.files.open_dir(path)

    def action_rename(self, path):
        """
        Rename action handler

        :param event: mouse event
        """
        self.window.controller.files.rename(path)

    def action_delete(self, path):
        """
        Delete action handler

        :param event: mouse event
        """
        self.window.controller.files.delete(path)
