#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #

import datetime
import os

from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import QFileSystemModel


from pygpt_net.utils import trans


class IndexedFileSystemModel(QFileSystemModel):
    def __init__(self, window, index_dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window = window
        self.index_dict = index_dict
        self._status_cache = {}
        # QFileSystemModel reports every not-yet-loaded directory as having
        # children.  That keeps directory loading lazy, but it also makes Qt
        # draw a disclosure arrow for empty directories.  Cache a lightweight
        # one-entry probe so the probe is not repeated during every paint.
        self._children_hint_cache = {}
        self.directoryLoaded.connect(self.refresh_path)
        self.rowsInserted.connect(self._invalidate_children_hint)
        self.rowsRemoved.connect(self._invalidate_children_hint)
        self.modelReset.connect(self._clear_children_hints)
        try:
            self.setReadOnly(False)
        except Exception:
            pass

    def _clear_children_hints(self):
        self._children_hint_cache.clear()

    @staticmethod
    def _children_hint_key(path):
        """Normalize cache keys so Qt/native Windows path forms share one hint."""
        return os.path.normcase(os.path.normpath(path))

    def _invalidate_children_hint(self, parent=QModelIndex(), *_):
        """Invalidate only the directory whose contents changed."""
        try:
            index = parent.siblingAtColumn(0) if parent.isValid() else QModelIndex()
            path = self.filePath(index) if index.isValid() else self.rootPath()
            if path:
                self._children_hint_cache.pop(self._children_hint_key(path), None)
        except Exception:
            # A full clear is still cheap and avoids keeping a stale hint if Qt
            # emits a model notification while the root index is changing.
            self._children_hint_cache.clear()

    def hasChildren(self, parent=QModelIndex()) -> bool:
        """Return accurate expandability without repeatedly scanning directories."""
        if not parent.isValid():
            return super().hasChildren(parent)

        try:
            index = parent.siblingAtColumn(0)
        except Exception:
            index = parent

        if not self.isDir(index):
            return False

        # Once QFileSystemModel has loaded the directory, use its asynchronous
        # cache only.  This is the fast path used for expanded/visited folders.
        if not self.canFetchMore(index):
            return self.rowCount(index) > 0

        path = self.filePath(index)
        if not path:
            return super().hasChildren(index)

        cache_key = self._children_hint_key(path)
        cached = self._children_hint_cache.get(cache_key)
        if cached is not None:
            return cached

        # For an unloaded directory QFileSystemModel otherwise returns True
        # unconditionally.  Probe only until the first entry and cache the
        # result.  This preserves lazy loading and avoids an os.listdir()/full
        # scan on every hasChildren()/paint call.
        try:
            with os.scandir(path) as entries:
                has_children = next(entries, None) is not None
            self._children_hint_cache[cache_key] = has_children
            return has_children
        except OSError:
            # Keep QFileSystemModel's default lazy behaviour for inaccessible
            # or transient paths rather than incorrectly hiding the arrow.
            return super().hasChildren(index)
        except Exception:
            return super().hasChildren(index)

    def refresh_path(self, path):
        index = self.index(path)
        if index.isValid():
            self._status_cache.clear()
            self._children_hint_cache.pop(self._children_hint_key(path), None)
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
        if role == Qt.ToolTipRole and index.isValid():
            return os.path.relpath(self.filePath(index.siblingAtColumn(0)), self.rootPath())
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
        """Get one file's index status lazily from SQLite and cache it."""
        file_id = self.window.core.idx.files.get_id(file_path)
        cached = self._status_cache.get(file_id)
        if cached is not None:
            return cached
        result = self.window.core.idx.get_file_index_status(file_path)
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
        self.index_dict = {}
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

