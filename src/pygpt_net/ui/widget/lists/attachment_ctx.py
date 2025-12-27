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

from functools import partial

from PySide6.QtCore import Qt, QItemSelectionModel
from PySide6.QtGui import QAction, QIcon, QResizeEvent
from PySide6.QtWidgets import QMenu, QAbstractItemView

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans


class AttachmentCtxList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Ctx Attachments menu

        :param window: main window
        :param id: input id
        """
        super(AttachmentCtxList, self).__init__(window)
        self.window = window
        self.id = id
        self.doubleClicked.connect(self.dblclick)
        self.setHeaderHidden(False)
        self.clicked.disconnect(self.click)

        # Flat rows + virtual multi-select (Ctrl/Shift)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Virtual multi-select guards
        self._suppress_item_click = False
        self._was_shift_click = False

        # Context menu selection restore
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

    def _selected_rows(self) -> list[int]:
        """Return list of selected row numbers."""
        try:
            return [ix.row() for ix in self.selectionModel().selectedRows()]
        except Exception:
            return []

    def _has_multi_selection(self) -> bool:
        """Check whether multiple rows are currently selected."""
        try:
            return len(self.selectionModel().selectedRows()) > 1
        except Exception:
            return False

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: mouse event
        """
        # Ctrl + Left: let Qt toggle selection; block business click afterwards
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier):
            idx = self.indexAt(event.pos())
            self._suppress_item_click = True
            if idx.isValid():
                super(AttachmentCtxList, self).mousePressEvent(event)  # native toggle
            else:
                event.accept()
            return

        # Shift + Left: let Qt perform range selection; suppress business click
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier):
            idx = self.indexAt(event.pos())
            self._suppress_item_click = True
            self._was_shift_click = True
            if idx.isValid():
                super(AttachmentCtxList, self).mousePressEvent(event)
            else:
                event.accept()
            return

        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())

            # When multiple are selected, a single left click anywhere clears selection
            if self._has_multi_selection():
                sel_model = self.selectionModel()
                sel_model.clearSelection()
                if not index.isValid():
                    event.accept()
                    return
                # continue to select clicked row as single

            # Default visual selection
            super(AttachmentCtxList, self).mousePressEvent(event)

            # Business click only when not suppressed and not multi-selection
            if index.isValid() and not self._suppress_item_click and not self._has_multi_selection():
                self.window.controller.assistant.files.select(index.row())
            return

        super(AttachmentCtxList, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # Finish Shift-based range selection (virtual)
        if event.button() == Qt.LeftButton and self._was_shift_click:
            self._was_shift_click = False
            super(AttachmentCtxList, self).mouseReleaseEvent(event)
            return

        # Clear Ctrl suppression flag on release (selection was already toggled by Qt on press)
        if event.button() == Qt.LeftButton and self._suppress_item_click:
            self._suppress_item_click = False
            super(AttachmentCtxList, self).mouseReleaseEvent(event)
            return

        super(AttachmentCtxList, self).mouseReleaseEvent(event)

    def click(self, val):
        """
        Click event

        :param val: click event
        """
        pass

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.assistant.files.select(val.row())

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        def ignore_trigger(func, arg, *args, **kwargs):
            func(arg)

        actions = {}

        index = self.indexAt(event.pos())
        idx = index.row() if index.isValid() else -1

        # Selection state
        sel_model = self.selectionModel()
        selected_indexes = list(sel_model.selectedRows()) if sel_model else []
        selected_rows = [ix.row() for ix in selected_indexes]
        multi = len(selected_rows) > 1

        # Allow menu on empty area only when multi-selection is active
        if not index.isValid() and not multi:
            return

        # Use class-level selection flags (PySide6) for compatibility and clarity
        SelectionFlag = getattr(QItemSelectionModel, "SelectionFlag", QItemSelectionModel)

        # Temporarily adjust selection if right-clicked outside current multi-selection
        backup_selection = None
        if index.isValid():
            if multi and idx in selected_rows:
                backup_selection = None  # keep multi-selection
            else:
                backup_selection = list(sel_model.selectedIndexes())
                sel_model.clearSelection()
                sel_model.select(index, SelectionFlag.Select | SelectionFlag.Rows)
                selected_rows = [idx]
                multi = False

        # Aggregate capabilities across selection (union)
        has_file_any = False
        has_src_any = False
        has_dest_any = False

        rows_for_flags = selected_rows if selected_rows else ([idx] if idx >= 0 else [])

        for r in rows_for_flags:
            try:
                if self.window.controller.chat.attachment.has_file_by_idx(r):
                    has_file_any = True
                if self.window.controller.chat.attachment.has_src_by_idx(r):
                    has_src_any = True
                if self.window.controller.chat.attachment.has_dest_by_idx(r):
                    has_dest_any = True
            except Exception:
                pass

        actions['open'] = QAction(QIcon(":/icons/view.svg"), trans('action.open'), self)
        actions['open_dir_src'] = QAction(QIcon(":/icons/folder.svg"), trans('action.open_dir_src'), self)
        actions['open_dir_dest'] = QAction(QIcon(":/icons/folder.svg"), trans('action.open_dir_storage'), self)
        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)

        menu = QMenu(self)

        if not multi:
            # Single selection: keep legacy path and event-based handlers
            if idx >= 0:
                if has_file_any:
                    actions['open'].triggered.connect(partial(ignore_trigger, self.action_open, event))
                    menu.addAction(actions['open'])
                if has_src_any:
                    actions['open_dir_src'].triggered.connect(partial(ignore_trigger, self.action_open_dir_src, event))
                    menu.addAction(actions['open_dir_src'])
                if has_dest_any:
                    actions['open_dir_dest'].triggered.connect(partial(ignore_trigger, self.action_open_dir_dest, event))
                    menu.addAction(actions['open_dir_dest'])

                actions['delete'].triggered.connect(partial(ignore_trigger, self.action_delete, event))
                menu.addAction(actions['delete'])
        else:
            # Multi selection: show union of available actions and pass list of rows
            rows = list(selected_rows)

            if has_file_any:
                actions['open'].triggered.connect(partial(self._action_open_multi, rows))
                menu.addAction(actions['open'])
            if has_src_any:
                actions['open_dir_src'].triggered.connect(partial(self._action_open_dir_src_multi, rows))
                menu.addAction(actions['open_dir_src'])
            if has_dest_any:
                actions['open_dir_dest'].triggered.connect(partial(self._action_open_dir_dest_multi, rows))
                menu.addAction(actions['open_dir_dest'])

            actions['delete'].triggered.connect(partial(self._action_delete_multi, rows))
            menu.addAction(actions['delete'])

        # Do not perform business selection here; keep selection virtual
        menu.exec_(event.globalPos())

        # Restore original selection after context menu if it was temporarily changed
        if backup_selection is not None and self.restore_after_ctx_menu:
            sel_model.clearSelection()
            for i in backup_selection:
                sel_model.select(i, SelectionFlag.Select | SelectionFlag.Rows)
        self._backup_selection = None
        self.restore_after_ctx_menu = True

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.chat.attachment.delete_by_idx(idx)

    def action_open(self, event):
        """
        Open action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.chat.attachment.open_by_idx(idx)

    def action_open_dir_src(self, event):
        """
        Open source directory action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.chat.attachment.open_dir_src_by_idx(idx)

    def action_open_dir_dest(self, event):
        """
        Open destination directory action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.chat.attachment.open_dir_dest_by_idx(idx)

    # ---- Multi-index context actions (aggregated; pass list[int]) ----

    def _action_delete_multi(self, rows: list[int], checked=False):
        if rows:
            self.window.controller.chat.attachment.delete_by_idx(list(rows))

    def _action_open_multi(self, rows: list[int], checked=False):
        if rows:
            self.window.controller.chat.attachment.open_by_idx(list(rows))

    def _action_open_dir_src_multi(self, rows: list[int], checked=False):
        if rows:
            self.window.controller.chat.attachment.open_dir_src_by_idx(list(rows))

    def _action_open_dir_dest_multi(self, rows: list[int], checked=False):
        if rows:
            self.window.controller.chat.attachment.open_dir_dest_by_idx(list(rows))