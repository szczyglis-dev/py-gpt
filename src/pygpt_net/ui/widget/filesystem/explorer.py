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

import datetime
import os

from PySide6.QtCore import Qt, QModelIndex, QDir
from PySide6.QtGui import QAction, QIcon, QCursor, QResizeEvent
from PySide6.QtWidgets import QTreeView, QMenu, QWidget, QVBoxLayout, QFileSystemModel, QLabel, QHBoxLayout, \
    QPushButton, QSizePolicy

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.ui.widget.element.button import ContextMenuButton
from pygpt_net.ui.widget.element.labels import HelpLabel
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
        self.owner = None
        self.index_data = index_data
        self.directory = directory
        self.model = IndexedFileSystemModel(self.window, self.index_data)
        self.model.setRootPath(self.directory)
        self.model.setFilter(self.model.filter() | QDir.Hidden)
        self.treeView = QTreeView()
        self.treeView.setModel(self.model)
        self.treeView.setRootIndex(self.model.index(self.directory))
        self.treeView.setUniformRowHeights(True)
        self.setProperty('class', 'file-explorer')

        header = QHBoxLayout()

        self.btn_open = QPushButton(trans('action.open'))
        self.btn_open.setMaximumHeight(40)
        self.btn_open.clicked.connect(
                lambda: self.action_open(self.directory)
        )
        self.btn_open.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

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

        self.btn_tool = QPushButton(QIcon(":/icons/db.svg"), "")
        self.btn_tool.setMaximumHeight(40)
        self.btn_tool.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.btn_tool.clicked.connect(
            lambda: self.window.tools.get("indexer").toggle()
        )

        self.path_label = QLabel(self.directory)
        self.path_label.setMaximumHeight(40)
        self.path_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

        header.addWidget(self.btn_open)
        header.addWidget(self.btn_upload)
        header.addStretch()
        header.addWidget(self.path_label)
        header.addStretch()

        header.addWidget(self.btn_tool)
        header.addWidget(self.btn_idx)
        header.addWidget(self.btn_clear)
        self.layout = QVBoxLayout()

        self.window.ui.nodes['tip.output.tab.files'] = HelpLabel(trans('tip.output.tab.files'), self.window)

        self.layout.addWidget(self.treeView)
        self.layout.addWidget(self.window.ui.nodes['tip.output.tab.files'])
        self.layout.addLayout(header)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.openContextMenu)
        self.treeView.setColumnWidth(0, int(self.width() / 2))

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
        self.tab = None
        self.installEventFilter(self)

        self._icons = {
            'open': QIcon(":/icons/view.svg"),
            'open_dir': QIcon(":/icons/folder_filled.svg"),
            'download': QIcon(":/icons/download.svg"),
            'rename': QIcon(":/icons/edit.svg"),
            'duplicate': QIcon(":/icons/stack.svg"),
            'touch': QIcon(":/icons/add.svg"),
            'mkdir': QIcon(":/icons/add_folder.svg"),
            'refresh': QIcon(":/icons/reload.svg"),
            'upload': QIcon(":/icons/upload.svg"),
            'delete': QIcon(":/icons/delete.svg"),
            'attachment': QIcon(":/icons/attachment.svg"),
            'copy': QIcon(":/icons/copy.svg"),
            'read': QIcon(":/icons/view.svg"),
            'db': QIcon(":/icons/db.svg"),
        }

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if event.type() == event.Type.FocusIn:
            if self.tab is not None:
                col_idx = self.tab.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
        return super().eventFilter(source, event)

    def set_tab(self, tab: Tab):
        """
        Set tab

        :param tab: Tab
        """
        self.tab = tab

    def setOwner(self, owner: Tab):
        """
        Set tab parent (owner)

        :param owner: parent tab instance
        """
        self.owner = owner

    def getOwner(self) -> Tab:
        """
        Get tab parent (owner)

        :return: parent tab instance
        """
        return self.owner

    def update_view(self):
        """Update explorer view"""
        self.model.beginResetModel()
        self.model.setRootPath(self.directory)
        self.model.endResetModel()
        self.treeView.setRootIndex(self.model.index(self.directory))

    def idx_context_menu(self, parent, pos):
        """
        Index all btn context menu

        :param parent: parent widget
        :param pos: mouse  position
        """
        menu = QMenu(self)
        idx_list = self.window.core.config.get('llama.idx.list')
        if len(idx_list) > 0:
            for idx in idx_list:
                id = idx['id']
                name = f"{idx['name']} ({idx['id']})"
                action = menu.addAction(f"IDX: {name}")
                action.triggered.connect(
                    lambda checked=False,
                           id=id: self.window.controller.idx.indexer.index_all_files(id)
                )
        menu.exec(parent.mapToGlobal(pos))

    def clear_context_menu(self, parent, pos):
        """
        Clear btn context menu

        :param parent: parent widget
        :param pos: mouse position
        """
        menu = QMenu(self)
        idx_list = self.window.core.config.get('llama.idx.list')
        if len(idx_list) > 0:
            for idx in idx_list:
                id = idx['id']
                name = f"{idx['name']} ({idx['id']})"
                action = menu.addAction(f"IDX: {name}")
                action.triggered.connect(
                    lambda checked=False,
                           id=id: self.window.controller.idx.indexer.clear(id)
                )
        menu.exec(parent.mapToGlobal(pos))

    def adjustColumnWidths(self):
        """Adjust column widths"""
        total_width = self.treeView.width()
        col_count = self.model.columnCount()
        first_column_width = int(total_width * self.column_proportion)
        self.treeView.setColumnWidth(0, first_column_width)
        if col_count > 1:
            remaining = max(total_width - first_column_width, 0)
            per_col = remaining // (col_count - 1) if col_count > 1 else 0
            for column in range(1, col_count):
                self.treeView.setColumnWidth(column, per_col)

    def resizeEvent(self, event: QResizeEvent):
        """
        Resize event

        :param event: Event object
        """
        super().resizeEvent(event)
        if event.oldSize().width() != event.size().width():
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
            preview_actions = []
            use_actions = []

            if self.window.core.filesystem.actions.has_preview(path):
                preview_actions = self.window.core.filesystem.actions.get_preview(self, path)

            actions['open'] = QAction(self._icons['open'], trans('action.open'), self)
            actions['open'].triggered.connect(
                lambda: self.action_open(path),
            )

            actions['open_dir'] = QAction(self._icons['open_dir'], trans('action.open_dir'), self)
            actions['open_dir'].triggered.connect(
                lambda: self.action_open_dir(path),
            )

            actions['download'] = QAction(self._icons['download'], trans('action.download'), self)
            actions['download'].triggered.connect(
                lambda: self.window.controller.files.download_local(path),
            )

            actions['rename'] = QAction(self._icons['rename'], trans('action.rename'), self)
            actions['rename'].triggered.connect(
                lambda: self.action_rename(path),
            )

            actions['duplicate'] = QAction(self._icons['duplicate'], trans('action.duplicate'), self)
            actions['duplicate'].triggered.connect(
                lambda: self.window.controller.files.duplicate_local(path, ""),
            )

            if os.path.isdir(path):
                parent = path
            else:
                parent = os.path.dirname(path)

            actions['touch'] = QAction(self._icons['touch'], trans('action.touch'), self)
            actions['touch'].triggered.connect(
                lambda: self.window.controller.files.touch_file(parent),
            )

            actions['mkdir'] = QAction(self._icons['mkdir'], trans('action.mkdir'), self)
            actions['mkdir'].triggered.connect(
                lambda: self.action_make_dir(parent),
            )

            actions['refresh'] = QAction(self._icons['refresh'], trans('action.refresh'), self)
            actions['refresh'].triggered.connect(
                lambda: self.window.controller.files.update_explorer(),
            )

            actions['upload'] = QAction(self._icons['upload'], trans('action.upload'), self)
            actions['upload'].triggered.connect(
                lambda: self.window.controller.files.upload_local(parent),
            )

            actions['delete'] = QAction(self._icons['delete'], trans('action.delete'), self)
            actions['delete'].triggered.connect(
                lambda: self.action_delete(path),
            )

            menu = QMenu(self)
            if preview_actions:
                for action in preview_actions:
                    menu.addAction(action)
            menu.addAction(actions['open'])
            menu.addAction(actions['open_dir'])

            use_menu = QMenu(trans('action.use'), self)

            if not os.path.isdir(path):
                actions['use_attachment'] = QAction(
                    self._icons['attachment'],
                    trans('action.use.attachment'),
                    self,
                )
                actions['use_attachment'].triggered.connect(
                    lambda: self.window.controller.files.use_attachment(path),
                )
                if self.window.core.filesystem.actions.has_use(path):
                    use_actions = self.window.core.filesystem.actions.get_use(self, path)

            actions['use_copy_work_path'] = QAction(
                self._icons['copy'],
                trans('action.use.copy_work_path'),
                self,
            )
            actions['use_copy_work_path'].triggered.connect(
                lambda: self.window.controller.files.copy_work_path(path),
            )

            actions['use_copy_sys_path'] = QAction(
                self._icons['copy'],
                trans('action.use.copy_sys_path'),
                self,
            )
            actions['use_copy_sys_path'].triggered.connect(
                lambda: self.window.controller.files.copy_sys_path(path),
            )

            actions['use_read_cmd'] = QAction(self._icons['read'], trans('action.use.read_cmd'), self)
            actions['use_read_cmd'].triggered.connect(
                lambda: self.window.controller.files.make_read_cmd(path),
            )

            if not os.path.isdir(path):
                use_menu.addAction(actions['use_attachment'])

            if use_actions:
                for action in use_actions:
                    use_menu.addAction(action)

            use_menu.addAction(actions['use_copy_work_path'])
            use_menu.addAction(actions['use_copy_sys_path'])
            use_menu.addAction(actions['use_read_cmd'])
            menu.addMenu(use_menu)

            file_id = self.window.core.idx.files.get_id(path)
            remove_actions = []
            for idx in self.index_data:
                items = self.index_data[idx]
                if file_id in items:
                    action = QAction(self._icons['delete'], trans("action.idx.remove") + ": " + idx, self)
                    action.triggered.connect(
                        lambda checked=False,
                               idx=idx,
                               file_id=file_id: self.action_idx_remove(file_id, idx)
                    )
                    remove_actions.append(action)

            if self.window.core.idx.indexing.is_allowed(path):
                idx_menu = QMenu(trans('action.idx'), self)
                idx_list = self.window.core.config.get('llama.idx.list')
                if len(idx_list) > 0 or len(remove_actions) > 0:
                    if len(idx_list) > 0:
                        for idx in idx_list:
                            id = idx['id']
                            name = f"{idx['name']} ({idx['id']})"
                            action = QAction(self._icons['db'], f"IDX: {name}", self)
                            action.triggered.connect(
                                lambda checked=False,
                                       id=id,
                                       path=path: self.action_idx(path, id)
                            )
                            idx_menu.addAction(action)

                if len(remove_actions) > 0:
                    idx_menu.addSeparator()
                    for action in remove_actions:
                        idx_menu.addAction(action)

                menu.addMenu(idx_menu)

            menu.addAction(actions['download'])
            menu.addAction(actions['touch'])
            menu.addAction(actions['mkdir'])
            menu.addAction(actions['upload'])
            menu.addAction(actions['refresh'])

            menu.addAction(actions['rename'])
            menu.addAction(actions['duplicate'])
            menu.addAction(actions['delete'])

            menu.exec(QCursor.pos())
        else:
            actions = {}

            actions['touch'] = QAction(self._icons['touch'], trans('action.touch'), self)
            actions['touch'].triggered.connect(
                lambda: self.window.controller.files.touch_file(self.directory),
            )

            actions['open_dir'] = QAction(self._icons['open_dir'], trans('action.open_dir'), self)
            actions['open_dir'].triggered.connect(
                lambda: self.action_open_dir(self.directory),
            )

            actions['mkdir'] = QAction(self._icons['mkdir'], trans('action.mkdir'), self)
            actions['mkdir'].triggered.connect(
                lambda: self.action_make_dir(self.directory),
            )

            actions['upload'] = QAction(self._icons['upload'], trans('action.upload'), self)
            actions['upload'].triggered.connect(
                lambda: self.window.controller.files.upload_local(),
            )

            menu = QMenu(self)
            menu.addAction(actions['touch'])
            menu.addAction(actions['open_dir'])
            menu.addAction(actions['mkdir'])
            menu.addAction(actions['upload'])
            menu.exec(QCursor.pos())

    def action_open(self, path):
        """
        Open action handler

        :param path: path to open
        """
        self.window.controller.files.open(path)

    def action_idx(self, path: str, idx: str):
        """
        Index file or dir handler

        :param path: path to open
        :param idx: index ID to use (name)
        """
        self.window.controller.idx.indexer.index_file(path, idx)

    def action_idx_remove(self, path: str, idx: str):
        """
        Remove file or dir from index handler

        :param path: path to open
        :param idx: index ID to use (name)
        """
        self.window.controller.idx.indexer.index_file_remove(path, idx)

    def action_open_dir(self, path: str):
        """
        Open in directory action handler

        :param path: path to open
        """
        self.window.controller.files.open_dir(path, True)

    def action_make_dir(self, path: str = None):
        """
        Make directory action handler

        :param path: parent path
        """
        self.window.controller.files.make_dir_dialog(path)

    def action_rename(self, path: str):
        """
        Rename action handler

        :param path: path to rename
        """
        self.window.controller.files.rename(path)

    def action_delete(self, path: str):
        """
        Delete action handler

        :param path: path to delete
        """
        self.window.controller.files.delete(path)


