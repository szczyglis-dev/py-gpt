#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.27 00:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtWidgets import QMenu, QAbstractItemView

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class AssistantVectorStoreEditorList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Store select menu (in editor)

        :param window: main window
        :param id: parent id
        """
        super(AssistantVectorStoreEditorList, self).__init__(window)
        self.window = window
        self.id = id

        # Virtual multi-select helpers
        self._suppress_item_click = False  # suppress business click after Ctrl/Shift selection
        self._ctrl_multi_active = False    # Ctrl gesture in progress
        self._ctrl_multi_index = None
        self._was_shift_click = False      # Shift range gesture

        # Context menu selection backup (temporary right-click selection)
        self._backup_selection = None
        self.restore_after_ctx_menu = True

        # Row-based multi-selection behavior
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Disable default BaseList click handler; business action is handled manually
        self.clicked.disconnect(self.click)

    # ----------------------------
    # Selection helpers
    # ----------------------------

    def _selected_rows(self) -> list[int]:
        """Return list of selected row numbers."""
        try:
            return sorted([ix.row() for ix in self.selectionModel().selectedRows()])
        except Exception:
            return []

    def _has_multi_selection(self) -> bool:
        """Check whether more than one row is selected."""
        try:
            return len(self.selectionModel().selectedRows()) > 1
        except Exception:
            return False

    # ----------------------------
    # Mouse events (virtual multi-select)
    # ----------------------------

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: mouse event
        """
        # Ctrl+Left: virtual toggle without business click
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

        # Shift+Left: let Qt perform range selection (anchor->clicked), suppress business click
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier):
            idx = self.indexAt(event.pos())
            self._suppress_item_click = True
            self._was_shift_click = True
            if idx.isValid():
                super(AssistantVectorStoreEditorList, self).mousePressEvent(event)
            else:
                event.accept()
            return

        # Plain left click
        if event.button() == Qt.LeftButton:
            idx = self.indexAt(event.pos())

            # When multiple are selected, a single plain click clears the multi-selection.
            if self._has_multi_selection():
                sel_model = self.selectionModel()
                sel_model.clearSelection()
                if not idx.isValid():
                    event.accept()
                    return
                # continue with default single selection for clicked row

            super(AssistantVectorStoreEditorList, self).mousePressEvent(event)
            return

        # Right click: prepare selection for context menu
        if event.button() == Qt.RightButton:
            idx = self.indexAt(event.pos())
            sel_model = self.selectionModel()
            selected_rows = [ix.row() for ix in sel_model.selectedRows()]
            multi = len(selected_rows) > 1

            if idx.isValid():
                if multi and idx.row() in selected_rows:
                    # Keep existing multi-selection; do not alter selection on right click
                    self._backup_selection = None
                else:
                    # Temporarily select the clicked row; backup previous selection to restore later
                    self._backup_selection = list(sel_model.selectedIndexes())
                    sel_model.clearSelection()
                    sel_model.select(idx, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            event.accept()
            return

        super(AssistantVectorStoreEditorList, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # If the click was a Shift-based range selection, bypass business click
        if event.button() == Qt.LeftButton and self._was_shift_click:
            self._was_shift_click = False
            self._suppress_item_click = False
            super(AssistantVectorStoreEditorList, self).mouseReleaseEvent(event)
            return

        # Finish "virtual" Ctrl toggle on same row (no business click)
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

        # Plain left: perform business selection only for single selection
        if event.button() == Qt.LeftButton:
            idx = self.indexAt(event.pos())
            if not self._has_multi_selection():
                if idx.isValid() and not self._suppress_item_click:
                    self.window.controller.assistant.store.select(idx.row())
            self._suppress_item_click = False
            super(AssistantVectorStoreEditorList, self).mouseReleaseEvent(event)
            return

        super(AssistantVectorStoreEditorList, self).mouseReleaseEvent(event)

    def click(self, val):
        # Not used; single-selection business click is handled in mouseReleaseEvent
        pass

    # ----------------------------
    # Context menu
    # ----------------------------

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['refresh'] = QAction(
            QIcon(":/icons/reload.svg"),
            trans('dialog.assistant.store.menu.current.refresh_store'),
            self
        )
        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
        actions['clear'] = QAction(
            QIcon(":/icons/close.svg"),
            trans('dialog.assistant.store.menu.current.clear_files'),
            self
        )
        actions['truncate'] = QAction(
            QIcon(":/icons/delete.svg"),
            trans('dialog.assistant.store.menu.current.truncate_files'),
            self
        )

        menu = QMenu(self)
        menu.addAction(actions['refresh'])
        menu.addAction(actions['delete'])
        menu.addAction(actions['clear'])
        menu.addAction(actions['truncate'])

        index = self.indexAt(event.pos())
        idx = index.row() if index.isValid() else -1

        # Selection state for multi / single
        selected_rows = self._selected_rows()
        multi = len(selected_rows) > 1

        # Allow menu on empty area only when multi-selection is active
        if not index.isValid() and not multi:
            if self._backup_selection is not None and self.restore_after_ctx_menu:
                sel_model = self.selectionModel()
                sel_model.clearSelection()
                for i in self._backup_selection:
                    sel_model.select(i, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                self._backup_selection = None
            return

        # Route actions: pass list on multi, int on single
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

        # Restore selection after context menu if it was temporarily changed
        if self.restore_after_ctx_menu and self._backup_selection is not None:
            sel_model = self.selectionModel()
            sel_model.clearSelection()
            for i in self._backup_selection:
                sel_model.select(i, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            self._backup_selection = None
        self.restore_after_ctx_menu = True

    # ----------------------------
    # Context actions (single or multi)
    # If 'item' is a list/tuple -> pass list of row ints to external code.
    # If 'item' is an int -> pass single row int to external code.
    # ----------------------------

    def action_delete(self, item):
        """
        Delete action handler

        :param item: int row or list of rows
        """
        if isinstance(item, (list, tuple)):
            if item:
                self.restore_after_ctx_menu = False
                self.window.controller.assistant.store.delete_by_idx(list(item))
            return
        idx = int(item)
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.assistant.store.delete_by_idx(idx)

    def action_clear(self, item):
        """
        Clear action handler

        :param item: int row or list of rows
        """
        if isinstance(item, (list, tuple)):
            if item:
                self.restore_after_ctx_menu = False
                self.window.controller.assistant.batch.clear_store_files_by_idx(list(item))
            return
        idx = int(item)
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.assistant.batch.clear_store_files_by_idx(idx)

    def action_truncate(self, item):
        """
        Truncate action handler

        :param item: int row or list of rows
        """
        if isinstance(item, (list, tuple)):
            if item:
                self.restore_after_ctx_menu = False
                self.window.controller.assistant.batch.truncate_store_files_by_idx(list(item))
            return
        idx = int(item)
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.assistant.batch.truncate_store_files_by_idx(idx)

    def action_refresh(self, item):
        """
        Refresh action handler
        """
        if isinstance(item, (list, tuple)):
            if item:
                self.restore_after_ctx_menu = False
                self.window.controller.assistant.store.refresh_by_idx(list(item))
            return
        idx = int(item)
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.assistant.store.refresh_by_idx(idx)