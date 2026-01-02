#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 20:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtWidgets import QMenu, QAbstractItemView

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class RemoteStoreGoogleEditorList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Store select menu (in editor) - Google File Search

        :param window: main window
        :param id: parent id
        """
        super(RemoteStoreGoogleEditorList, self).__init__(window)
        self.window = window
        self.id = id

        self._suppress_item_click = False
        self._ctrl_multi_active = False
        self._ctrl_multi_index = None
        self._was_shift_click = False

        self._backup_selection = None
        self.restore_after_ctx_menu = True

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Disable BaseList click handler; business action handled manually
        self.clicked.disconnect(self.click)

    def _selected_rows(self) -> list[int]:
        try:
            return sorted([ix.row() for ix in self.selectionModel().selectedRows()])
        except Exception:
            return []

    def _has_multi_selection(self) -> bool:
        try:
            return len(self.selectionModel().selectedRows()) > 1
        except Exception:
            return False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier):
            idx = self.indexAt(event.pos())
            if idx.isValid():
                self._ctrl_multi_active = True
                self._ctrl_multi_index = idx
                self._suppress_item_click = True
                event.accept()
                return
            self._suppress_item_click = True
            event.accept()
            return

        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier):
            idx = self.indexAt(event.pos())
            self._suppress_item_click = True
            self._was_shift_click = True
            if idx.isValid():
                super(RemoteStoreGoogleEditorList, self).mousePressEvent(event)
            else:
                event.accept()
            return

        if event.button() == Qt.LeftButton:
            idx = self.indexAt(event.pos())
            if self._has_multi_selection():
                sel_model = self.selectionModel()
                sel_model.clearSelection()
                if not idx.isValid():
                    event.accept()
                    return
            super(RemoteStoreGoogleEditorList, self).mousePressEvent(event)
            return

        if event.button() == Qt.RightButton:
            idx = self.indexAt(event.pos())
            sel_model = self.selectionModel()
            selected_rows = [ix.row() for ix in sel_model.selectedRows()]
            multi = len(selected_rows) > 1

            if idx.isValid():
                if multi and idx.row() in selected_rows:
                    self._backup_selection = None
                else:
                    self._backup_selection = list(sel_model.selectedIndexes())
                    sel_model.clearSelection()
                    sel_model.select(idx, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            event.accept()
            return

        super(RemoteStoreGoogleEditorList, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._was_shift_click:
            self._was_shift_click = False
            self._suppress_item_click = False
            super(RemoteStoreGoogleEditorList, self).mouseReleaseEvent(event)
            return

        if event.button() == Qt.LeftButton and self._ctrl_multi_active:
            try:
                idx = self.indexAt(event.pos())
                if idx.isValid() and self._ctrl_multi_index and idx == self._ctrl_multi_index:
                    sel_model = self.selectionModel()
                    sel_model.select(idx, QItemSelectionModel.Toggle | QItemSelectionModel.Rows)
            finally:
                self._ctrl_multi_active = False
                self._ctrl_multi_index = None
                self._suppress_item_click = False
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            idx = self.indexAt(event.pos())
            if not self._has_multi_selection():
                if idx.isValid() and not self._suppress_item_click:
                    self.window.controller.remote_store.google.select(idx.row())
            self._suppress_item_click = False
            super(RemoteStoreGoogleEditorList, self).mouseReleaseEvent(event)
            return

        super(RemoteStoreGoogleEditorList, self).mouseReleaseEvent(event)

    def click(self, val):
        pass

    def contextMenuEvent(self, event):
        actions = {}
        actions['refresh'] = QAction(
            QIcon(":/icons/reload.svg"),
            trans('dialog.remote_store.menu.current.refresh_store'),
            self
        )
        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
        actions['clear'] = QAction(
            QIcon(":/icons/close.svg"),
            trans('dialog.remote_store.menu.current.clear_files'),
            self
        )
        actions['truncate'] = QAction(
            QIcon(":/icons/delete.svg"),
            trans('dialog.remote_store.menu.current.truncate_files'),
            self
        )

        menu = QMenu(self)
        menu.addAction(actions['refresh'])
        menu.addAction(actions['delete'])
        menu.addAction(actions['clear'])
        menu.addAction(actions['truncate'])

        index = self.indexAt(event.pos())
        idx = index.row() if index.isValid() else -1

        selected_rows = self._selected_rows()
        multi = len(selected_rows) > 1

        if not index.isValid() and not multi:
            if self._backup_selection is not None and self.restore_after_ctx_menu:
                sel_model = self.selectionModel()
                sel_model.clearSelection()
                for i in self._backup_selection:
                    sel_model.select(i, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                self._backup_selection = None
            return

        if multi:
            actions['refresh'].triggered.connect(lambda: self.action_refresh(list(selected_rows)))
            actions['delete'].triggered.connect(lambda: self.action_delete(list(selected_rows)))
            actions['clear'].triggered.connect(lambda: self.action_clear(list(selected_rows)))
            actions['truncate'].triggered.connect(lambda: self.action_truncate(list(selected_rows)))
        else:
            actions['refresh'].triggered.connect(lambda: self.action_refresh(idx))
            actions['delete'].triggered.connect(lambda: self.action_delete(idx))
            actions['clear'].triggered.connect(lambda: self.action_clear(idx))
            actions['truncate'].triggered.connect(lambda: self.action_truncate(idx))

        menu.exec_(event.globalPos())

        if self.restore_after_ctx_menu and self._backup_selection is not None:
            sel_model = self.selectionModel()
            sel_model.clearSelection()
            for i in self._backup_selection:
                sel_model.select(i, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            self._backup_selection = None
        self.restore_after_ctx_menu = True

    def action_delete(self, item):
        if isinstance(item, (list, tuple)):
            if item:
                self.restore_after_ctx_menu = False
                self.window.controller.remote_store.google.delete_by_idx(list(item))
            return
        idx = int(item)
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.remote_store.google.delete_by_idx(idx)

    def action_clear(self, item):
        if isinstance(item, (list, tuple)):
            if item:
                self.restore_after_ctx_menu = False
                self.window.controller.remote_store.google.batch.clear_store_files_by_idx(list(item))
            return
        idx = int(item)
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.remote_store.google.batch.clear_store_files_by_idx(idx)

    def action_truncate(self, item):
        if isinstance(item, (list, tuple)):
            if item:
                self.restore_after_ctx_menu = False
                self.window.controller.remote_store.google.batch.truncate_store_files_by_idx(list(item))
            return
        idx = int(item)
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.remote_store.google.batch.truncate_store_files_by_idx(idx)

    def action_refresh(self, item):
        if isinstance(item, (list, tuple)):
            if item:
                self.restore_after_ctx_menu = False
                self.window.controller.remote_store.google.refresh_by_idx(list(item))
            return
        idx = int(item)
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.remote_store.google.refresh_by_idx(idx)