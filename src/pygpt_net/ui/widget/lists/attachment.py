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

from PySide6.QtCore import Qt, QPoint, QItemSelectionModel
from PySide6.QtGui import QAction, QIcon, QResizeEvent, QImage
from PySide6.QtWidgets import QMenu, QApplication, QAbstractItemView

from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans


class AttachmentList(BaseList):
    _ICON_VIEW = QIcon(":/icons/view.svg")
    _ICON_FOLDER = QIcon(":/icons/folder_filled.svg")
    _ICON_EDIT = QIcon(":/icons/edit.svg")
    _ICON_DELETE = QIcon(":/icons/delete.svg")

    def __init__(self, window=None, id=None):
        """
        Attachments menu

        :param window: main window
        :param id: input id
        """
        super(AttachmentList, self).__init__(window)
        self.window = window
        self.id = id
        self.doubleClicked.connect(self.dblclick)
        self.setHeaderHidden(False)
        self.clicked.disconnect(self.click)

        # Multi-select: rows + Ctrl/Shift gestures, but "virtual" (no business click)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Guards for virtual multi-select (do not trigger controller on Ctrl/Shift)
        self._suppress_item_click = False       # one-shot suppression of business click
        self._ctrl_multi_active = False         # Ctrl gesture in progress
        self._ctrl_multi_index = None           # index pressed with Ctrl
        self._was_shift_click = False           # Shift gesture flag

        # Context menu selection restore
        self._backup_selection = None
        self.restore_after_ctx_menu = True

        hdr = self.header()
        hdr.setStretchLastSection(False)

        self.column_proportion = 0.3
        self._last_width = -1
        self.adjustColumnWidths()

    def adjustColumnWidths(self):
        hdr = self.header()
        cols = hdr.count()
        if cols <= 0:
            return
        total_width = self.viewport().width() or self.width()
        first_column_width = int(total_width * self.column_proportion)
        remaining = max(total_width - first_column_width, 0)
        if self.columnWidth(0) != first_column_width:
            self.setColumnWidth(0, first_column_width)
        if cols > 1:
            other = remaining // (cols - 1)
            for column in range(1, cols):
                if self.columnWidth(column) != other:
                    self.setColumnWidth(column, other)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        w = event.size().width()
        if w != self._last_width:
            self._last_width = w
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
        # Ctrl + Left: toggle visual selection only (virtual multi-select)
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier):
            idx = self.indexAt(event.pos())
            self._ctrl_multi_active = True
            self._ctrl_multi_index = idx if idx.isValid() else None
            self._suppress_item_click = True
            event.accept()
            return

        # Shift + Left: let Qt perform range selection; suppress business click
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier):
            idx = self.indexAt(event.pos())
            self._suppress_item_click = True
            self._was_shift_click = True
            if idx.isValid():
                super(AttachmentList, self).mousePressEvent(event)
            else:
                event.accept()
            return

        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())

            # If multi selected: single left click anywhere clears selection
            if self._has_multi_selection():
                sel_model = self.selectionModel()
                sel_model.clearSelection()
                if not index.isValid():
                    event.accept()
                    return
                # continue to select clicked row as single

            # Default path: allow Qt to select row visually
            super(AttachmentList, self).mousePressEvent(event)

            # Business click only when not suppressed and not multi-selection
            if index.isValid() and not self._suppress_item_click and not self._has_multi_selection():
                mode = self.window.core.config.get('mode')
                self.window.controller.attachment.select(mode, index.row())
            return

        super(AttachmentList, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # Finish Shift-based range selection (keep it virtual)
        if event.button() == Qt.LeftButton and self._was_shift_click:
            self._was_shift_click = False
            super(AttachmentList, self).mouseReleaseEvent(event)
            return

        # Finish Ctrl-based toggle selection (virtual)
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

        super(AttachmentList, self).mouseReleaseEvent(event)

    def click(self, val):
        """
        Click event

        :param val: click event
        """
        return

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        mode = self.window.core.config.get('mode')
        self.window.controller.attachment.select(mode, val.row())

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        mode = self.window.core.config.get('mode')
        pos = event.pos()
        index = self.indexAt(pos)
        idx = index.row() if index.isValid() else -1

        # Read current selection
        sel_model = self.selectionModel()
        selected_indexes = list(sel_model.selectedRows()) if sel_model else []
        selected_rows = [ix.row() for ix in selected_indexes]
        multi = len(selected_rows) > 1

        # Allow menu on empty area only when multi-selection is active
        if not index.isValid() and not multi:
            return

        # If right-click on a row outside current multi-selection, temporarily select that row
        backup_selection = None
        if index.isValid():
            if multi and idx in selected_rows:
                backup_selection = None  # keep multi-selection
            else:
                backup_selection = list(sel_model.selectedIndexes())
                sel_model.clearSelection()
                sel_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                selected_rows = [idx]
                multi = False

        # Resolve attachment(s)
        selected_attachments = []
        try:
            for r in selected_rows:
                a = self.window.controller.attachment.get_by_idx(mode, r)
                if a:
                    selected_attachments.append(a)
        except Exception:
            pass

        attachment = None
        if idx >= 0:
            attachment = self.window.controller.attachment.get_by_idx(mode, idx)

        # Compute flags for file-based actions when multi
        all_files = all(a and a.type == AttachmentItem.TYPE_FILE for a in selected_attachments) if selected_attachments else False

        menu = QMenu(self)
        actions = {}

        # Open / Open dir
        actions['open'] = QAction(self._ICON_VIEW, trans('action.open'), menu)
        actions['open_dir'] = QAction(self._ICON_FOLDER, trans('action.open_dir'), menu)

        # Rename (single only)
        actions['rename'] = QAction(self._ICON_EDIT, trans('action.rename'), menu)

        # Delete (single or multi)
        actions['delete'] = QAction(self._ICON_DELETE, trans('action.delete'), menu)

        fs_actions = None
        path = None

        # Single selection path (preserve previous behavior)
        if not multi and attachment:
            path = attachment.path
            if attachment.type == AttachmentItem.TYPE_FILE:
                fs_actions = self.window.core.filesystem.actions

                # Preview actions (single only)
                if fs_actions.has_preview(path):
                    preview_actions = fs_actions.get_preview(self, path)
                    for preview_action in preview_actions or []:
                        try:
                            preview_action.setParent(menu)
                        except Exception:
                            pass
                        menu.addAction(preview_action)

                # Open / Open dir
                actions['open'].triggered.connect(partial(self._action_open_idx, idx))
                actions['open_dir'].triggered.connect(partial(self._action_open_dir_idx, idx))
                menu.addAction(actions['open'])
                menu.addAction(actions['open_dir'])

                # Use submenu (single only)
                if fs_actions.has_use(path):
                    use_actions = fs_actions.get_use(self, path)
                    use_menu = QMenu(trans('action.use'), menu)
                    for use_action in use_actions or []:
                        try:
                            use_action.setParent(use_menu)
                        except Exception:
                            pass
                        use_menu.addAction(use_action)
                    menu.addMenu(use_menu)

                # Rename (single only)
                actions['rename'].triggered.connect(partial(self._action_rename_idx, idx))
                menu.addAction(actions['rename'])

            # Delete
            actions['delete'].triggered.connect(partial(self._action_delete_idx, idx))
            menu.addAction(actions['delete'])

        else:
            # Multi-selection aggregated actions
            rows = list(selected_rows)

            # Open / Open dir only when all selected are files
            if all_files:
                actions['open'].triggered.connect(partial(self._action_open_multi, rows))
                menu.addAction(actions['open'])

                actions['open_dir'].triggered.connect(partial(self._action_open_dir_multi, rows))
                menu.addAction(actions['open_dir'])

            # Rename disabled for multi; do not add

            # Delete for multi (pass list)
            actions['delete'].triggered.connect(partial(self._action_delete_multi, rows))
            menu.addAction(actions['delete'])

        # Do not trigger controller selection here; keep it virtual
        menu.exec_(event.globalPos())

        # Restore original selection after context menu if it was temporarily changed
        if backup_selection is not None and self.restore_after_ctx_menu:
            sel_model.clearSelection()
            for i in backup_selection:
                sel_model.select(i, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self._backup_selection = None
        self.restore_after_ctx_menu = True

    def keyPressEvent(self, event):
        """
        Key press event to handle undo action

        :param event: Event
        """
        if event.key() == Qt.Key_V and (event.modifiers() & Qt.ControlModifier):
            self.handle_paste()

    def handle_paste(self):
        """Handle clipboard paste"""
        clipboard = QApplication.clipboard()
        source = clipboard.mimeData()
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage):
                self.window.controller.attachment.from_clipboard_image(image)
            return
        if source.hasUrls():
            urls = source.urls()
            for url in urls:
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    self.window.controller.attachment.from_clipboard_url(local_path, all=True)
            return
        if source.hasText():
            text = source.text()
            self.window.controller.attachment.from_clipboard_text(text, all=True)

    def action_open(self, event):
        """
        Open action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.open(mode, idx)

    def action_open_dir(self, event):
        """
        Open dir action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.open_dir(mode, idx)

    def action_rename(self, event):
        """
        Rename action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.rename(mode, idx)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.attachment.delete(idx)

    # Single-index context actions (backward compatible)

    def _action_open_idx(self, idx, checked=False):
        if idx >= 0:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.open(mode, idx)

    def _action_open_dir_idx(self, idx, checked=False):
        if idx >= 0:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.open_dir(mode, idx)

    def _action_rename_idx(self, idx, checked=False):
        if idx >= 0:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.rename(mode, idx)

    def _action_delete_idx(self, idx, checked=False):
        if idx >= 0:
            self.window.controller.attachment.delete(idx)

    # Multi-index context actions (aggregated)

    def _action_open_multi(self, rows: list[int], checked=False):
        """Open multiple attachments: pass list of row indexes."""
        if rows:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.open(mode, list(rows))

    def _action_open_dir_multi(self, rows: list[int], checked=False):
        """Open directories for multiple attachments: pass list of row indexes."""
        if rows:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.open_dir(mode, list(rows))

    def _action_delete_multi(self, rows: list[int], checked=False):
        """Delete multiple attachments: pass list of row indexes."""
        if rows:
            self.window.controller.attachment.delete(list(rows))