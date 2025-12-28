#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.28 04:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QAbstractItemView

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans


class ProfileList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Profile menu (in editor)

        :param window: main window
        :param id: parent id
        """
        super(ProfileList, self).__init__(window)
        self.window = window
        self.id = id

        # Enable row-based multi-select with native Ctrl/Shift gestures
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Context menu restore helper
        self._backup_selection = None
        self.restore_after_ctx_menu = True

    def _selected_rows(self) -> list[int]:
        """Return list of selected row numbers."""
        try:
            return [ix.row() for ix in self.selectionModel().selectedRows()]
        except Exception:
            return []

    def _has_multi_selection(self) -> bool:
        """Return True when multiple rows are selected."""
        try:
            return len(self.selectionModel().selectedRows()) > 1
        except Exception:
            return False

    def mousePressEvent(self, event):
        """
        Mouse press event
        - Ctrl: let Qt toggle selection (virtual; no business action).
        - Shift: let Qt range-select (virtual).
        - If multiple are selected: a single left click anywhere clears selection.
        """
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier):
            idx = self.indexAt(event.pos())
            if idx.isValid():
                super(ProfileList, self).mousePressEvent(event)  # native toggle
            else:
                event.accept()
            return

        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier):
            idx = self.indexAt(event.pos())
            if idx.isValid():
                super(ProfileList, self).mousePressEvent(event)  # native range
            else:
                event.accept()
            return

        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            # Clear multi-selection with a single click (also on empty area)
            if self._has_multi_selection():
                sel_model = self.selectionModel()
                sel_model.clearSelection()
                if not index.isValid():
                    event.accept()
                    return
            # Default selection behavior
            super(ProfileList, self).mousePressEvent(event)
            return

        super(ProfileList, self).mousePressEvent(event)

    def click(self, val):
        pass

    def contextMenuEvent(self, event):
        """
        Context menu event
        - Shows menu on a row, or on empty area when multi-selection is active.
        - For multi-selection, actions pass list[int] of selected rows.
        - For single selection, actions pass single int (legacy behavior).
        """
        actions = {}
        actions['use'] = QAction(QIcon(":/icons/check.svg"), trans('action.use'), self)
        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('action.edit'), self)
        actions['duplicate'] = QAction(QIcon(":/icons/copy.svg"), trans('action.duplicate'), self)
        actions['reset'] = QAction(QIcon(":/icons/close.svg"), trans('action.reset'), self)
        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.profile.delete'), self)
        actions['delete_all'] = QAction(QIcon(":/icons/delete.svg"), trans('action.profile.delete_all'), self)

        # Hit test
        index = self.indexAt(event.pos())
        idx = index.row() if index.isValid() else -1

        # Current selection state
        sel_model = self.selectionModel()
        selected_indexes = list(sel_model.selectedRows()) if sel_model else []
        selected_rows = [ix.row() for ix in selected_indexes]
        multi = len(selected_rows) > 1

        # Allow menu on empty area only when multi-selection is active
        if not index.isValid() and not multi:
            return

        # If right-click outside the current multi-selection, temporarily select clicked row
        backup_selection = None
        if index.isValid():
            if multi and idx in selected_rows:
                backup_selection = None  # keep selection as-is
            else:
                backup_selection = list(sel_model.selectedIndexes())
                sel_model.clearSelection()
                sel_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                selected_rows = [idx]
                multi = False

        menu = QMenu(self)

        if not multi:
            # Single: keep legacy behavior (pass single index via event)
            menu.addAction(actions['edit'])
            actions['edit'].triggered.connect(lambda: self.action_edit(event))

            menu.addAction(actions['use'])
            actions['use'].triggered.connect(lambda: self.action_use(event))

            menu.addAction(actions['duplicate'])
            actions['duplicate'].triggered.connect(lambda: self.action_duplicate(event))

            menu.addAction(actions['reset'])
            actions['reset'].triggered.connect(lambda: self.action_reset(event))

            menu.addAction(actions['delete'])
            actions['delete'].triggered.connect(lambda: self.action_delete(event))

            menu.addAction(actions['delete_all'])
            actions['delete_all'].triggered.connect(lambda: self.action_delete_all(event))
        else:
            # Multi: keep only actions that make sense in bulk; Use/Edit/Duplicate are single-only
            rows = list(selected_rows)

            menu.addAction(actions['reset'])
            actions['reset'].triggered.connect(lambda checked=False, r=rows: self._action_reset_multi(r))

            menu.addAction(actions['delete'])
            actions['delete'].triggered.connect(lambda checked=False, r=rows: self._action_delete_multi(r))

            menu.addAction(actions['delete_all'])
            actions['delete_all'].triggered.connect(lambda checked=False, r=rows: self._action_delete_all_multi(r))

        # Show menu
        if index.isValid() or multi:
            menu.exec_(event.globalPos())

        # Restore selection after context menu if it was temporarily changed
        if backup_selection is not None and self.restore_after_ctx_menu:
            sel_model.clearSelection()
            for i in backup_selection:
                sel_model.select(i, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self._backup_selection = None
        self.restore_after_ctx_menu = True

    # ---------- Single-item handlers (legacy; keep unchanged signatures) ----------

    def action_use(self, event):
        """
        Use action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.settings.profile.select_by_idx(idx)

    def action_duplicate(self, event):
        """
        Duplicate action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.settings.profile.duplicate_by_idx(idx)

    def action_reset(self, event):
        """
        Reset action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.settings.profile.reset_by_idx(idx)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.settings.profile.delete_by_idx(idx)

    def action_delete_all(self, event):
        """
        Delete all action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.settings.profile.delete_all_by_idx(idx)

    def action_edit(self, event):
        """
        Edit action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.settings.profile.edit_by_idx(idx)

    # ---------- Multi-item handlers (new; pass list[int]) ----------

    def _action_reset_multi(self, rows: list[int]):
        if rows:
            self.window.controller.settings.profile.reset_by_idx(list(rows))

    def _action_delete_multi(self, rows: list[int]):
        if rows:
            self.window.controller.settings.profile.delete_by_idx(list(rows))

    def _action_delete_all_multi(self, rows: list[int]):
        if rows:
            self.window.controller.settings.profile.delete_all_by_idx(list(rows))