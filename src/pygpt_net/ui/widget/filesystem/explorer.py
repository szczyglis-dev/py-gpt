#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.16 06:00:00                  #
# ================================================== #

import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QAction, QIcon, QCursor, QResizeEvent
from PySide6.QtWidgets import QTreeView, QMenu, QWidget, QVBoxLayout, QFileSystemModel, QLabel, QHBoxLayout, \
    QPushButton, QSizePolicy

from pygpt_net.ui.widget.element.button import ContextMenuButton
from pygpt_net.ui.widget.element.help import HelpLabel
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

        self.btn_idx = ContextMenuButton(trans('idx.btn.index_all'), self)
        self.btn_idx.action = self.idx_context_menu
        self.btn_idx.setMaximumHeight(40)
        self.btn_idx.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.btn_clear = ContextMenuButton(trans('idx.btn.clear'), self)
        self.btn_clear.action = self.clear_context_menu
        self.btn_clear.setMaximumHeight(40)
        self.btn_clear.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

        self.path_label = QLabel(self.directory)
        self.path_label.setMaximumHeight(40)
        self.path_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.path_label.setStyleSheet(self.window.controller.theme.style('text_small'))

        header.addWidget(self.btn_upload)
        header.addWidget(self.btn_idx)
        header.addWidget(self.btn_clear)
        header.addStretch()
        header.addWidget(self.path_label)

        layout = QVBoxLayout()

        self.window.ui.nodes['tip.output.tab.files'] = HelpLabel(trans('tip.output.tab.files'), self.window)

        layout.addWidget(self.treeView)
        layout.addWidget(self.window.ui.nodes['tip.output.tab.files'])
        layout.addLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.openContextMenu)
        self.treeView.setColumnWidth(0, self.width() / 2)

        self.header = self.treeView.header()
        self.header.setStretchLastSection(True)
        self.header.setContentsMargins(0, 0, 0, 0)

        self.column_proportion = 0.3
        self.adjustColumnWidths()

        self.header.setStyleSheet("""
           QHeaderView::section {
               text-align: center;
               vertical-align: middle;
           }
       """)

    def idx_context_menu(self, parent, pos):
        """
        Index all btn context menu
        :param pos: mouse  position
        """
        menu = QMenu(self)
        idxs = self.window.core.config.get('llama.idx.list')
        if len(idxs) > 0:
            for idx in idxs:
                id = idx['id']
                name = idx['name'] + " (" + idx['id'] + ")"
                action = menu.addAction("IDX: " + name)
                action.triggered.connect(lambda checked=False, id=id:
                                         self.window.controller.idx.indexer.index_all_files(id))
        menu.exec_(parent.mapToGlobal(pos))

    def clear_context_menu(self, parent, pos):
        """
        Clear btn context menu

        :param pos: mouse position
        """
        menu = QMenu(self)
        idxs = self.window.core.config.get('llama.idx.list')
        if len(idxs) > 0:
            for idx in idxs:
                id = idx['id']
                name = idx['name'] + " (" + idx['id'] + ")"
                action = menu.addAction("IDX: " + name)
                action.triggered.connect(lambda checked=False, id=id:
                                         self.window.controller.idx.indexer.clear(id))
        menu.exec_(parent.mapToGlobal(pos))

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

        :param position: mouse position
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

            menu = QMenu(self)
            idx_menu = QMenu(trans('action.idx'), self)

            actions['rename'] = QAction(QIcon.fromTheme("edit-edit"), trans('action.rename'), self)
            actions['rename'].triggered.connect(
                lambda: self.action_rename(path))

            actions['delete'] = QAction(QIcon.fromTheme("edit-delete"), trans('action.delete'), self)
            actions['delete'].triggered.connect(
                lambda: self.action_delete(path))

            menu.addAction(actions['open'])
            menu.addAction(actions['open_dir'])
            menu.addAction(actions['rename'])
            menu.addAction(actions['delete'])

            # indexes list
            idxs = self.window.core.config.get('llama.idx.list')
            if len(idxs) > 0:
                for idx in idxs:
                    id = idx['id']
                    name = idx['name'] + " (" + idx['id'] + ")"
                    action = idx_menu.addAction("IDX: " + name)
                    action.triggered.connect(lambda checked=False, id=id, path=path:
                                             self.action_idx(path, id))

                menu.addMenu(idx_menu)

            menu.exec(QCursor.pos())

    def action_open(self, path):
        """
        Open action handler

        :param path: path to open
        """
        self.window.controller.files.open(path)

    def action_idx(self, path, id):
        """
        Index file or dir handler

        :param path: path to open
        :param id: index id
        """
        self.window.controller.idx.indexer.index_file(path, id)

    def action_open_dir(self, path):
        """
        Open in directory action handler

        :param path: path to open
        """
        self.window.controller.files.open_dir(path, True)

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
                status = self.get_index_status(file_path)   # get index status
                if status['indexed']:
                    content = ''
                    content += datetime.datetime.fromtimestamp(status['last_index_at']).strftime("%Y-%m-%d %H:%M")
                    content += ' (' + ",".join(status['indexed_in']) + ')'
                else:
                    content = '-'  # if file not indexed
                return content
        return super().data(index, role)

    def get_index_status(self, file_path) -> dict:
        """
        Get index status

        :param file_path: file path
        :return: file index status
        """
        file_id = self.window.core.idx.to_file_id(file_path)
        indexed_in = []
        indexed_timestamps = {}
        last_index_at = 0
        for idx in self.index_dict:
            items = self.index_dict[idx]
            if file_id in items:
                indexed_in.append(idx)  # append idx where file is indexed
                indexed_timestamps[idx] = items[file_id]['indexed_ts']
                if items[file_id]['indexed_ts'] > last_index_at:
                    last_index_at = items[file_id]['indexed_ts']

        # sort indexed_in by timestamp DESC
        indexed_in = sorted(indexed_in, key=lambda x: indexed_timestamps[x], reverse=True)
        if len(indexed_in) > 0:
            return {'indexed': True, 'indexed_in': indexed_in, 'last_index_at': last_index_at}
        else:
            return {'indexed': False}

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        Prepare Header data (append Indexed column)

        :param section: Section
        :param orientation: Orientation
        :param role: Role
        :return: Header data
        """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:
                return trans('files.explorer.header.name')
            elif section == 1:
                return trans('files.explorer.header.size')
            elif section == 2:
                return trans('files.explorer.header.type')
            elif section == 3:
                return trans('files.explorer.header.modified')
            elif section == 4:
                return trans('files.explorer.header.indexed')
        return super().headerData(section, orientation, role)

    def update_idx_status(self, idx_data):
        """
        Update index data status

        :param idx_data: new index data dict
        """
        self.index_dict = idx_data
        top_left_index = self.index(0, 0)
        bottom_right_index = self.index(self.rowCount() - 1, self.columnCount() - 1)
        self.dataChanged.emit(top_left_index, bottom_right_index, [Qt.DisplayRole])
        self.layoutChanged.emit()
