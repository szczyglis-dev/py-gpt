#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.27 21:00:00                  #
# ================================================== #

from PySide6.QtCore import QItemSelectionModel, QPoint
from PySide6.QtGui import QAction, QIcon, Qt
from PySide6.QtWidgets import QMenu, QAbstractItemView

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans


class AssistantList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Assistants select menu

        :param window: main window
        :param id: input id
        """
        super(AssistantList, self).__init__(window)
        self.window = window
        self.id = id
        self.doubleClicked.connect(self.dblclick)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.restore_after_ctx_menu = True
        self._backup_selection = None

        # Enable row-based multi-select with Ctrl/Shift gestures
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Virtual multi-select helpers to suppress business click after Ctrl/Shift
        self._suppress_item_click = False
        self._ctrl_multi_active = False
        self._ctrl_multi_index = None
        self._was_shift_click = False

    # ----------------------------
    # Helpers
    # ----------------------------

    def _selected_indexes(self):
        """Return list of selected row indexes (column 0)."""
        try:
            return list(self.selectionModel().selectedRows())
        except Exception:
            return []

    def _selected_rows(self) -> list[int]:
        """Return list of selected row numbers."""
        try:
            return [ix.row() for ix in self.selectionModel().selectedRows()]
        except Exception:
            return []

    def _has_multi_selection(self) -> bool:
        """Check whether more than one row is selected."""
        try:
            return len(self.selectionModel().selectedRows()) > 1
        except Exception:
            return False

    # ----------------------------
    # Clicks
    # ----------------------------

    def click(self, val):
        """
        Row click handler.

        Suppresses business click when triggered by virtual Ctrl/Shift multi-select
        and when multiple rows are selected.
        """
        # Skip business click right after Ctrl/Shift selection
        if self._suppress_item_click:
            self._suppress_item_click = False
            return

        # Ignore business click if multiple are selected
        if self._has_multi_selection():
            return

        self.window.controller.assistant.select(val.row())

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        row = val.row()
        if row >= 0:
            self.window.controller.assistant.editor.edit(row)

    # ----------------------------
    # Context menu
    # ----------------------------

    def show_context_menu(self, pos: QPoint):
        """
        Context menu event

        :param pos: QPoint
        """
        global_pos = self.viewport().mapToGlobal(pos)
        index = self.indexAt(pos)
        idx = index.row() if index.isValid() else -1

        selected_rows = self._selected_rows()
        multi = len(selected_rows) > 1

        # Allow menu on empty area only when multi-selection is active
        if not index.isValid() and not multi:
            return

        actions = {}
        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('assistant.action.edit'), self)
        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('assistant.action.delete'), self)

        # Edit only for single selection
        actions['edit'].setEnabled(idx >= 0 and not multi)
        actions['edit'].triggered.connect(
            lambda checked=False, item=index: self.action_edit(item)
        )

        # Delete for single or multi; pass list when multi
        if multi:
            actions['delete'].triggered.connect(
                lambda checked=False, rows=list(selected_rows): self.action_delete(rows)
            )
        else:
            actions['delete'].triggered.connect(
                lambda checked=False, item=index: self.action_delete(item)
            )

        menu = QMenu(self)
        menu.addAction(actions['edit'])
        menu.addAction(actions['delete'])

        if idx >= 0 or multi:
            menu.exec_(global_pos)

        # store previous scroll position
        self.store_scroll_position()

        # restore selection if it was backed up
        if self.restore_after_ctx_menu:
            if self._backup_selection is not None:
                self.selectionModel().clearSelection()
                for i in self._backup_selection:
                    self.selectionModel().select(
                        i, QItemSelectionModel.Select | QItemSelectionModel.Rows
                    )
                self._backup_selection = None

        # restore scroll position
        self.restore_after_ctx_menu = True
        self.restore_scroll_position()

    # ----------------------------
    # Context actions
    # ----------------------------

    def action_edit(self, item):
        """
        Edit action handler

        :param item: QModelIndex
        """
        idx = item.row()
        if idx >= 0:
            self.restore_after_ctx_menu = False  # do not restore selection after context menu
            self.window.controller.assistant.editor.edit(idx)

    def action_delete(self, item):
        """
        Delete action handler

        :param item: QModelIndex for single, or list[int] for multi
        """
        if isinstance(item, (list, tuple)):
            self.restore_after_ctx_menu = False  # do not restore selection after context menu
            self.window.controller.assistant.delete(list(item))
            return

        idx = item.row()
        if idx >= 0:
            self.restore_after_ctx_menu = False  # do not restore selection after context menu
            self.window.controller.assistant.delete(idx)

    # ----------------------------
    # Mouse events (virtual multi-select)
    # ----------------------------

    def mousePressEvent(self, event):
        # Ctrl+Left: virtual toggle without business click
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier):
            idx = self.indexAt(event.pos())
            self._suppress_item_click = True
            if idx.isValid():
                self._ctrl_multi_active = True
                self._ctrl_multi_index = idx
                event.accept()
                return
            # Ctrl on empty area -> just suppress business click
            event.accept()
            return

        # Shift+Left: let Qt perform range selection, suppress business click
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier):
            idx = self.indexAt(event.pos())
            self._suppress_item_click = True
            self._was_shift_click = True
            if idx.isValid():
                super().mousePressEvent(event)  # default range selection behavior
            else:
                event.accept()
            return

        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())

            # When multiple are selected, a single click clears the multi-selection
            if self._has_multi_selection():
                self.selectionModel().clearSelection()
                if not index.isValid():
                    event.accept()
                    return
                # continue with default single selection for clicked row

            # Proceed with default handling
            if index.isValid():
                super().mousePressEvent(event)
                return
            else:
                # Click on empty area -> clear any single selection
                self.selectionModel().clearSelection()
                event.accept()
                return

        elif event.button() == Qt.RightButton:
            index = self.indexAt(event.pos())
            sel_model = self.selectionModel()
            selected_rows = [ix.row() for ix in sel_model.selectedRows()]
            multi = len(selected_rows) > 1

            if index.isValid():
                if multi and index.row() in selected_rows:
                    # Keep existing multi-selection; do not alter selection on right click
                    self._backup_selection = None
                else:
                    # Select the clicked row temporarily for single or when clicking outside current multi
                    self._backup_selection = list(sel_model.selectedIndexes())
                    sel_model.clearSelection()
                    sel_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            event.accept()
            return

        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # Finish Shift-range selection: skip business click path
        if event.button() == Qt.LeftButton and self._was_shift_click:
            self._was_shift_click = False
            super().mouseReleaseEvent(event)
            return

        # Finish "virtual" Ctrl toggle on same row
        if event.button() == Qt.LeftButton and self._ctrl_multi_active:
            try:
                idx = self.indexAt(event.pos())
                if idx.isValid() and self._ctrl_multi_index and idx == self._ctrl_multi_index:
                    sel_model = self.selectionModel()
                    sel_model.select(idx, QItemSelectionModel.Toggle | QItemSelectionModel.Rows)
            finally:
                self._ctrl_multi_active = False
                self._ctrl_multi_index = None
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def selectionCommand(self, index, event=None):
        """
        Selection command
        :param index: Index
        :param event: Event
        """
        return super().selectionCommand(index, event)