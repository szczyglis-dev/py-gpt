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

from PySide6.QtCore import QPoint, QItemSelectionModel, Qt, QEventLoop, QTimer, QMimeData
from PySide6.QtGui import QAction, QIcon, QCursor, QDrag, QPainter, QPixmap, QPen, QColor
from PySide6.QtWidgets import QMenu, QAbstractItemView, QApplication

from pygpt_net.core.types import (
    MODE_EXPERT,
)
from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans


class PresetList(BaseList):
    _ICO_EDIT = QIcon(":/icons/edit.svg")
    _ICO_COPY = QIcon(":/icons/copy.svg")
    _ICO_UNDO = QIcon(":/icons/undo.svg")
    _ICO_DELETE = QIcon(":/icons/delete.svg")
    _ICO_CHECK = QIcon(":/icons/check.svg")
    _ICO_CLOSE = QIcon(":/icons/close.svg")
    _ICO_UP = QIcon(":/icons/collapse.svg")
    _ICO_DOWN = QIcon(":/icons/expand.svg")

    ROLE_UUID = Qt.UserRole + 1
    ROLE_ID = Qt.UserRole + 2
    ROLE_IS_SPECIAL = Qt.UserRole + 3

    def __init__(self, window=None, id=None):
        """
        Presets select menu

        :param window: main window
        :param id: input id
        """
        super(PresetList, self).__init__(window)
        self.window = window
        self.id = id

        self.doubleClicked.connect(self.dblclick)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self._backup_selection = None
        self.restore_after_ctx_menu = True

        # Flat list behavior
        self.setRootIsDecorated(False)
        self.setItemsExpandable(False)
        self.setUniformRowHeights(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # ExtendedSelection enables Ctrl/Shift multi-select gestures
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # Drag & drop state
        self._dnd_enabled = False
        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)  # switched dynamically
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragDropOverwriteMode(False)
        # We use our own visual indicator for drop position
        self.setDropIndicatorShown(False)

        self._press_pos = None
        self._press_index = None
        self._press_backup_selection = None
        self._press_backup_current = None
        self._dragging = False
        self._dragged_was_selected = False

        # Virtual multi-select: suppress single-item business click once (Ctrl/Shift)
        self._suppress_item_click = False
        # Flag for "virtual" Ctrl multi-select gesture
        self._ctrl_multi_active = False
        self._ctrl_multi_index = None
        # Guard to detect Shift-click range selection and bypass single-select follow-ups
        self._was_shift_click = False

        # Mark that we already applied selection at drag start (one-shot per DnD)
        self._drag_selection_applied = False

        # ID-based selection persistence (single selection list)
        self._saved_selection_ids = None

        # Defer refresh payload after drop (DnD teardown must finish first)
        self._pending_after_drop = None

        # Guard against input during model rebuild (prevents crashes on quick clicks)
        self._model_updating = False

        # Keep original selection IDs before opening context menu (right-click)
        self._ctx_menu_original_ids = None

        # One-shot forced selection after refresh (list of ROLE_ID)
        self._selection_override_ids = None

        # Custom drop indicator (visual only)
        self._drop_indicator_active = False
        # seam row for indicator (row under which the line is drawn)
        self._drop_indicator_to_row = -1
        self._drop_indicator_padding = 6  # visual left/right padding

        # Short-lived scroll freeze to prevent jumps during click-triggered model refresh
        self._scroll_freeze_depth = 0
        self._scroll_freeze_timer = None
        self._pending_scroll_value = None
        self._pending_refocus_role_id = None

    # -------- Public helpers to protect updates --------

    def begin_model_update(self):
        """Temporarily block user interaction while the model/view is rebuilt."""
        self._model_updating = True
        self.setEnabled(False)

    def end_model_update(self):
        """Re-enable interaction after model/view rebuild is complete."""
        self.setEnabled(True)
        self._model_updating = False
        # If there is a pending scroll/selection stabilization, apply it right after update
        self._apply_pending_scroll()
        self._apply_pending_refocus()
        QTimer.singleShot(0, self._apply_pending_scroll)
        QTimer.singleShot(0, self._apply_pending_refocus)
        # Unfreeze shortly after everything settled in the event loop
        QTimer.singleShot(50, self._unfreeze_scroll)

    # ---------------------------------------------------

    # -------- Scroll freeze helpers (prevent accidental jumps on click) --------

    def _freeze_scroll(self, ms: int = 250):
        """
        Freeze scrollTo() effects for a very short time and keep current scroll value.
        This avoids jumps caused by programmatic scroll during selection/refresh.
        """
        try:
            sb = self.verticalScrollBar()
        except Exception:
            sb = None
        if sb is not None:
            self._pending_scroll_value = sb.value()
        self._scroll_freeze_depth += 1

        # Apply stabilization now and on next frame(s)
        QTimer.singleShot(0, self._apply_pending_scroll)
        QTimer.singleShot(16, self._apply_pending_scroll)

        # Auto-unfreeze after given duration
        if self._scroll_freeze_timer:
            try:
                self._scroll_freeze_timer.stop()
            except Exception:
                pass
        self._scroll_freeze_timer = QTimer(self)
        self._scroll_freeze_timer.setSingleShot(True)
        self._scroll_freeze_timer.timeout.connect(self._unfreeze_scroll)
        self._scroll_freeze_timer.start(max(50, int(ms)))

    def _apply_pending_scroll(self):
        """Re-apply saved scroll position when frozen."""
        if self._pending_scroll_value is None:
            return
        try:
            sb = self.verticalScrollBar()
        except Exception:
            sb = None
        if sb is not None:
            sb.setValue(self._pending_scroll_value)

    def _unfreeze_scroll(self):
        """Release the temporary scroll freeze."""
        if self._scroll_freeze_depth > 0:
            self._scroll_freeze_depth -= 1
        if self._scroll_freeze_depth <= 0:
            self._scroll_freeze_depth = 0
            self._pending_scroll_value = None

    def scrollTo(self, index, hint=QAbstractItemView.EnsureVisible):
        """
        Temporarily suppress automatic scrolling while frozen.
        This prevents list jumping when selection triggers scrollTo during refresh.
        """
        if self._scroll_freeze_depth > 0:
            self._apply_pending_scroll()
            return
        return super().scrollTo(index, hint)

    def _apply_pending_refocus(self):
        """
        Ensure selection stays on the intended item (by ROLE_ID) after a model refresh.
        Does not force scrolling when scroll is frozen.
        """
        pid = self._pending_refocus_role_id
        if not pid:
            return
        model = self.model()
        if model is None:
            return
        target_idx = None
        try:
            for r in range(model.rowCount()):
                ix = model.index(r, 0)
                if ix.data(self.ROLE_ID) == pid:
                    target_idx = ix
                    break
        except Exception:
            target_idx = None

        if target_idx is not None and target_idx.isValid():
            try:
                sel_model = self.selectionModel()
                if sel_model:
                    prev_unlocked = getattr(self, "unlocked", True)
                    self.unlocked = True
                    try:
                        sel_model.clearSelection()
                        sel_model.select(target_idx, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
                        self.setCurrentIndex(target_idx)
                    finally:
                        self.unlocked = prev_unlocked
                # If refocus succeeded, clear the pending marker
                self._pending_refocus_role_id = None
            except Exception:
                # Keep pending id for next attempt if apply failed
                pass

    # --------------------------------------------------------------------------

    def set_dnd_enabled(self, enabled: bool):
        """
        Toggle DnD behaviour at runtime.
        Using DragDrop (not InternalMove) to avoid implicit Qt reordering.
        We also disable the native drop indicator and render our own line.
        """
        self._dnd_enabled = bool(enabled)
        if self._dnd_enabled:
            self.setDragEnabled(True)
            self.setAcceptDrops(True)
            self.setDragDropMode(QAbstractItemView.DragDrop)
            self.setDropIndicatorShown(False)  # use custom indicator
        else:
            self.setDragEnabled(False)
            self.setAcceptDrops(False)
            self.setDragDropMode(QAbstractItemView.NoDragDrop)
            self.setDropIndicatorShown(False)
            self.unsetCursor()
        self._clear_drop_indicator()  # ensure clean state

    def backup_selection(self):
        """
        Persist selected preset identity (by ROLE_ID) instead of raw indexes.
        """
        try:
            sel_rows = self.selectionModel().selectedRows()
            ids = []
            for ix in sel_rows:
                pid = ix.data(self.ROLE_ID)
                if pid:
                    ids.append(str(pid))
            self._saved_selection_ids = ids if ids else None
        except Exception:
            self._saved_selection_ids = None

    def restore_selection(self):
        """
        Restore selection by ROLE_ID to keep it attached to the same item regardless of position.
        """
        ids = self._saved_selection_ids or []
        self._saved_selection_ids = None
        if not ids:
            return
        model = self.model()
        if model is None:
            return
        target_id = ids[0]
        sel_model = self.selectionModel()
        prev_unlocked = self.unlocked
        self.unlocked = True
        try:
            sel_model.clearSelection()
            first_idx = None
            for r in range(model.rowCount()):
                idx = model.index(r, 0)
                pid = idx.data(self.ROLE_ID)
                if pid == target_id:
                    first_idx = idx
                    break
            if first_idx is not None and first_idx.isValid():
                sel_model.select(first_idx, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
                self.setCurrentIndex(first_idx)
                self.scrollTo(first_idx)
        finally:
            self.unlocked = prev_unlocked

    def _current_selected_ids(self) -> list[str]:
        """Read current selection IDs (ROLE_ID)."""
        try:
            return [ix.data(self.ROLE_ID) for ix in self.selectionModel().selectedRows() if ix.data(self.ROLE_ID)]
        except Exception:
            return []

    def click(self, val):
        """Row click handler; select by ID (stable under reordering)."""
        if self._model_updating:
            return

        # Suppress business click after virtual Ctrl/Shift selection
        if self._suppress_item_click:
            self._suppress_item_click = False
            return

        # Ignore business click if multiple rows are selected
        if self._has_multi_selection():
            return

        index = val
        if not index.isValid():
            return
        preset_id = index.data(self.ROLE_ID)
        if preset_id:
            # Freeze scroll and remember the intended selection to re-apply after any refresh
            self._freeze_scroll(300)
            self._pending_refocus_role_id = preset_id
            self.window.controller.presets.select_by_id(preset_id)
            # Re-apply selection in next ticks to win races with late refresh
            QTimer.singleShot(0, self._apply_pending_refocus)
            QTimer.singleShot(50, self._apply_pending_refocus)
            self.selection = self.selectionModel().selection()
            return
        row = index.row()
        if row >= 0:
            self._freeze_scroll(300)
            self.window.controller.presets.select(row)
            QTimer.singleShot(0, self._apply_pending_refocus)
            QTimer.singleShot(50, self._apply_pending_refocus)
            self.selection = self.selectionModel().selection()

    def dblclick(self, val):
        """Double click event"""
        if self._model_updating:
            return
        row = val.row()
        if row >= 0:
            self.window.controller.presets.editor.edit(row)

    # ----------------------------
    # Selection helpers (multi / single)
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

    def _selected_role_ids(self) -> list[str]:
        """Return list of selected ROLE_ID (stable IDs)."""
        try:
            out = []
            for ix in self.selectionModel().selectedRows():
                pid = ix.data(self.ROLE_ID)
                if pid:
                    out.append(pid)
            return out
        except Exception:
            return []

    def _has_multi_selection(self) -> bool:
        """Check whether more than one row is selected."""
        try:
            return len(self.selectionModel().selectedRows()) > 1
        except Exception:
            return False

    # ----------------------------
    # Context menu
    # ----------------------------

    def show_context_menu(self, pos: QPoint):
        """Context menu event"""
        if self._model_updating:
            return

        global_pos = self.viewport().mapToGlobal(pos)
        mode = self.window.core.config.get('mode')
        index = self.indexAt(pos)
        idx = index.row() if index.isValid() else -1

        # Gather selection state
        selected_idx_list = self._selected_indexes()
        selected_ids = [ix.data(self.ROLE_ID) for ix in selected_idx_list if ix.data(self.ROLE_ID)]
        selected_rows = [ix.row() for ix in selected_idx_list]
        multi = len(selected_rows) > 1

        # Allow menu on empty area only when multi-selection is active
        if not index.isValid() and not multi:
            return

        # Resolve clicked item (for single)
        preset = None
        if idx >= 0:
            preset_id = self.window.core.presets.get_by_idx(idx, mode)
            if preset_id:
                preset = self.window.core.presets.items.get(preset_id)

        # Determine special/current flags for single target
        is_current_single = idx >= 0 and self.window.controller.presets.is_current(idx)
        is_special_single = bool(index.data(self.ROLE_IS_SPECIAL)) if index.isValid() else False

        # Build menu
        menu = QMenu(self)

        # Edit (only for single)
        edit_act = QAction(self._ICO_EDIT, trans('preset.action.edit'), menu)
        edit_act.triggered.connect(lambda checked=False, it=index: self.action_edit(it))
        edit_act.setEnabled(idx >= 0 and not multi)
        menu.addAction(edit_act)

        # Enable / Disable (single or multi, expert mode; ignore current.*)
        if mode == MODE_EXPERT:
            if multi:
                items = self.window.core.presets.items
                any_enable = False
                any_disable = False
                for ix in selected_idx_list:
                    pid = ix.data(self.ROLE_ID)
                    if not pid:
                        continue
                    it = items.get(pid)
                    if not it:
                        continue
                    if getattr(it, "filename", "").startswith("current."):
                        continue
                    if getattr(it, "enabled", False):
                        any_disable = True
                    else:
                        any_enable = True
                if any_enable:
                    enable_act = QAction(self._ICO_CHECK, trans('preset.action.enable'), menu)
                    enable_act.triggered.connect(lambda checked=False, ids=list(selected_ids): self.action_enable(ids))
                    menu.addAction(enable_act)
                if any_disable:
                    disable_act = QAction(self._ICO_CLOSE, trans('preset.action.disable'), menu)
                    disable_act.triggered.connect(lambda checked=False, ids=list(selected_ids): self.action_disable(ids))
                    menu.addAction(disable_act)
            else:
                if preset and not getattr(preset, "filename", "").startswith("current."):
                    if not getattr(preset, "enabled", False):
                        enable_act = QAction(self._ICO_CHECK, trans('preset.action.enable'), menu)
                        enable_act.triggered.connect(lambda checked=False, it=index: self.action_enable(it))
                        menu.addAction(enable_act)
                    else:
                        disable_act = QAction(self._ICO_CLOSE, trans('preset.action.disable'), menu)
                        disable_act.triggered.connect(lambda checked=False, it=index: self.action_disable(it))
                        menu.addAction(disable_act)

        # Duplicate (single or multi)
        duplicate_act = QAction(self._ICO_COPY, trans('preset.action.duplicate'), menu)
        if multi:
            duplicate_act.triggered.connect(lambda checked=False, ids=list(selected_ids): self.action_duplicate(ids))
        else:
            duplicate_act.triggered.connect(lambda checked=False, it=index: self.action_duplicate(it))

        # Up/Down only for single, non-current, non-special, and when DnD is on
        if not multi and self._dnd_enabled and not is_current_single and not is_special_single and idx >= 0:
            up_act = QAction(self._ICO_UP, trans('common.up'), menu)
            down_act = QAction(self._ICO_DOWN, trans('common.down'), menu)
            up_act.setEnabled(idx > 1)
            down_act.setEnabled(idx < (self.model().rowCount() - 1))
            up_act.triggered.connect(lambda checked=False, it=index: self.action_move_up(it))
            down_act.triggered.connect(lambda checked=False, it=index: self.action_move_down(it))
            menu.addAction(up_act)
            menu.addAction(down_act)

        # Restore / Delete depending on current / multi
        if not multi and is_current_single:
            edit_act.setEnabled(False)
            restore_act = QAction(self._ICO_UNDO, trans('dialog.editor.btn.defaults'), menu)
            restore_act.triggered.connect(lambda checked=False, it=index: self.action_restore(it))
            menu.addAction(restore_act)
            menu.addAction(duplicate_act)
        else:
            # In multi-selection: disable delete if any current.* or special in selection
            can_delete_all = True
            if multi:
                for ix in selected_idx_list:
                    pid = ix.data(self.ROLE_ID)
                    if not pid:
                        continue
                    if pid.startswith("current.") or bool(ix.data(self.ROLE_IS_SPECIAL)):
                        can_delete_all = False
                        break
            else:
                can_delete_all = idx >= 0 and not is_current_single

            delete_act = QAction(self._ICO_DELETE, trans('preset.action.delete'), menu)
            if multi:
                delete_act.triggered.connect(lambda checked=False, ids=list(selected_ids): self.action_delete(ids))
            else:
                delete_act.triggered.connect(lambda checked=False, it=index: self.action_delete(it))
            delete_act.setEnabled(can_delete_all)

            menu.addAction(duplicate_act)
            menu.addAction(delete_act)

        self.selection = self.selectionModel().selection()
        menu.exec_(global_pos)

        # Restore selection after context menu if needed
        self.store_scroll_position()
        if self.restore_after_ctx_menu:
            if self._backup_selection is not None:
                sel_model = self.selectionModel()
                sel_model.clearSelection()
                for i in self._backup_selection:
                    sel_model.select(
                        i, QItemSelectionModel.Select | QItemSelectionModel.Rows
                    )
                self._backup_selection = None
        self.restore_after_ctx_menu = True
        self.restore_scroll_position()

    # ----------------------------
    # Context actions (single or multi)
    # If 'item' is a QModelIndex -> single row (int will be passed to external code).
    # If 'item' is a list/tuple -> multi; pass list of ROLE_ID strings to external code.
    # ----------------------------

    def action_edit(self, item):
        idx = item.row()
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.presets.editor.edit(idx)

    def action_duplicate(self, item):
        if isinstance(item, (list, tuple)):
            self.restore_after_ctx_menu = False
            self.window.controller.presets.duplicate(list(item))
            return
        idx = item.row()
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.presets.duplicate(idx)

    def action_delete(self, item):
        if isinstance(item, (list, tuple)):
            self.restore_after_ctx_menu = False
            self.window.controller.presets.delete(list(item))
            return
        idx = item.row()
        if idx >= 0:
            self.restore_after_ctx_menu = False
            self.window.controller.presets.delete(idx)

    def action_restore(self, item):
        self.window.controller.presets.restore()

    def action_enable(self, item):
        if isinstance(item, (list, tuple)):
            self.window.controller.presets.enable(list(item))
            return
        idx = item.row()
        if idx >= 0:
            self.window.controller.presets.enable(idx)

    def action_disable(self, item):
        if isinstance(item, (list, tuple)):
            self.window.controller.presets.disable(list(item))
            return
        idx = item.row()
        if idx >= 0:
            self.window.controller.presets.disable(idx)

    def action_move_up(self, item):
        row = item.row()
        if row <= 1:
            return
        self.restore_after_ctx_menu = False
        # Select the moved element (exception rule for context Up)
        moved_role_id = item.data(self.ROLE_ID)
        if moved_role_id:
            self._selection_override_ids = [moved_role_id]
            # Keep controller in sync with the view selection
            self.window.controller.presets.select_by_id(moved_role_id)
        self._move_row(row, row - 1)

    def action_move_down(self, item):
        row = item.row()
        if row < 0 or row >= (self.model().rowCount() - 1):
            return
        if row == 0:
            return
        self.restore_after_ctx_menu = False
        # Select the moved element (exception rule for context Down)
        moved_role_id = item.data(self.ROLE_ID)
        if moved_role_id:
            self._selection_override_ids = [moved_role_id]
            # Keep controller in sync with the view selection
            self.window.controller.presets.select_by_id(moved_role_id)
        self._move_row(row, row + 1)

    # ----------------------------
    # Ordering helpers (core-based)
    # ----------------------------

    def _core_regular_ids_for_mode(self) -> list[str]:
        """Return current ordered preset IDs for mode, excluding pinned current.<mode>."""
        mode = self.window.core.config.get('mode')
        data = self.window.core.presets.get_by_mode(mode) or {}
        ids = list(data.keys())
        if ids and ids[0].startswith("current."):
            ids = ids[1:]
        return ids

    def _core_regular_uuids_for_mode(self) -> list[str]:
        """UUID list resolved from core ordered IDs (excluding pinned)."""
        ids = self._core_regular_ids_for_mode()
        items = self.window.core.presets.items
        out = []
        for pid in ids:
            it = items.get(pid)
            if it and it.uuid:
                out.append(it.uuid)
        return out

    def _collect_regular_uuids(self) -> list[str]:
        """Backward-compatible wrapper used by older code: now returns core-based UUIDs."""
        return self._core_regular_uuids_for_mode()

    def _is_row_selected(self, row: int) -> bool:
        """Check if given row is currently selected."""
        try:
            sel = self.selectionModel().selectedRows()
            return any(ix.row() == row for ix in sel)
        except Exception:
            return False

    def _reorder_and_persist(self, from_row: int, to_row: int) -> str:
        """
        Compute new UUID order using core order (not the view), then persist it.
        Returns moved preset ID (filename) for later selection if needed.
        """
        if from_row <= 0 or to_row <= 0:
            return ""

        ids_seq = self._core_regular_ids_for_mode()
        if not ids_seq:
            return ""

        i_from = from_row - 1
        i_to = to_row - 1
        if i_from < 0 or i_from >= len(ids_seq):
            return ""
        if i_to < 0:
            i_to = 0
        if i_to > len(ids_seq):
            i_to = len(ids_seq)

        moved_id = ids_seq[i_from]
        seq_ids = list(ids_seq)
        item = seq_ids.pop(i_from)
        seq_ids.insert(i_to if i_to <= len(seq_ids) else len(seq_ids), item)

        items = self.window.core.presets.items
        uuids = [items[pid].uuid for pid in seq_ids if pid in items and items[pid].uuid]
        mode = self.window.core.config.get('mode')
        self.window.controller.presets.persist_order_for_mode(mode, uuids)

        return moved_id

    # ----------------------------
    # Drag visuals (safe, no delegate painting)
    # ----------------------------

    def _drag_pixmap_for_index(self, index) -> QPixmap | None:
        """
        Build a safe pixmap for dragged row without using delegate.paint (prevents crash).
        """
        try:
            text = str(index.data(Qt.DisplayRole) or "")
            fm = self.fontMetrics()
            w = max(fm.horizontalAdvance(text) + 24, 80)
            h = max(fm.height() + 10, 24)
            pm = QPixmap(w, h)
            pm.fill(Qt.transparent)

            painter = QPainter()
            painter.begin(pm)
            try:
                # background bubble
                bg = self.palette().base().color()
                bg.setAlpha(220)
                painter.fillRect(pm.rect(), bg)
                # border
                pen = QPen(QColor(0, 0, 0, 40))
                painter.setPen(pen)
                painter.drawRect(pm.rect().adjusted(0, 0, -1, -1))
                # text
                painter.setPen(self.palette().text().color())
                painter.drawText(pm.rect().adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, text)
            finally:
                painter.end()
            return pm
        except Exception:
            return None

    def startDrag(self, supportedActions):
        """
        Start drag with pixmap built from the actually dragged row (self._press_index).
        Avoids using selection for drag visuals (no 'ghost' of another item).
        """
        if not self._dnd_enabled or self._press_index is None or not self._press_index.isValid():
            return super().startDrag(supportedActions)

        model = self.model()
        drag = QDrag(self)
        # mime data from the pressed index (not from selection)
        try:
            mime = model.mimeData([self._press_index])
        except Exception:
            mime = QMimeData()
        drag.setMimeData(mime)

        pm = self._drag_pixmap_for_index(self._press_index)
        if pm is not None:
            drag.setPixmap(pm)
            drag.setHotSpot(pm.rect().center())

        drag.exec(Qt.MoveAction)

    # ----------------------------
    # Refresh & painting
    # ----------------------------

    def _force_full_repaint(self):
        """
        Force a synchronous full repaint of the viewport and notify the view that data/layout could change.
        This clears any stale drag visuals on some platforms/styles.
        """
        model = self.model()
        if model is not None and model.rowCount() > 0:
            top = model.index(0, 0)
            bottom = model.index(model.rowCount() - 1, 0)
            try:
                model.dataChanged.emit(top, bottom, [Qt.DisplayRole])
            except Exception:
                pass
            try:
                model.layoutChanged.emit()
            except Exception:
                pass
        self.viewport().repaint()

    def _refresh_after_order_change(self, moved_id: str, follow_selection: bool):
        """
        Refresh the list from core order and keep selection/scroll stable.

        For both DnD and context moves:
        - if _selection_override_ids is set, layout will restore those IDs;
        - otherwise, take current selected IDs and use them as override to ensure
          selection 'follows element, not position'.
        """
        if not self._selection_override_ids:
            self._selection_override_ids = self._current_selected_ids()

        self.store_scroll_position()

        # Use custom indicator only; do not re-enable native one here
        self.setUpdatesEnabled(False)
        try:
            self.window.controller.presets.update_list()
            self.restore_scroll_position()
        finally:
            self.setUpdatesEnabled(True)

        # Clear helpers for context menu (layout will consume _selection_override_ids)
        self._ctx_menu_original_ids = None
        self._backup_selection = None

        QApplication.processEvents(QEventLoop.ExcludeUserInputEvents | QEventLoop.ExcludeSocketNotifiers)
        self._force_full_repaint()
        QTimer.singleShot(0, self.viewport().update)

    def _apply_after_drop(self):
        """Execute deferred refresh after the drop event has fully finished in Qt."""
        payload = self._pending_after_drop
        self._pending_after_drop = None
        if not payload:
            return
        moved_id, follow_selection = payload
        self._refresh_after_order_change(moved_id, follow_selection)
        # Activate moved preset in controller at the very end (deferred to avoid re-entrancy)
        QTimer.singleShot(0, lambda mid=moved_id: self._finalize_select_after_drop(mid))

    def _finalize_select_after_drop(self, moved_role_id: str):
        """
        Final activation of the moved preset in controller after DnD completed and view got refreshed.
        This is intentionally deferred to the next event loop tick.
        """
        try:
            pid = moved_role_id
            if not pid:
                ids = self._current_selected_ids()
                pid = ids[0] if ids else ""
            if pid:
                self.window.controller.presets.select_by_id(pid)
        except Exception:
            pass

    def _move_row(self, from_row: int, to_row: int):
        """Move row programmatically; persist order and keep selection attached to the same item."""
        if from_row == to_row:
            return
        moved_id = self._reorder_and_persist(from_row, to_row)
        self._refresh_after_order_change(moved_id, follow_selection=False)

    # --- Custom drop indicator helpers ---

    def _compute_drop_locations(self, pos: QPoint) -> tuple[int, int]:
        """
        Compute both:
        - to_row_drop: final insertion row used for reordering (after 'moving-down' adjustment),
        - seam_row: row under which the visual indicator line should be drawn
                    in the current (pre-drop) view geometry.

        This keeps visuals and the final insertion point perfectly aligned.

        Returns: (to_row_drop, seam_row)
        """
        model = self.model()
        if model is None:
            return -1, -1

        idx = self.indexAt(pos)

        beyond_last = False
        if not idx.isValid():
            to_row_raw = model.rowCount()  # append at the end
            if model.rowCount() > 0:
                last_idx = model.index(model.rowCount() - 1, 0)
                last_rect = self.visualRect(last_idx)
                if last_rect.isValid() and pos.y() > last_rect.bottom():
                    beyond_last = True
        else:
            rect = self.visualRect(idx)
            to_row_raw = idx.row() + (1 if pos.y() > rect.center().y() else 0)

        # Keep first row pinned (cannot insert above row 1)
        if to_row_raw <= 1:
            to_row_raw = 1

        # seam row is always the boundary under the row at (to_row_raw - 1),
        # except in explicit "beyond last" zone where we draw under the last row.
        if model.rowCount() > 0:
            if beyond_last:
                seam_row = model.rowCount() - 1
            else:
                seam_row = max(0, min(model.rowCount() - 1, to_row_raw - 1))
        else:
            seam_row = -1

        # Apply 'moving down' adjustment only to the logical insertion row,
        # never to the visual seam (otherwise the line jumps one row up).
        from_row = self._press_index.row() if (self._press_index and self._press_index.isValid()) else -1
        to_row_drop = to_row_raw
        if from_row >= 0 and to_row_raw > from_row and not beyond_last:
            to_row_drop -= 1

        # Clamp to valid ranges
        to_row_drop = max(1, min(model.rowCount(), to_row_drop))
        if seam_row >= 0:
            seam_row = max(0, min(model.rowCount() - 1, seam_row))

        return to_row_drop, seam_row

    def _update_drop_indicator_from_pos(self, pos: QPoint):
        """
        Update custom drop indicator state based on cursor position.
        Draws a single horizontal line under the row where the item will land.
        """
        if not self._dnd_enabled or self._model_updating:
            self._clear_drop_indicator()
            return

        model = self.model()
        if model is None or model.rowCount() <= 0:
            self._clear_drop_indicator()
            return

        _, seam_row = self._compute_drop_locations(pos)
        if seam_row < 0:
            self._clear_drop_indicator()
            return

        if not self._drop_indicator_active or self._drop_indicator_to_row != seam_row:
            self._drop_indicator_active = True
            self._drop_indicator_to_row = seam_row
            self.viewport().update()

    def _clear_drop_indicator(self):
        """Hide custom drop indicator."""
        if self._drop_indicator_active or self._drop_indicator_to_row != -1:
            self._drop_indicator_active = False
            self._drop_indicator_to_row = -1
            if self.viewport():
                self.viewport().update()

    def paintEvent(self, event):
        """
        Standard paint + overlay a clear drop indicator line at the computed insertion position.
        """
        super().paintEvent(event)

        if not self._drop_indicator_active or not self._dnd_enabled:
            return

        model = self.model()
        if model is None or model.rowCount() <= 0:
            return

        seam_row = self._drop_indicator_to_row
        if seam_row < 0 or seam_row >= model.rowCount():
            return

        idx = model.index(seam_row, 0)
        rect = self.visualRect(idx)
        if not rect.isValid() or rect.height() <= 0:
            return

        # Line under the seam row
        y = rect.bottom()
        x1 = self._drop_indicator_padding
        x2 = self.viewport().width() - self._drop_indicator_padding

        painter = QPainter(self.viewport())
        try:
            # Use highlight color with good contrast; 1px thickness
            color = self.palette().highlight().color()
            color.setAlpha(220)
            pen = QPen(color, 1)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.drawLine(x1, y, x2, y)
        finally:
            painter.end()

    # ----------------------------
    # Mouse / DnD events
    # ----------------------------

    def _mouse_event_point(self, event):
        if hasattr(event, "position"):
            try:
                p = event.position()
                if hasattr(p, "toPoint"):
                    return p.toPoint()
            except Exception:
                pass
        if hasattr(event, "pos"):
            return event.pos()
        return self.viewport().mapFromGlobal(QCursor.pos())

    def mousePressEvent(self, event):
        if self._model_updating:
            event.ignore()
            return

        # Ctrl+Left: virtual toggle without business click
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier):
            idx = self.indexAt(self._mouse_event_point(event))
            if idx.isValid():
                self._ctrl_multi_active = True
                self._ctrl_multi_index = idx
                self._suppress_item_click = True
                event.accept()
                return
            self._suppress_item_click = True
            event.accept()
            return

        # Shift+Left: let Qt perform range selection (anchor -> clicked), suppress business click
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier):
            idx = self.indexAt(self._mouse_event_point(event))
            if idx.isValid():
                self._suppress_item_click = True
                self._was_shift_click = True
                super().mousePressEvent(event)  # default range selection
                return
            # Shift on empty area -> ignore silently
            self._suppress_item_click = True
            self._was_shift_click = True
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            index = self.indexAt(self._mouse_event_point(event))
            # When multiple are selected, a single plain click clears the multi-selection
            if self._has_multi_selection():
                sel_model = self.selectionModel()
                sel_model.clearSelection()
                if not index.isValid():
                    event.accept()
                    return
                # continue with default single selection for clicked row

            # Freeze scroll for a moment to prevent jumps caused by selection-triggered refresh
            if index.isValid():
                self._freeze_scroll(250)
            if self._dnd_enabled:
                sel_model = self.selectionModel()
                self._press_backup_selection = list(sel_model.selectedIndexes())
                self._press_backup_current = self.currentIndex()
                self._dragged_was_selected = any(ix.row() == index.row() for ix in self._press_backup_selection or [])
                super().mousePressEvent(event)
                # Keep old selection (do not auto-select dragged item yet)
                sel_model.clearSelection()
                for i in self._press_backup_selection or []:
                    sel_model.select(i, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                if self._press_backup_current and self._press_backup_current.isValid():
                    self.setCurrentIndex(self._press_backup_current)
                self._press_pos = self._mouse_event_point(event)
                self._press_index = index
                self._drag_selection_applied = False
                event.accept()
                return
            else:
                super().mousePressEvent(event)

        elif event.button() == Qt.RightButton:
            index = self.indexAt(self._mouse_event_point(event))
            sel_model = self.selectionModel()
            selected_rows = [ix.row() for ix in sel_model.selectedRows()]
            multi = len(selected_rows) > 1

            # Save original IDs only if we are going to change selection
            if index.isValid():
                if multi and index.row() in selected_rows:
                    # Keep existing multi-selection; do not alter selection on right click
                    self._backup_selection = None
                    self._ctx_menu_original_ids = [ix.data(self.ROLE_ID) for ix in sel_model.selectedRows() if ix.data(self.ROLE_ID)]
                else:
                    # Right-click outside current selection (or not multi) -> select the clicked row temporarily
                    self._ctx_menu_original_ids = []
                    for ix in sel_model.selectedRows():
                        pid = ix.data(self.ROLE_ID)
                        if pid:
                            self._ctx_menu_original_ids.append(pid)
                    self._backup_selection = list(sel_model.selectedIndexes())
                    sel_model.clearSelection()
                    sel_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._model_updating:
            return
        if not self._dnd_enabled:
            return super().mouseMoveEvent(event)
        if self._press_index is None or self._press_pos is None:
            return super().mouseMoveEvent(event)
        if not (event.buttons() & Qt.LeftButton):
            return super().mouseMoveEvent(event)

        cur = self._mouse_event_point(event)
        dist = (cur - self._press_pos).manhattanLength()
        threshold = QApplication.startDragDistance()
        if dist < threshold:
            return

        # Pin current.* at the top; prevent dragging it
        if self._press_index.row() == 0 or bool(self._press_index.data(self.ROLE_IS_SPECIAL)):
            return super().mouseMoveEvent(event)

        # Exception rule: at the start of drag, select the dragged item (view-only to avoid re-entrancy)
        if not self._drag_selection_applied:
            try:
                sel_model = self.selectionModel()
                prev_unlocked = self.unlocked
                self.unlocked = True
                try:
                    sel_model.clearSelection()
                    sel_model.select(self._press_index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
                    self.setCurrentIndex(self._press_index)
                finally:
                    self.unlocked = prev_unlocked
            except Exception:
                pass
            self._drag_selection_applied = True

        self._dragging = True
        self.setCursor(QCursor(Qt.ClosedHandCursor))
        # Let base class proceed; it will trigger startDrag when needed.
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._model_updating:
            event.ignore()
            return

        # If the click was a Shift-based range selection, bypass single-select synchronization
        if event.button() == Qt.LeftButton and self._was_shift_click:
            self._was_shift_click = False
            # Let Qt finish its own release processing; do not run our single-select logic
            super().mouseReleaseEvent(event)
            return

        # Finish "virtual" Ctrl toggle on same row
        if event.button() == Qt.LeftButton and self._ctrl_multi_active:
            try:
                idx = self.indexAt(self._mouse_event_point(event))
                if idx.isValid() and self._ctrl_multi_index and idx == self._ctrl_multi_index:
                    sel_model = self.selectionModel()
                    sel_model.select(idx, QItemSelectionModel.Toggle | QItemSelectionModel.Rows)
            finally:
                self._ctrl_multi_active = False
                self._ctrl_multi_index = None
                # do not emit business click after Ctrl path
                self._press_pos = None
                self._press_index = None
                self._press_backup_selection = None
                self._press_backup_current = None
                self._dragging = False
                self._dragged_was_selected = False
                self._drag_selection_applied = False
            event.accept()
            return

        try:
            if self._dnd_enabled and event.button() == Qt.LeftButton:
                self.unsetCursor()
                self._clear_drop_indicator()
                if not self._dragging:
                    idx = self.indexAt(self._mouse_event_point(event))
                    if idx.isValid():
                        # Skip business selection if multi-selection is active (e.g., after Shift)
                        if self._has_multi_selection():
                            pass
                        else:
                            pid = idx.data(self.ROLE_ID)
                            if pid:
                                # Keep scroll stable also for this late selection path
                                self._freeze_scroll(300)
                                self._pending_refocus_role_id = pid
                                self.window.controller.presets.select_by_id(pid)
                                QTimer.singleShot(0, self._apply_pending_refocus)
                                QTimer.singleShot(50, self._apply_pending_refocus)
                            else:
                                self.setCurrentIndex(idx)
                                self.window.controller.presets.select(idx.row())
        finally:
            self._press_pos = None
            self._press_index = None
            self._press_backup_selection = None
            self._press_backup_current = None
            self._dragging = False
            self._dragged_was_selected = False
            self._drag_selection_applied = False
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if self._model_updating:
            event.ignore()
            return
        if not self._dnd_enabled:
            return
        event.setDropAction(Qt.MoveAction)
        event.acceptProposedAction()
        super().dragEnterEvent(event)
        # Show indicator immediately on enter
        self._update_drop_indicator_from_pos(self._mouse_event_point(event))

    def dragLeaveEvent(self, event):
        if self._model_updating:
            event.ignore()
            return
        self.unsetCursor()
        self._clear_drop_indicator()
        super().dragLeaveEvent(event)

    def dragMoveEvent(self, event):
        if self._model_updating:
            event.ignore()
            return
        if not self._dnd_enabled:
            return

        pos = self._mouse_event_point(event)
        idx = self.indexAt(pos)
        # Do not allow dropping into the pinned first row zone
        if idx.isValid() and idx.row() == 0:
            rect = self.visualRect(idx)
            if pos.y() <= rect.center().y():
                self._clear_drop_indicator()
                event.ignore()
                return

        # Let base class process autoscroll and internal geometry first
        event.setDropAction(Qt.MoveAction)
        event.acceptProposedAction()
        super().dragMoveEvent(event)

        # Update custom indicator based on current cursor and updated viewport
        self._update_drop_indicator_from_pos(pos)

    def dropEvent(self, event):
        """
        Fully handle flat row-to-row move. Persist order and defer view rebuild to next event loop,
        so Qt can finish DnD teardown (prevents temporary disappearance).
        """
        if self._model_updating:
            event.ignore()
            return
        if not self._dnd_enabled:
            return super().dropEvent(event)

        model = self.model()
        if model is None:
            event.ignore()
            return

        # Source row (from press index if available)
        if self._press_index is not None and self._press_index.isValid():
            from_row = self._press_index.row()
        else:
            cur = self.currentIndex()
            from_row = cur.row() if cur.isValid() else -1

        if from_row < 0:
            event.ignore()
            self.unsetCursor()
            self._drag_selection_applied = False
            self._clear_drop_indicator()
            return

        # Target row computed exactly the same way as the indicator (but with 'moving down' adjustment)
        to_row, _ = self._compute_drop_locations(self._mouse_event_point(event))

        moved_id = self._reorder_and_persist(from_row, to_row)

        # Defer the heavy refresh to the next event loop tick
        self._pending_after_drop = (moved_id, False)
        QTimer.singleShot(0, self._apply_after_drop)

        # Properly finalize DnD in Qt and exit without mutating the model here
        event.setDropAction(Qt.MoveAction)
        event.acceptProposedAction()
        self.unsetCursor()
        self._drag_selection_applied = False
        self._clear_drop_indicator()

    # ----------------------------
    # Legacy helper (not used in new path)
    # ----------------------------

    def _persist_current_model_order(self):
        """Deprecated in favor of _reorder_and_persist; retained for backward compatibility if needed."""
        model = self.model()
        if model is None:
            return
        uuids = []
        for i in range(model.rowCount()):
            if i == 0:
                continue
            idx = model.index(i, 0)
            u = idx.data(self.ROLE_UUID)
            if u and isinstance(u, str):
                uuids.append(u)
        mode = self.window.core.config.get('mode')
        self.window.controller.presets.persist_order_for_mode(mode, uuids)

    def selectionCommand(self, index, event=None):
        """
        Selection command
        :param index: Index
        :param event: Event
        """
        # Prevent selection changes while model is updating (guards against stale indexes)
        if self._model_updating:
            return QItemSelectionModel.NoUpdate
        return super().selectionCommand(index, event)