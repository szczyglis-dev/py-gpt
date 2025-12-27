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

from PySide6.QtGui import QAction, QIcon, QResizeEvent, Qt
from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QMenu, QAbstractItemView

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans


class UploadedFileList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Attachments menu

        :param window: main window
        :param id: input id
        """
        super(UploadedFileList, self).__init__(window)
        self.window = window
        self.id = id

        # double click selects item (business action)
        self.doubleClicked.connect(self.dblclick)

        # keep header visible here
        self.setHeaderHidden(False)

        # disable default click handler from BaseList; we drive selection manually
        self.clicked.disconnect(self.click)

        # Flat, row-based, multi-select behavior
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Virtual multi-select helpers
        self._suppress_item_click = False  # suppress business click after Ctrl/Shift selection
        self._ctrl_multi_active = False    # Ctrl gesture in progress
        self._ctrl_multi_index = None
        self._was_shift_click = False      # Shift range gesture

        # Context menu selection backup (temporary right-click selection)
        self._backup_selection = None
        self.restore_after_ctx_menu = True

        self.header = self.header()
        self.header.setStretchLastSection(False)

        self.column_proportion = 0.3
        self.adjustColumnWidths()

    def adjustColumnWidths(self):
        total_width = self.width()
        first_column_width = int(total_width * self.column_proportion)
        self.setColumnWidth(0, first_column_width)
        for column in range(1, 4):
            self.setColumnWidth(column, (total_width - first_column_width) // (4 - 1))

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.adjustColumnWidths()

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
            # Ctrl on empty space -> just suppress
            self._suppress_item_click = True
            event.accept()
            return

        # Shift+Left: let Qt perform range selection, but suppress business click
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier):
            idx = self.indexAt(event.pos())
            self._suppress_item_click = True
            self._was_shift_click = True
            if idx.isValid():
                super(UploadedFileList, self).mousePressEvent(event)
            else:
                event.accept()
            return

        # Plain left click
        if event.button() == Qt.LeftButton:
            idx = self.indexAt(event.pos())

            # When multiple are selected, a single plain click clears the multi-selection.
            # If clicked on empty area: just clear and return.
            if self._has_multi_selection():
                sel_model = self.selectionModel()
                sel_model.clearSelection()
                if not idx.isValid():
                    event.accept()
                    return
                # continue with default single selection for clicked row

            # Perform default selection handling (no business click here)
            super(UploadedFileList, self).mousePressEvent(event)
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

        super(UploadedFileList, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # If the click was a Shift-based range selection, bypass business click
        if event.button() == Qt.LeftButton and self._was_shift_click:
            self._was_shift_click = False
            self._suppress_item_click = False
            super(UploadedFileList, self).mouseReleaseEvent(event)
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
                    self.window.controller.assistant.files.select(idx.row())
            self._suppress_item_click = False
            super(UploadedFileList, self).mouseReleaseEvent(event)
            return

        super(UploadedFileList, self).mouseReleaseEvent(event)

    def click(self, val):
        """
        Click event

        :param val: click event
        """
        # Not used; single-selection business click is handled in mouseReleaseEvent
        pass

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        row = val.row()
        if row >= 0:
            self.window.controller.assistant.files.select(row)

    # ----------------------------
    # Context menu
    # ----------------------------

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        # actions['download'] = QAction(QIcon(":/icons/download.svg"), trans('action.download'), self)
        menu = QMenu(self)
        # menu.addAction(actions['download'])  # not allowed for download files with purpose: assistants :(
        index = self.indexAt(event.pos())
        idx = index.row() if index.isValid() else -1

        # Selection state for multi / single
        selected_rows = self._selected_rows()
        multi = len(selected_rows) > 1

        # Allow menu on empty area only when multi-selection is active
        if not index.isValid() and not multi:
            # Restore selection if it was temporarily changed on right click
            if self._backup_selection is not None and self.restore_after_ctx_menu:
                sel_model = self.selectionModel()
                sel_model.clearSelection()
                for i in self._backup_selection:
                    sel_model.select(i, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                self._backup_selection = None
            return

        # Route actions: pass list on multi, int on single
        if multi:
            # actions['rename'] = QAction(QIcon(":/icons/edit.svg"), trans('action.rename'), self)
            actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
            # actions['rename'].triggered.connect(lambda: self.action_rename(list(selected_rows)))
            actions['delete'].triggered.connect(lambda: self.action_delete(list(selected_rows)))
            # menu.addAction(actions['rename'])
            menu.addAction(actions['delete'])
            # actions['download'].triggered.connect(lambda: self.action_download(list(selected_rows)))
        else:
            # Keep legacy behavior: on single right click also select item in controller
            if idx >= 0:
                self.window.controller.assistant.files.select(idx)
            actions['rename'] = QAction(QIcon(":/icons/edit.svg"), trans('action.rename'), self)
            actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
            actions['rename'].triggered.connect(lambda: self.action_rename(idx))
            actions['delete'].triggered.connect(lambda: self.action_delete(idx))
            menu.addAction(actions['rename'])
            menu.addAction(actions['delete'])
            # actions['download'].triggered.connect(lambda: self.action_download(idx))
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

    def action_rename(self, item):
        """
        Rename action handler

        :param item: int row or list of rows
        """
        if isinstance(item, (list, tuple)):
            if item:
                self.restore_after_ctx_menu = False
                self.window.controller.assistant.files.rename(list(item))
            return
        idx = int(item)
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.assistant.files.rename(idx)

    def action_download(self, item):
        """
        Download action handler

        :param item: int row or list of rows
        """
        if isinstance(item, (list, tuple)):
            if item:
                self.restore_after_ctx_menu = False
                self.window.controller.assistant.files.download(list(item))
            return
        idx = int(item)
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.assistant.files.download(idx)

    def action_delete(self, item):
        """
        Delete action handler

        :param item: int row or list of rows
        """
        if isinstance(item, (list, tuple)):
            if item:
                self.restore_after_ctx_menu = False
                self.window.controller.assistant.files.delete(list(item))
            return
        idx = int(item)
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.assistant.files.delete(idx)