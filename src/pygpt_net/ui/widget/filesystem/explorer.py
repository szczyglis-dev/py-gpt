#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

import datetime
import os

from PySide6.QtCore import Qt, QModelIndex, QDir
from PySide6.QtGui import QAction, QIcon, QCursor, QResizeEvent
from PySide6.QtWidgets import QTreeView, QMenu, QWidget, QVBoxLayout, QFileSystemModel, QLabel, QHBoxLayout, \
    QPushButton, QSizePolicy

from pygpt_net.core.tabs import Tab
from pygpt_net.ui.widget.element.button import ContextMenuButton
from pygpt_net.ui.widget.element.labels import HelpLabel
from pygpt_net.utils import trans
import pygpt_net.icons_rc


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

        # btn with icon
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
                name = idx['name'] + " (" + idx['id'] + ")"
                action = menu.addAction("IDX: " + name)
                action.triggered.connect(
                    lambda checked=False,
                           id=id: self.window.controller.idx.indexer.index_all_files(id)
                )
        menu.exec_(parent.mapToGlobal(pos))

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
                name = idx['name'] + " (" + idx['id'] + ")"
                action = menu.addAction("IDX: " + name)
                action.triggered.connect(
                    lambda checked=False,
                           id=id: self.window.controller.idx.indexer.clear(id)
                )
        menu.exec_(parent.mapToGlobal(pos))

    def adjustColumnWidths(self):
        """Adjust column widths"""
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
            preview_actions = []
            use_actions = []

            if self.window.core.filesystem.actions.has_preview(path):
                preview_actions = self.window.core.filesystem.actions.get_preview(self, path)

            # open file
            actions['open'] = QAction(QIcon(":/icons/view.svg"), trans('action.open'), self)
            actions['open'].triggered.connect(
                lambda: self.action_open(path),
            )

            # open in file manager
            actions['open_dir'] = QAction(QIcon(":/icons/folder_filled.svg"), trans('action.open_dir'), self)
            actions['open_dir'].triggered.connect(
                lambda: self.action_open_dir(path),
            )

            # download
            actions['download'] = QAction(QIcon(":/icons/download.svg"), trans('action.download'), self)
            actions['download'].triggered.connect(
                lambda: self.window.controller.files.download_local(path),
            )

            # rename
            actions['rename'] = QAction(QIcon(":/icons/edit.svg"), trans('action.rename'), self)
            actions['rename'].triggered.connect(
                lambda: self.action_rename(path),
            )

            # duplicate
            actions['duplicate'] = QAction(QIcon(":/icons/stack.svg"), trans('action.duplicate'), self)
            actions['duplicate'].triggered.connect(
                lambda: self.window.controller.files.duplicate_local(path, ""),
            )

            if os.path.isdir(path):
                parent = path
            else:
                parent = os.path.dirname(path)

            # touch file
            actions['touch'] = QAction(QIcon(":/icons/add.svg"), trans('action.touch'), self)
            actions['touch'].triggered.connect(
                lambda: self.window.controller.files.touch_file(parent),
            )

            # make dir
            actions['mkdir'] = QAction(QIcon(":/icons/add_folder.svg"), trans('action.mkdir'), self)
            actions['mkdir'].triggered.connect(
                lambda: self.action_make_dir(parent),
            )

            # refresh
            actions['refresh'] = QAction(QIcon(":/icons/reload.svg"), trans('action.refresh'), self)
            actions['refresh'].triggered.connect(
                lambda: self.window.controller.files.update_explorer(),
            )

            # upload to dir
            actions['upload'] = QAction(QIcon(":/icons/upload.svg"), trans('action.upload'), self)
            actions['upload'].triggered.connect(
                lambda: self.window.controller.files.upload_local(parent),
            )

            # delete
            actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
            actions['delete'].triggered.connect(
                lambda: self.action_delete(path),
            )

            # menu
            menu = QMenu(self)
            if preview_actions:
                for action in preview_actions:
                    menu.addAction(action)
            menu.addAction(actions['open'])
            menu.addAction(actions['open_dir'])

            # use menu
            use_menu = QMenu(trans('action.use'), self)

            # use
            if not os.path.isdir(path):
                # use as attachment
                actions['use_attachment'] = QAction(
                    QIcon(":/icons/attachment.svg"),
                    trans('action.use.attachment'),
                    self,
                )
                actions['use_attachment'].triggered.connect(
                    lambda: self.window.controller.files.use_attachment(path),
                )
                # use by filetype
                if self.window.core.filesystem.actions.has_use(path):
                    use_actions = self.window.core.filesystem.actions.get_use(self, path)

            # copy work path
            actions['use_copy_work_path'] = QAction(
                QIcon(":/icons/copy.svg"),
                trans('action.use.copy_work_path'),
                self,
            )
            actions['use_copy_work_path'].triggered.connect(
                lambda: self.window.controller.files.copy_work_path(path),
            )

            # copy sys path
            actions['use_copy_sys_path'] = QAction(
                QIcon(":/icons/copy.svg"),
                trans('action.use.copy_sys_path'),
                self,
            )
            actions['use_copy_sys_path'].triggered.connect(
                lambda: self.window.controller.files.copy_sys_path(path),
            )

            # use read cmd
            actions['use_read_cmd'] = QAction(QIcon(":/icons/view.svg"), trans('action.use.read_cmd'), self)
            actions['use_read_cmd'].triggered.connect(
                lambda: self.window.controller.files.make_read_cmd(path),
            )

            # add actions to menu
            if not os.path.isdir(path):
                use_menu.addAction(actions['use_attachment'])

            # use by type
            if use_actions:
                for action in use_actions:
                    use_menu.addAction(action)

            # use common actions
            use_menu.addAction(actions['use_copy_work_path'])
            use_menu.addAction(actions['use_copy_sys_path'])
            use_menu.addAction(actions['use_read_cmd'])
            menu.addMenu(use_menu)

            # remove from index
            file_id = self.window.core.idx.files.get_id(path)
            remove_actions = []
            for idx in self.index_data:
                items = self.index_data[idx]
                if file_id in items:
                    action = QAction(QIcon(":/icons/delete.svg"), trans("action.idx.remove") + ": " + idx, self)
                    action.triggered.connect(
                        lambda checked=False,
                               idx=idx,
                               file_id=file_id: self.action_idx_remove(file_id, idx)  # by file_id, not path
                    )
                    remove_actions.append(action)

            # add to index if allowed
            if self.window.core.idx.indexing.is_allowed(path):
                idx_menu = QMenu(trans('action.idx'), self)
                idx_list = self.window.core.config.get('llama.idx.list')
                if len(idx_list) > 0 or len(remove_actions) > 0:
                    # add
                    if len(idx_list) > 0:
                        for idx in idx_list:
                            id = idx['id']
                            name = idx['name'] + " (" + idx['id'] + ")"
                            action = QAction(QIcon(":/icons/db.svg"), "IDX: " + name, self)
                            action.triggered.connect(
                                lambda checked=False,
                                       id=id,
                                       path=path: self.action_idx(path, id)
                            )
                            idx_menu.addAction(action)

                # remove
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
            # no item selected
            actions = {}

            # touch file
            actions['touch'] = QAction(QIcon(":/icons/add.svg"), trans('action.touch'), self)
            actions['touch'].triggered.connect(
                lambda: self.window.controller.files.touch_file(self.directory),
            )

            # open in file manager
            actions['open_dir'] = QAction(QIcon(":/icons/folder_filled.svg"), trans('action.open_dir'), self)
            actions['open_dir'].triggered.connect(
                lambda: self.action_open_dir(self.directory),
            )

            # make dir in dir
            actions['mkdir'] = QAction(QIcon(":/icons/add_folder.svg"), trans('action.mkdir'), self)
            actions['mkdir'].triggered.connect(
                lambda: self.action_make_dir(self.directory),
            )

            # upload in dir
            actions['upload'] = QAction(QIcon(":/icons/upload.svg"), trans('action.upload'), self)
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
        self.directoryLoaded.connect(self.refresh_path)

    def refresh_path(self, path):
        index = self.index(path)
        if index.isValid():
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
        # index status
        if index.column() == self.columnCount() - 1:
            if role == Qt.DisplayRole:
                file_path = self.filePath(index.siblingAtColumn(0))
                status = self.get_index_status(file_path)   # get index status
                if status['indexed']:
                    ts = datetime.datetime.fromtimestamp(status['last_index_at'])
                    # check if today
                    if ts.date() == datetime.date.today():
                        dt = ts.strftime("%H:%M")
                    else:
                        dt = ts.strftime("%Y-%m-%d %H:%M")
                    content = ''
                    content += dt
                    content += ' (' + ",".join(status['indexed_in']) + ')'
                else:
                    content = '-'  # if file not indexed
                return content
        # modified date
        elif index.column() == self.columnCount() - 2:
            if role == Qt.DisplayRole:
                dt = self.lastModified(index)
                data = dt.toString("yyyy-MM-dd HH:mm:ss")
                ts = dt.toSecsSinceEpoch()
                dt_from_ts = datetime.datetime.fromtimestamp(ts)
                if dt_from_ts.date() == datetime.date.today():
                    data = dt_from_ts.strftime("%H:%M")
                else:
                    data = dt_from_ts.strftime("%Y-%m-%d %H:%M")
                file_path = self.filePath(index.siblingAtColumn(0))
                status = self.get_index_status(file_path)  # get index status
                if status['indexed']:
                    # if modified date is newer, mark file with *
                    if 'last_index_at' in status and status['last_index_at'] < dt.toSecsSinceEpoch():
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
        indexed_in = sorted(
            indexed_in,
            key=lambda x: indexed_timestamps[x],
            reverse=True,
        )
        if len(indexed_in) > 0:
            return {
                'indexed': True,
                'indexed_in': indexed_in,
                'last_index_at': last_index_at,
            }
        else:
            return {
                'indexed': False,
            }

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
        top_left_index = self.index(0, 0)
        bottom_right_index = self.index(self.rowCount() - 1, self.columnCount() - 1)
        path = self.rootPath()
        self.dataChanged.emit(top_left_index, bottom_right_index, [Qt.DisplayRole])
        self.setRootPath("")
        self.setRootPath(path)
        self.layoutChanged.emit()