class IndexedFileSystemModel(QFileSystemModel):
    def __init__(self, window, index_dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window = window
        self.index_dict = index_dict
        self._status_cache = {}
        self.directoryLoaded.connect(self.refresh_path)

    def refresh_path(self, path):
        index = self.index(path)
        if index.isValid():
            self._status_cache.clear()
            self.dataChanged.emit(index, index)

    def columnCount(self, parent=QModelIndex()) -> int:
        """
        Return column count

        :param parent: parent
        :return: column count
        """
        return super().columnCount(parent) + 1

    def data(self, index, role=Qt.DisplayRole) -> any:
        """
        Data handler

        :param index: row index
        :param role: role
        :return: data
        """
        last_col = self.columnCount() - 1
        if index.column() == last_col:
            if role == Qt.DisplayRole:
                file_path = self.filePath(index.siblingAtColumn(0))
                status = self.get_index_status(file_path)
                if status['indexed']:
                    ts = status['last_index_at']
                    dt = datetime.datetime.fromtimestamp(ts)
                    if dt.date() == datetime.date.today():
                        ds = dt.strftime("%H:%M")
                    else:
                        ds = dt.strftime("%Y-%m-%d %H:%M")
                    content = f"{ds} ({','.join(status['indexed_in'])})"
                else:
                    content = '-'
                return content
        elif index.column() == last_col - 1:
            if role == Qt.DisplayRole:
                dt_qt = self.lastModified(index)
                ts = dt_qt.toSecsSinceEpoch()
                dt_py = datetime.datetime.fromtimestamp(ts)
                if dt_py.date() == datetime.date.today():
                    data = dt_py.strftime("%H:%M")
                else:
                    data = dt_py.strftime("%Y-%m-%d %H:%M")
                file_path = self.filePath(index.siblingAtColumn(0))
                status = self.get_index_status(file_path)
                if status['indexed']:
                    if 'last_index_at' in status and status['last_index_at'] < ts:
                        data += '*'
                return data

        return super().data(index, role)

    def get_index_status(self, file_path) -> dict:
        """
        Get index status

        :param file_path: file path
        :return: file index status
        """
        file_id = self.window.core.idx.files.get_id(file_path)
        cached = self._status_cache.get(file_id)
        if cached is not None:
            return cached
        indexed_in = []
        indexed_timestamps = {}
        last_index_at = 0
        for idx in self.index_dict:
            items = self.index_dict[idx]
            if file_id in items:
                indexed_in.append(idx)
                ts = items[file_id]['indexed_ts']
                indexed_timestamps[idx] = ts
                if ts > last_index_at:
                    last_index_at = ts
        if indexed_in:
            indexed_in.sort(key=lambda x: indexed_timestamps[x], reverse=True)
            result = {
                'indexed': True,
                'indexed_in': indexed_in,
                'last_index_at': last_index_at,
            }
        else:
            result = {'indexed': False}
        self._status_cache[file_id] = result
        return result

    def headerData(self, section, orientation, role=Qt.DisplayRole) -> str:
        """
        Prepare Header data (append Indexed column)

        :param section: Section
        :param orientation: Orientation
        :param role: Role
        :return: Header data
        """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:  # name
                return trans('files.explorer.header.name')
            elif section == 1:  # size
                return trans('files.explorer.header.size')
            elif section == 2:  # type
                return trans('files.explorer.header.type')
            elif section == 3:  # modified
                return trans('files.explorer.header.modified')
            elif section == 4:  # indexed
                return trans('files.explorer.header.indexed')
        return super().headerData(section, orientation, role)

    def update_idx_status(self, idx_data):
        """
        Update index data status

        :param idx_data: new index data dict
        """
        self.index_dict = idx_data
        self._status_cache.clear()
        row_count = self.rowCount()
        if row_count > 0:
            top_left_index = self.index(0, 0)
            bottom_right_index = self.index(row_count - 1, self.columnCount() - 1)
            self.dataChanged.emit(top_left_index, bottom_right_index, [Qt.DisplayRole])
        path = self.rootPath()
        self.setRootPath("")
        self.setRootPath(path)
        self.layoutChanged.emit()