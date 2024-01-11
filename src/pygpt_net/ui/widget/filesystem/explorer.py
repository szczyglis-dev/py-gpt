#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QCursor, QResizeEvent
from PySide6.QtWidgets import QTreeView, QMenu, QWidget, QVBoxLayout, QFileSystemModel, QLabel

from pygpt_net.utils import trans


class FileExplorer(QWidget):
    def __init__(self, window, directory):
        """
        File explorer widget

        :param window: Window instance
        :param directory: directory to explore
        """
        super().__init__()

        self.window = window
        self.model = QFileSystemModel()
        self.model.setRootPath(directory)

        self.treeView = QTreeView()
        self.treeView.setModel(self.model)
        self.treeView.setRootIndex(self.model.index(directory))

        self.path_label = QLabel(directory)
        self.path_label.setMaximumHeight(40)
        self.path_label.setAlignment(Qt.AlignRight)
        self.path_label.setStyleSheet(self.window.controller.theme.get_style('text_small'))

        layout = QVBoxLayout()

        layout.addWidget(self.path_label)
        layout.addWidget(self.treeView)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.openContextMenu)
        self.treeView.setColumnWidth(0, self.width() / 2)

        self.header = self.treeView.header()
        self.header.setStretchLastSection(True)
        self.header.setContentsMargins(0, 0, 0, 0)
        self.header.setMaximumHeight(40)

        self.column_proportion = 0.5
        self.adjustColumnWidths()

        self.header.setStyleSheet("""
           QHeaderView::section {
               padding-top: 0.8em;
               text-align: center;
               vertical-align: middle;
           }
       """)

    def adjustColumnWidths(self):
        """
        Adjust column widths
        """
        total_width = self.treeView.width()
        first_column_width = int(total_width * self.column_proportion)
        self.treeView.setColumnWidth(0, first_column_width)
        for column in range(1, self.model.columnCount()):
            self.treeView.setColumnWidth(column, (total_width - first_column_width) // (self.model.columnCount() - 1))

    def resizeEvent(self, event: QResizeEvent):
        """
        Resize event
        :param event: Event object
        """
        super().resizeEvent(event)
        self.adjustColumnWidths()

    def openContextMenu(self, position):
        """
        Open context menu
        :param position: position
        """
        indexes = self.treeView.selectedIndexes()
        if indexes:
            index = indexes[0]
            path = self.model.filePath(index)

            actions = {}
            actions['open'] = QAction(QIcon.fromTheme("document-open"), trans('action.open'), self)
            actions['open'].triggered.connect(
                lambda: self.action_open(path))

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
            menu.addAction(actions['open'])
            menu.addAction(actions['open_dir'])
            menu.addAction(actions['rename'])
            menu.addAction(actions['delete'])

            menu.exec(QCursor.pos())

    def action_open(self, path):
        """
        Open action handler

        :param path: path to open
        """
        self.window.controller.files.open(path)

    def action_open_dir(self, path):
        """
        Open dir action handler

        :param path: path to open
        """
        self.window.controller.files.open_dir(path)

    def action_rename(self, path):
        """
        Rename action handler

        :param path: path to open
        """
        self.window.controller.files.rename(path)

    def action_delete(self, path):
        """
        Delete action handler

        :param path: path to open
        """
        self.window.controller.files.delete(path)
