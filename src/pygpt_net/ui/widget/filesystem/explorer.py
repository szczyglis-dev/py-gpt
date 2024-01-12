#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.11 09:00:00                  #
# ================================================== #

import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QAction, QIcon, QCursor, QResizeEvent
from PySide6.QtWidgets import QTreeView, QMenu, QWidget, QVBoxLayout, QFileSystemModel, QLabel, QHBoxLayout, \
    QPushButton, QSizePolicy

from pygpt_net.utils import trans


class FileExplorer(QWidget):
    def __init__(self, window, directory, index_data):
        """
        File explorer widget

        :param window: Window instance
        :param directory: directory to explore
        :param index_data: index data
        """
        super().__init__()

        self.window = window
        self.index_data = index_data
        self.directory = directory
        self.model = IndexedFileSystemModel(self.window, self.index_data)
        self.model.setRootPath(directory)

        self.treeView = QTreeView()
        self.treeView.setModel(self.model)
        self.treeView.setRootIndex(self.model.index(directory))

        header = QHBoxLayout()

        self.btn_upload = QPushButton(trans('files.local.upload'))
        self.btn_upload.setMaximumHeight(40)
        self.btn_upload.clicked.connect(self.window.controller.files.upload_local)
        self.btn_upload.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.btn_idx = QPushButton(trans('idx.btn.index_all'))
        self.btn_idx.setMaximumHeight(40)
        self.btn_idx.clicked.connect(self.window.controller.idx.index_all)
        self.btn_idx.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.btn_clear = QPushButton(trans('idx.btn.clear'))
        self.btn_clear.setMaximumHeight(40)
        self.btn_clear.clicked.connect(self.window.controller.idx.clear)
        self.btn_clear.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.path_label = QLabel(self.directory)
        self.path_label.setMaximumHeight(40)
        self.path_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.path_label.setStyleSheet(self.window.controller.theme.get_style('text_small'))

        header.addWidget(self.btn_upload)
        header.addWidget(self.btn_idx)
        header.addWidget(self.btn_clear)
        header.addStretch()
        header.addWidget(self.path_label)

        layout = QVBoxLayout()

        layout.addWidget(self.treeView)
        layout.addLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.openContextMenu)
        self.treeView.setColumnWidth(0, self.width() / 2)

        self.header = self.treeView.header()
        self.header.setStretchLastSection(True)
        self.header.setContentsMargins(0, 0, 0, 0)
        #self.header.setMaximumHeight(40)

        self.column_proportion = 0.5
        self.adjustColumnWidths()

        self.header.setStyleSheet("""
           QHeaderView::section {
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

            actions['index_path'] = QAction(QIcon.fromTheme("search"), trans('action.idx'), self)
            actions['index_path'].triggered.connect(
                lambda: self.action_idx(path))

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
            menu.addAction(actions['index_path'])
            menu.addAction(actions['delete'])

            menu.exec(QCursor.pos())

    def action_open(self, path):
        """
        Open action handler

        :param path: path to open
        """
        self.window.controller.files.open(path)

    def action_idx(self, path):
        """
        Index file or dir handler

        :param path: path to open
        """
        self.window.controller.idx.index_path(path)

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


class IndexedFileSystemModel(QFileSystemModel):
    def __init__(self, window, index_dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window = window
        self.index_dict = index_dict

    def columnCount(self, parent=QModelIndex()):
        """
        Return column count

        :param parent: parent
        :return: column count
        """
        return super().columnCount(parent) + 1

    def data(self, index, role=Qt.DisplayRole):
        """
        Data handler

        :param index: row index
        :param role: role
        :return: data
        """
        if index.column() == self.columnCount() - 1:
            if role == Qt.DisplayRole:
                file_path = self.filePath(index.siblingAtColumn(0))
                file_id = self.window.core.idx.to_file_id(file_path)
                if self.index_dict.get(file_id):
                    # show status and date from timestamp:
                    return datetime.datetime.fromtimestamp(self.index_dict[file_id]['indexed_ts']).strftime(
                        "%Y-%m-%d %H:%M")
                else:
                    return "-"
        return super().data(index, role)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        Prepare Header data (append Indexed column)

        :param section: Section
        :param orientation: Orientation
        :param role: Role
        :return: Header data
        """
        if section == self.columnCount() - 1 and orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return "Indexed"
        return super().headerData(section, orientation, role)

    def update_idx_status(self, new_index_dict):
        """
        Update index status

        :param new_index_dict: new index dict
        """
        self.index_dict = new_index_dict
        top_left_index = self.index(0, 0)
        bottom_right_index = self.index(self.rowCount() - 1, self.columnCount() - 1)
        self.dataChanged.emit(top_left_index, bottom_right_index, [Qt.DisplayRole])
        self.layoutChanged.emit()
