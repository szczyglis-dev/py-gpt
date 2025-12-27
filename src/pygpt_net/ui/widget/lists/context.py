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

import datetime
import functools
from typing import Union

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, QPoint, QItemSelectionModel, QPersistentModelIndex
from PySide6.QtGui import QIcon, QColor, QPixmap, QStandardItem
from PySide6.QtWidgets import QMenu, QAbstractItemView

from .base import BaseList
from pygpt_net.utils import trans


class ContextList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Context select menu

        :param window: main window
        :param id: input id
        """
        super(ContextList, self).__init__(window)
        self.window = window
        self.id = id
        self.expanded_items = set()
        self._icons = {
            'add': QIcon(":/icons/add.svg"),
            'edit': QIcon(":/icons/edit.svg"),
            'delete': QIcon(":/icons/delete.svg"),
            'chat': QIcon(":/icons/chat.svg"),
            'copy': QIcon(":/icons/copy.svg"),
            'close': QIcon(":/icons/close.svg"),
            'pin': QIcon(":/icons/pin3.svg"),
            'clock': QIcon(":/icons/clock.svg"),
            'db': QIcon(":/icons/db.svg"),
            'folder': QIcon(":/icons/folder_filled.svg"),
            'attachment': QIcon(":/icons/attachment.svg"),
        }
        self._color_icon_cache = {}

        # Multi-select configuration and guards
        # - ExtendedSelection enables Ctrl/Shift based multi-selection
        # - _suppress_item_click prevents "business click" side-effects during virtual multi-select
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._suppress_item_click = False

        # Track last selection target type to keep selection homogeneous (groups vs items)
        self._last_selection_target_is_group = None

        # Force-next-click activation when we collapse multi-selection with a plain click
        self._force_single_click_index: QPersistentModelIndex | None = None

        # Use a custom delegate for labels/pinned/attachment indicators and group border indicator
        # Pass both: attachment icon and pin icon (pin2.svg) for pinned indicator rendering
        self.setItemDelegate(ImportantItemDelegate(self, self._icons['attachment'], self._icons['pin']))

        # Ensure context menu works as before
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self._backup_selection = None
        self.restore_after_ctx_menu = True

        # Make group rows visually stick to the left edge (if this is a tree view).
        # Children remain indented by delegate's manual shift (+15 px), preserving structure.
        try:
            if hasattr(self, 'setIndentation'):
                # Set tree indentation to 0 so group/folder rows do not look like children
                self.setIndentation(0)
        except Exception:
            # Safe no-op if the underlying view does not support setIndentation
            pass

        self._loading_more = False  # guard to avoid multiple triggers while updating
        try:
            self.verticalScrollBar().valueChanged.connect(self._on_vertical_scroll)
        except Exception:
            pass  # safe no-op if view doesn't expose verticalScrollBar

        # Keep selection homogeneous using selectionChanged pruning as a safety net
        try:
            self.selectionModel().selectionChanged.connect(self._on_selection_changed)
        except Exception:
            # Will be connected by the framework once model/selection model is available
            pass

        # Scroll preservation guards for destructive model changes (like delete/move)
        # They ensure the view does not jump after removing rows and anchor to RMB target when used.
        self._scroll_guard_active = False
        self._deletion_initiated = False
        self._pre_update_scroll_value = 0
        self._connected_model = None
        self._model_signals_connected = False
        self._context_menu_anchor_index: QPersistentModelIndex | None = None
        self._context_menu_anchor_scroll_value: int | None = None
        self._connect_model_signals_safely()

    def _on_vertical_scroll(self, value: int):
        """
        Trigger infinite scroll: when scrollbar reaches bottom, request the next page.
        """
        try:
            sb = self.verticalScrollBar()
        except Exception:
            return
        if sb.maximum() <= 0:
            return  # nothing to scroll
        # Close-to-bottom detection; keep a tiny threshold for stability
        if not self._loading_more and value >= sb.maximum():
            self._loading_more = True
            # Ask controller to increase the total limit and refresh the list
            self.window.controller.ctx.load_more()
            # Release the guard shortly after model updates
            QtCore.QTimer.singleShot(250, lambda: setattr(self, "_loading_more", False))

    def _connect_model_signals_safely(self):
        """
        Connect model change signals once and keep track of the connected instance.
        """
        try:
            model = self._model if self._model is not None else self.model()
        except Exception:
            model = self.model()

        if model is None:
            return

        if self._connected_model is model and self._model_signals_connected:
            return

        # Disconnect from previous model if needed
        if self._connected_model is not None and self._connected_model is not model:
            try:
                self._connected_model.rowsAboutToBeRemoved.disconnect(self._on_rows_about_to_be_removed)
            except Exception:
                pass
            try:
                self._connected_model.rowsRemoved.disconnect(self._on_rows_removed)
            except Exception:
                pass
            try:
                self._connected_model.modelAboutToBeReset.disconnect(self._on_model_about_to_be_reset)
            except Exception:
                pass
            try:
                self._connected_model.modelReset.disconnect(self._on_model_reset)
            except Exception:
                pass
            try:
                self._connected_model.layoutAboutToBeChanged.disconnect(self._on_layout_about_to_change)
            except Exception:
                pass
            try:
                self._connected_model.layoutChanged.disconnect(self._on_layout_changed)
            except Exception:
                pass

        # Connect to current model
        try:
            model.rowsAboutToBeRemoved.connect(self._on_rows_about_to_be_removed)
        except Exception:
            pass
        try:
            model.rowsRemoved.connect(self._on_rows_removed)
        except Exception:
            pass
        try:
            model.modelAboutToBeReset.connect(self._on_model_about_to_be_reset)
        except Exception:
            pass
        try:
            model.modelReset.connect(self._on_model_reset)
        except Exception:
            pass
        try:
            model.layoutAboutToBeChanged.connect(self._on_layout_about_to_change)
        except Exception:
            pass
        try:
            model.layoutChanged.connect(self._on_layout_changed)
        except Exception:
            pass

        self._connected_model = model
        self._model_signals_connected = True

    def setModel(self, model):
        """
        Ensure model signals are (re)connected whenever the view's model is replaced.
        """
        super().setModel(model)
        self._connect_model_signals_safely()

    def _activate_scroll_guard(self, reason: str = "", override_value: int | None = None):
        """
        Capture current (or overridden) scroll position to restore it after a destructive update.
        If override_value is provided, it will be used as the anchor scroll position.
        """
        if self._scroll_guard_active:
            if override_value is not None:
                try:
                    self._pre_update_scroll_value = int(override_value)
                    self.set_pending_v_scroll(self._pre_update_scroll_value)
                except Exception:
                    pass
            return
        try:
            sb = self.verticalScrollBar()
            if sb is None:
                return
            val = int(override_value) if override_value is not None else sb.value()
            self._pre_update_scroll_value = val
            self.set_pending_v_scroll(val)
            self._scroll_guard_active = True
        except Exception:
            self._scroll_guard_active = True
            self._pre_update_scroll_value = 0

    def _schedule_scroll_restore(self):
        """
        Restore captured scroll position after the model/layout change settles.
        A short cascade of timers is used to win potential late scrollTo() calls.
        """
        if not self._scroll_guard_active:
            return

        def apply():
            try:
                sb = self.verticalScrollBar()
                if sb is None:
                    return
                target = min(self._pre_update_scroll_value, sb.maximum())
                sb.setValue(target)
            except Exception:
                pass

        # Apply several times to outlast any post-update scrolls triggered by selection changes
        QtCore.QTimer.singleShot(0, apply)
        QtCore.QTimer.singleShot(25, apply)
        QtCore.QTimer.singleShot(75, apply)
        QtCore.QTimer.singleShot(150, apply)
        QtCore.QTimer.singleShot(300, apply)
        QtCore.QTimer.singleShot(600, apply)
        QtCore.QTimer.singleShot(750, self._clear_scroll_guard)

    def _clear_scroll_guard(self):
        """
        Clear guard flags after restoration completed.
        """
        self._scroll_guard_active = False
        self._deletion_initiated = False
        self._context_menu_anchor_index = None
        self._context_menu_anchor_scroll_value = None
        # Clear BaseList pending values if any were set
        try:
            self.clear_pending_scroll()
        except Exception:
            pass

    # Model signal handlers

    def _on_rows_about_to_be_removed(self, parent, start, end):
        """
        Rows are going to be removed; capture current scroll to preserve viewport.
        Prefer context menu anchor value if present.
        """
        anchor_val = self._context_menu_anchor_scroll_value
        self._activate_scroll_guard("rowsAboutToBeRemoved", anchor_val)

    def _on_rows_removed(self, parent, start, end):
        """
        Rows removed; schedule scroll restoration.
        """
        if self._scroll_guard_active or self._deletion_initiated:
            self._schedule_scroll_restore()

    def _on_model_about_to_be_reset(self):
        """
        Model reset incoming. If it follows a delete operation, capture scroll now.
        """
        if self._deletion_initiated or self._scroll_guard_active:
            anchor_val = self._context_menu_anchor_scroll_value
            self._activate_scroll_guard("modelAboutToBeReset", anchor_val)

    def _on_model_reset(self):
        """
        Model has been reset; restore scroll if we armed the guard.
        """
        if self._scroll_guard_active or self._deletion_initiated:
            self._schedule_scroll_restore()

    def _on_layout_about_to_change(self):
        """
        Layout change incoming; if it is a consequence of delete, capture scroll.
        """
        if self._deletion_initiated:
            anchor_val = self._context_menu_anchor_scroll_value
            self._activate_scroll_guard("layoutAboutToBeChanged", anchor_val)

    def _on_layout_changed(self):
        """
        Layout changed; restore scroll if guard is active.
        """
        if self._scroll_guard_active or self._deletion_initiated:
            self._schedule_scroll_restore()

    def scrollTo(self, index, hint=QAbstractItemView.EnsureVisible):
        """
        Block automatic scrolling requests while scroll guard is active
        (e.g., selection changes executed by controller after delete).
        """
        if self._scroll_guard_active or self._deletion_initiated:
            return
        super().scrollTo(index, hint)

    @property
    def _model(self):
        return self.window.ui.models['ctx.list']

    @property
    def _view(self):
        return self.window.ui.nodes['ctx.list']

    def _color_icon(self, color: QColor) -> QIcon:
        """
        Returns (and caches) a solid color icon pixmap for menu items.
        """
        key = color.rgba()
        icon = self._color_icon_cache.get(key)
        if icon is None:
            pixmap = QPixmap(16, 16)
            pixmap.fill(color)
            icon = QIcon(pixmap)
            self._color_icon_cache[key] = icon
        return icon

    def _selected_rows(self):
        """
        Returns selected row indexes (first column only).
        """
        sel = self.selectionModel()
        if not sel:
            return []
        try:
            return [idx for idx in sel.selectedRows(0) if idx.isValid()]
        except TypeError:
            # Fallback if PySide6 binding lacks column overload
            unique = set(i.row() for i in sel.selectedIndexes())
            return [self._model.index(r, 0) for r in unique]

    def _selected_item_ids(self) -> list:
        """
        Returns IDs of selected non-group, non-section items.
        """
        ids = []
        for idx in self._selected_rows():
            item = self._model.itemFromIndex(idx)
            if isinstance(item, Item):
                if hasattr(item, "id"):
                    ids.append(int(item.id))
        return ids

    def _selected_group_ids(self) -> list:
        """
        Returns IDs of selected groups.
        """
        ids = []
        for idx in self._selected_rows():
            item = self._model.itemFromIndex(idx)
            if isinstance(item, GroupItem):
                if hasattr(item, "id"):
                    ids.append(int(item.id))
        return ids

    def _selection_types(self) -> set:
        """
        Returns a set describing current selection types: {'group'} | {'item'} | {'group','item'} | set()
        """
        types = set()
        for idx in self._selected_rows():
            item = self._model.itemFromIndex(idx)
            if isinstance(item, GroupItem):
                types.add('group')
            elif isinstance(item, Item):
                types.add('item')
        return types

    def _has_multi_selection(self) -> bool:
        """
        Returns True if more than one selectable (group or item) row is selected.
        """
        count = 0
        for idx in self._selected_rows():
            it = self._model.itemFromIndex(idx)
            if isinstance(it, (GroupItem, Item)):
                count += 1
                if count > 1:
                    return True
        return False

    def _is_group_index(self, index: QtCore.QModelIndex) -> bool:
        """
        Returns True if the index points to a group/folder item.
        """
        it = self._model.itemFromIndex(index)
        return bool(isinstance(it, GroupItem))

    def _can_toggle_with_ctrl(self, index: QtCore.QModelIndex) -> bool:
        """
        Returns True if Ctrl-toggle on the given index would not mix selection types.
        """
        if not index.isValid():
            return False
        target_is_group = self._is_group_index(index)
        types = self._selection_types()
        if not types:
            return True
        if types == {'group'} and target_is_group:
            return True
        if types == {'item'} and not target_is_group:
            return True
        return False

    def _prune_selection_to_type(self, want_groups: bool):
        """
        Deselects all rows that do not match desired type.
        """
        sel = self.selectionModel()
        if not sel:
            return
        for idx in self._selected_rows():
            if self._is_group_index(idx) != want_groups:
                sel.select(idx, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)

    def _on_selection_changed(self, selected, deselected):
        """
        Keep selection homogeneous by removing indices of the opposite type.
        """
        types = self._selection_types()
        if len(types) <= 1:
            return
        # Decide desired type: prefer the last selection target if known, else majority
        if self._last_selection_target_is_group is not None:
            want_groups = bool(self._last_selection_target_is_group)
        else:
            # Majority fallback
            g = len(self._selected_group_ids())
            i = len(self._selected_item_ids())
            want_groups = g >= i
        self._prune_selection_to_type(want_groups)

    def _perform_item_activation(self, index: QtCore.QModelIndex):
        """
        Execute business action for a single click on the given index.
        """
        item = self._model.itemFromIndex(index)
        if item is None or not hasattr(item, 'isFolder'):
            return
        if item.isFolder:
            self.window.controller.ctx.set_group(item.id)
            if self._view.isExpanded(index):
                self.expanded_items.discard(item.id)
                self._view.collapse(index)
            else:
                self.expanded_items.add(item.id)
                self._view.expand(index)
        else:
            self.window.controller.ctx.select_by_id(item.id)

    def click(self, index):
        """
        Click event (override, connected in BaseList class)

        :param index: index
        """
        # If we armed a "force-single" activation, bypass stale multi-state and suppression once
        if self._force_single_click_index is not None:
            try:
                if index == self._force_single_click_index:
                    self._force_single_click_index = None
                    self._suppress_item_click = False
                    self._perform_item_activation(index)
                    return
            finally:
                # Always clear the one-shot guard
                self._force_single_click_index = None

        # Prevent side-effects (like open/toggle) during virtual multi-select or guarded clicks
        if self._suppress_item_click:
            self._suppress_item_click = False
            return
        # Ignore click side-effects if multiple rows (items or groups) are currently selected
        if self._has_multi_selection():
            return

        self._perform_item_activation(index)

    def expand_group(self, id):
        """
        Expand group

        :param id: group id
        """
        for i in range(self._model.rowCount()):
            item = self._model.item(i)
            if isinstance(item, GroupItem) and item.id == id:
                index = self._model.indexFromItem(item)
                self._view.expand(index)
                self.expanded_items.add(id)
                break

    def dblclick(self, index):
        """
        Double click event

        :param index: index
        """
        print("dblclick")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            no_mod = (event.modifiers() == Qt.NoModifier)
            had_multi = self._has_multi_selection()

            # Clear any stale suppression when user performs a plain left click
            if no_mod:
                self._suppress_item_click = False

            # When multiple selection is active and a plain left click occurs:
            # - clicking empty area clears the selection and consumes the click,
            # - clicking a row clears previous multi-selection and immediately arms one-shot activation.
            if had_multi and no_mod:
                sel = self.selectionModel()
                if sel:
                    sel.clearSelection()
                self.setCurrentIndex(QtCore.QModelIndex())
                try:
                    self.window.controller.ctx.unselect()
                except Exception:
                    pass
                if not index.isValid():
                    event.accept()
                    return
                # Arm one-shot activation for the row under cursor; Qt will select it afterwards
                self._force_single_click_index = QPersistentModelIndex(index)

            # Remember the target type for homogeneous selection control
            if index.isValid():
                self._last_selection_target_is_group = self._is_group_index(index)
            else:
                self._last_selection_target_is_group = None

            # Ctrl-based virtual toggle: do not trigger "click" side effects; allow for groups and items
            if event.modifiers() & Qt.ControlModifier:
                if index.isValid():
                    if not self._can_toggle_with_ctrl(index):
                        # Normalize current selection to the target type so groups/items can be Ctrl-selected immediately
                        self._prune_selection_to_type(self._is_group_index(index))
                    sel = self.selectionModel()
                    if sel:
                        sel.select(index, QItemSelectionModel.Toggle | QItemSelectionModel.Rows)
                    self._suppress_item_click = True
                    self.viewport().update()
                event.accept()
                return

            # Shift-based range select: allow default range behavior, but suppress side-effects and prune type
            if event.modifiers() & Qt.ShiftModifier:
                self._suppress_item_click = True
                super().mousePressEvent(event)
                # Prune to the anchor type to prevent mixed selection
                if index.isValid():
                    self._prune_selection_to_type(self._is_group_index(index))
                return

            # Plain left click
            if not index.isValid():
                try:
                    self.window.controller.ctx.unselect()
                except Exception:
                    pass
            # Make sure next real click is not suppressed
                self._suppress_item_click = False
                event.accept()
                return

            super().mousePressEvent(event)

        elif event.button() == Qt.RightButton:
            index = self.indexAt(event.pos())
            # Anchor scroll to the row under the RMB, regardless of current selection elsewhere
            if index.isValid():
                self._context_menu_anchor_index = QPersistentModelIndex(index)
                try:
                    self._context_menu_anchor_scroll_value = self.verticalScrollBar().value()
                except Exception:
                    self._context_menu_anchor_scroll_value = None

            sel = self.selectionModel()
            if not sel:
                event.accept()
                return
            multi_items = len(self._selected_item_ids()) > 1
            multi_groups = len(self._selected_group_ids()) > 1
            # Keep current multi-selection if right-click happens on one of the selected rows
            if index.isValid() and sel.isSelected(index) and (multi_items or multi_groups):
                self._backup_selection = list(sel.selectedIndexes())
            else:
                # Default: right-click selects the row under cursor for single-row context actions
                self._backup_selection = list(sel.selectedIndexes())
                if index.isValid():
                    sel.clearSelection()
                    sel.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            event.accept()
        else:
            super().mousePressEvent(event)

    def _build_multi_context_menu(self, ids: list[int]) -> QMenu:
        """
        Build aggregated context menu for multiple selected items.
        """
        menu = QMenu(self)

        # Resolve contexts
        ctx_list = []
        for _id in ids:
            meta = self.window.core.ctx.get_meta_by_id(_id)
            if meta is not None:
                ctx_list.append(meta)

        # Determine mixed states
        any_pinned = any(getattr(c, "important", False) for c in ctx_list)
        any_unpinned = any(not getattr(c, "important", False) for c in ctx_list)

        # Actions that pass a list of IDs
        a_open = menu.addAction(self._icons['chat'], trans('action.open'))
        a_open.triggered.connect(functools.partial(self.action_open, ids, None))

        a_open_new_tab = menu.addAction(self._icons['chat'], trans('action.open_new_tab'))
        a_open_new_tab.triggered.connect(functools.partial(self.action_open_new_tab, ids, None))

        a_rename = menu.addAction(self._icons['edit'], trans('action.rename'))
        a_rename.triggered.connect(functools.partial(self.action_rename, ids))

        a_duplicate = menu.addAction(self._icons['copy'], trans('action.duplicate'))
        a_duplicate.triggered.connect(functools.partial(self.action_duplicate, ids))

        # Pin/Unpin: show both if state is mixed
        if any_unpinned:
            a_pin = menu.addAction(self._icons['pin'], trans('action.pin'))
            a_pin.triggered.connect(functools.partial(self.action_pin, ids))
        if any_pinned:
            a_unpin = menu.addAction(self._icons['pin'], trans('action.unpin'))
            a_unpin.triggered.connect(functools.partial(self.action_unpin, ids))

        a_delete = menu.addAction(self._icons['delete'], trans('action.delete'))
        a_delete.triggered.connect(functools.partial(self.action_delete, ids))

        # Labels
        colors = self.window.controller.ui.get_colors()
        set_label_menu = menu.addMenu(trans('calendar.day.label'))
        for status_id, status_info in colors.items():
            name = trans('calendar.day.' + status_info['label']) if status_id != 0 else '-'
            icon = self._color_icon(status_info['color'])
            status_action = set_label_menu.addAction(icon, name)
            status_action.triggered.connect(
                functools.partial(self.action_set_label, ids, status_id)
            )

        # Indexing (IDX) aggregated
        idx_menu = QMenu(trans('action.idx'), self)
        idxs = self.window.core.config.get('llama.idx.list')
        store = self.window.core.idx.get_current_store()

        # Provide all available "index to" targets
        if idxs:
            for idx_dict in idxs:
                index_id = idx_dict['id']
                name = idx_dict['name'] + " (" + idx_dict['id'] + ")"
                action = idx_menu.addAction(self._icons['db'], "IDX: " + name)
                action.triggered.connect(functools.partial(self.action_idx, ids, index_id))

            # Provide "remove from" for the union of indexes over the current store
            union_store_indexes = set()
            for c in ctx_list:
                if getattr(c, "indexed", None) and getattr(c, "indexes", None):
                    if store in c.indexes:
                        for sidx in c.indexes[store]:
                            union_store_indexes.add(sidx)
            if union_store_indexes:
                idx_menu.addSeparator()
                for store_index in sorted(union_store_indexes):
                    action = idx_menu.addAction(self._icons['delete'], trans("action.idx.remove") + ": " + store_index)
                    action.triggered.connect(
                        functools.partial(self.action_idx_remove, store_index, ids)
                    )
            menu.addMenu(idx_menu)

        # Group operations
        group_menu = QMenu(trans('action.move_to'), self)
        groups = self.window.core.ctx.get_groups()

        action = group_menu.addAction(self._icons['add'], trans("action.group.new"))
        action.triggered.connect(functools.partial(self.window.controller.ctx.new_group, ids))

        if groups:
            group_menu.addSeparator()

        for group_id, group in groups.items():
            action = group_menu.addAction(self._icons['folder'], group.name)
            action.triggered.connect(functools.partial(self.window.controller.ctx.move_to_group, ids, group_id))

        # Remove from group if any selected is in a group
        in_any_group = any(getattr(c, "group_id", None) not in (None, 0) for c in ctx_list)
        if groups or in_any_group:
            group_menu.addSeparator()
        if in_any_group:
            action = group_menu.addAction(self._icons['delete'], trans("action.group.remove"))
            action.triggered.connect(functools.partial(self.window.controller.ctx.remove_from_group, ids))

        menu.addMenu(group_menu)

        # Copy IDs (list)
        a_copy_ids = menu.addAction(self._icons['copy'], trans('action.ctx_copy_id') + " x" + str(len(ids)))
        a_copy_ids.triggered.connect(functools.partial(self.action_copy_id, ids))

        # Reset (list)
        a_reset = menu.addAction(self._icons['close'], trans('action.ctx_reset'))
        a_reset.triggered.connect(functools.partial(self.action_reset, ids))

        return menu

    def _build_multi_group_context_menu(self, group_ids: list[int]) -> QMenu:
        """
        Build aggregated context menu for multiple selected groups.
        """
        menu = QMenu(self)

        a_new = menu.addAction(self._icons['add'], trans('action.ctx.new'))
        a_new.triggered.connect(functools.partial(self.action_group_new_in_group, group_ids))

        a_rename = menu.addAction(self._icons['edit'], trans('action.rename'))
        a_rename.triggered.connect(functools.partial(self.action_group_rename, group_ids))

        a_delete = menu.addAction(self._icons['delete'], trans('action.group.delete.only'))
        a_delete.triggered.connect(functools.partial(self.action_group_delete_only, group_ids))

        a_delete_all = menu.addAction(self._icons['delete'], trans('action.group.delete.all'))
        a_delete_all.triggered.connect(functools.partial(self.action_group_delete_all, group_ids))

        # Copy group IDs (list)
        a_copy = menu.addAction(self._icons['copy'], trans('action.ctx_copy_id') + " x" + str(len(group_ids)))
        a_copy.triggered.connect(functools.partial(self.action_copy_id, group_ids))

        return menu

    def show_context_menu(self, pos: QPoint):
        """
        Context menu event

        :param pos: QPoint
        """
        # Capture RMB anchor for scroll: item under cursor + current scroll value
        index = self.indexAt(pos)
        if index.isValid():
            self._context_menu_anchor_index = QPersistentModelIndex(index)
        else:
            self._context_menu_anchor_index = None
        try:
            self._context_menu_anchor_scroll_value = self.verticalScrollBar().value()
        except Exception:
            self._context_menu_anchor_scroll_value = None

        global_pos = self.viewport().mapToGlobal(pos)
        item = self._model.itemFromIndex(index)

        # If multiple groups are selected and the click was on a selected group row, show aggregated group menu
        selected_group_ids = self._selected_group_ids()
        if len(selected_group_ids) > 1 and index.isValid() and self.selectionModel().isSelected(index) and self._is_group_index(index):
            menu = self._build_multi_group_context_menu(selected_group_ids)
            if menu:
                menu.exec(global_pos)

            self.store_scroll_position()
            if self.restore_after_ctx_menu and self._backup_selection is not None:
                sel = self.selectionModel()
                sel.clearSelection()
                for sel_idx in self._backup_selection:
                    sel.select(sel_idx, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                self._backup_selection = None
            self.restore_after_ctx_menu = True
            self.restore_scroll_position()
            return

        # If multiple items are selected and the click was on a selected item row, show aggregated menu
        selected_ids = self._selected_item_ids()
        if len(selected_ids) > 1 and index.isValid() and self.selectionModel().isSelected(index) and not self._is_group_index(index):
            menu = self._build_multi_context_menu(selected_ids)
            if menu:
                menu.exec(global_pos)

            self.store_scroll_position()
            if self.restore_after_ctx_menu and self._backup_selection is not None:
                sel = self.selectionModel()
                sel.clearSelection()
                for sel_idx in self._backup_selection:
                    sel.select(sel_idx, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                self._backup_selection = None
            self.restore_after_ctx_menu = True
            self.restore_scroll_position()
            return

        if item is not None and index.isValid() and hasattr(item, 'id'):
            idx = item.row()
            id_value = item.id

            if hasattr(item, 'isFolder') and item.isFolder:
                menu = QMenu(self)
                a_new = menu.addAction(self._icons['add'], trans('action.ctx.new'))
                a_new.triggered.connect(functools.partial(self.window.controller.ctx.new_in_group, force=False, group_id=id_value))
                a_rename = menu.addAction(self._icons['edit'], trans('action.rename'))
                a_rename.triggered.connect(functools.partial(self.window.controller.ctx.rename_group, id_value))
                a_delete = menu.addAction(self._icons['delete'], trans('action.group.delete.only'))
                a_delete.triggered.connect(functools.partial(self.window.controller.ctx.delete_group, id_value))
                a_delete_all = menu.addAction(self._icons['delete'], trans('action.group.delete.all'))
                a_delete_all.triggered.connect(functools.partial(self.window.controller.ctx.delete_group_all, id_value))
                if idx >= 0:
                    menu.exec(global_pos)
            else:
                ctx_id = id_value
                ctx = self.window.core.ctx.get_meta_by_id(ctx_id)
                if ctx is None:
                    return

                is_important = ctx.important

                # For single selection payloads, pass a single ID

                menu = QMenu(self)
                a_open = menu.addAction(self._icons['chat'], trans('action.open'))
                a_open.triggered.connect(functools.partial(self.action_open, ctx_id, idx))

                a_open_new_tab = menu.addAction(self._icons['chat'], trans('action.open_new_tab'))
                a_open_new_tab.triggered.connect(functools.partial(self.action_open_new_tab, ctx_id, idx))

                a_rename = menu.addAction(self._icons['edit'], trans('action.rename'))
                a_rename.triggered.connect(functools.partial(self.action_rename, ctx_id))

                a_duplicate = menu.addAction(self._icons['copy'], trans('action.duplicate'))
                a_duplicate.triggered.connect(functools.partial(self.action_duplicate, ctx_id))

                if is_important:
                    a_pin = menu.addAction(self._icons['pin'], trans('action.unpin'))
                    a_pin.triggered.connect(functools.partial(self.action_unpin, ctx_id))
                else:
                    a_pin = menu.addAction(self._icons['pin'], trans('action.pin'))
                    a_pin.triggered.connect(functools.partial(self.action_pin, ctx_id))

                a_delete = menu.addAction(self._icons['delete'], trans('action.delete'))
                a_delete.triggered.connect(functools.partial(self.action_delete, ctx_id))

                colors = self.window.controller.ui.get_colors()
                set_label_menu = menu.addMenu(trans('calendar.day.label'))
                for status_id, status_info in colors.items():
                    name = trans('calendar.day.' + status_info['label']) if status_id != 0 else '-'
                    icon = self._color_icon(status_info['color'])
                    status_action = set_label_menu.addAction(icon, name)
                    status_action.triggered.connect(
                        functools.partial(self.action_set_label, ctx_id, status_id)
                    )

                idx_menu = QMenu(trans('action.idx'), self)
                idxs = self.window.core.config.get('llama.idx.list')
                store = self.window.core.idx.get_current_store()
                if idxs:
                    for idx_dict in idxs:
                        index_id = idx_dict['id']
                        name = idx_dict['name'] + " (" + idx_dict['id'] + ")"
                        action = idx_menu.addAction(self._icons['db'], "IDX: " + name)
                        action.triggered.connect(functools.partial(self.action_idx, ctx_id, index_id))

                    if ctx.indexed is not None and ctx.indexed > 0:
                        if store in ctx.indexes:
                            store_indexes = ctx.indexes[store]
                            idx_menu.addSeparator()
                            for store_index in store_indexes:
                                action = idx_menu.addAction(self._icons['delete'], trans("action.idx.remove") + ": " + store_index)
                                action.triggered.connect(
                                    functools.partial(self.action_idx_remove, store_index, ctx_id)
                                )
                    menu.addMenu(idx_menu)

                group_menu = QMenu(trans('action.move_to'), self)
                groups = self.window.core.ctx.get_groups()

                action = group_menu.addAction(self._icons['add'], trans("action.group.new"))
                action.triggered.connect(functools.partial(self.window.controller.ctx.new_group, ctx_id))

                if groups:
                    group_menu.addSeparator()

                for group_id, group in groups.items():
                    action = group_menu.addAction(self._icons['folder'], group.name)
                    action.triggered.connect(functools.partial(self.window.controller.ctx.move_to_group, ctx_id, group_id))

                if groups:
                    group_menu.addSeparator()

                if ctx.group_id is not None and ctx.group_id > 0:
                    group_name = str(ctx.group_id)
                    if ctx.group_id in groups:
                        group_name = groups[ctx.group_id].name
                    action = group_menu.addAction(self._icons['delete'], trans("action.group.remove") + ": " + group_name)
                    action.triggered.connect(functools.partial(self.window.controller.ctx.remove_from_group, ctx_id))

                menu.addMenu(group_menu)

                a_copy_id = menu.addAction(self._icons['copy'], trans('action.ctx_copy_id') + " @" + str(ctx_id))
                a_copy_id.triggered.connect(functools.partial(self.action_copy_id, ctx_id))

                if ctx.indexed is not None and ctx.indexed > 0:
                    suffix = ""
                    if ctx.updated > ctx.indexed:
                        suffix = " *"
                    dt = datetime.datetime.fromtimestamp(ctx.indexed).strftime("%Y-%m-%d %H:%M")
                    action = menu.addAction(self._icons['clock'], trans('action.ctx.indexed') + ": " + dt + suffix)
                    action.setEnabled(False)

                a_reset = menu.addAction(self._icons['close'], trans('action.ctx_reset'))
                a_reset.triggered.connect(functools.partial(self.action_reset, ctx_id))

                if idx >= 0:
                    # Keep internal single selection marker unchanged
                    self.window.controller.ctx.set_selected(ctx_id)
                    menu.exec(global_pos)

        self.store_scroll_position()

        if self.restore_after_ctx_menu:
            if self._backup_selection is not None:
                sel = self.selectionModel()
                sel.clearSelection()
                for sel_idx in self._backup_selection:
                    sel.select(sel_idx, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                self._backup_selection = None

        self.restore_after_ctx_menu = True
        self.restore_scroll_position()

    def get_visible_unpaged_ids(self) -> set:
        """
        Return a set of IDs for currently visible, ungrouped and not pinned items (top-level only).
        """
        ids = set()
        model = self._model
        for r in range(model.rowCount()):
            it = model.item(r)
            # skip groups and date sections
            if isinstance(it, GroupItem) or isinstance(it, SectionItem):
                continue
            if isinstance(it, Item):
                data = it.data(QtCore.Qt.ItemDataRole.UserRole) or {}
                in_group = bool(data.get("in_group", False))
                is_important = bool(data.get("is_important", False))
                if not in_group and not is_important and hasattr(it, "id"):
                    ids.add(int(it.id))
        return ids

    def action_open(self, id, idx: Union[int, list] = None):
        """
        Open context action handler.
        Accepts either a single string ID or a list of integer IDs.

        :param id: context id (str) or list of ids (list[int])
        :param idx: index id (optional)
        """
        self.restore_after_ctx_menu = False
        if isinstance(id, list) and len(id) > 0:
            # use the first selected item's index for multiple selection
            id = id[0]
        self.window.controller.ctx.load(id, select_idx=idx)

    def action_open_new_tab(self, id, idx: int = None):
        """
        Open context action handler in a new tab.
        Accepts either a single string ID or a list of integer IDs.

        :param id: context id (str) or list of ids (list[int])
        :param idx: index id (optional)
        """
        self.restore_after_ctx_menu = False
        if isinstance(id, list):
            for i in id:
                self.window.controller.ctx.load(i, new_tab=True)
            return
        self.window.controller.ctx.load(id, select_idx=idx, new_tab=True)

    def action_idx(self, id, idx):
        """
        Index with llama context action handler.
        Accepts either a single string ID or a list of integer IDs.

        :param id: context id (str) or list of ids (list[int])
        :param idx: index name/id
        """
        self.restore_after_ctx_menu = False
        self.window.controller.idx.indexer.index_ctx_meta(id, idx)

    def action_idx_remove(self, idx: str, meta_id):
        """
        Remove from index action handler.
        Accepts either a single string ID or a list of integer IDs.

        :param idx: index id
        :param meta_id: meta id (str) or list of ids (list[int])
        """
        self.restore_after_ctx_menu = False
        self.window.controller.idx.indexer.index_ctx_meta_remove(idx, meta_id)

    def action_rename(self, id):
        """
        Rename action handler.
        Accepts either a single string ID or a list of integer IDs.

        :param id: context id or list of ids
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.rename(id)

    def action_pin(self, id):
        """
        Pin action handler.
        Accepts either a single string ID or a list of integer IDs.

        :param id: context id or list of ids
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.set_important(id, True)

    def action_unpin(self, id):
        """
        Unpin action handler.
        Accepts either a single string ID or a list of integer IDs.

        :param id: context id or list of ids
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.set_important(id, False)

    def action_important(self, id):
        """
        Set as important action handler.
        Accepts either a single string ID or a list of integer IDs.

        :param id: context id or list of ids
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.set_important(id)

    def action_duplicate(self, id):
        """
        Duplicate handler.
        Accepts either a single string ID or a list of integer IDs.

        :param id: context id or list of ids
        """
        self.window.controller.ctx.common.duplicate(id)

    def action_delete(self, id):
        """
        Delete action handler.
        Accepts either a single string ID or a list of integer IDs.

        :param id: context id or list of ids
        """
        # Anchor scroll to RMB-targeted viewport position if available, else keep current value
        anchor_val = self._context_menu_anchor_scroll_value
        self._deletion_initiated = True
        self._activate_scroll_guard("delete", anchor_val)
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.delete(id)

    def action_copy_id(self, id):
        """
        Copy ID(s) action handler.
        Accepts either a single string ID or a list of integer IDs.

        :param id: context id or list of ids
        """
        self.window.controller.ctx.common.copy_id(id)

    def action_reset(self, id):
        """
        Reset action handler.
        Accepts either a single string ID or a list of integer IDs.

        :param id: context id or list of ids
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.common.reset(id)

    def action_set_label(self, id, label: int):
        """
        Set label action handler.
        Accepts either a single string ID or a list of integer IDs.

        :param id: context id or list of ids
        :param label: label id
        """
        self.window.controller.ctx.set_label(id, label)

    # Group bulk/single wrappers (accept single id or list of ids)
    def action_group_new_in_group(self, group_id_or_ids):
        """
        Create new context(s) inside the given group(s).
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.new_in_group(force=False, group_id=group_id_or_ids)

    def action_group_rename(self, group_id_or_ids):
        """
        Rename group(s).
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.rename_group(group_id_or_ids)

    def action_group_delete_only(self, group_id_or_ids):
        """
        Delete group(s) only (keep items).
        """
        # Preserve scroll around group deletion as well to avoid jump; anchor to RMB target if present
        anchor_val = self._context_menu_anchor_scroll_value
        self._deletion_initiated = True
        self._activate_scroll_guard("group_delete_only", anchor_val)
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.delete_group(group_id_or_ids)

    def action_group_delete_all(self, group_id_or_ids):
        """
        Delete group(s) with all items.
        """
        # Preserve scroll around group deletion as well to avoid jump; anchor to RMB target if present
        anchor_val = self._context_menu_anchor_scroll_value
        self._deletion_initiated = True
        self._activate_scroll_guard("group_delete_all", anchor_val)
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.delete_group_all(group_id_or_ids)

    def selectionCommand(self, index, event=None):
        """
        Selection command
        :param index: Index
        :param event: Event
        """
        # Prevent mixing selection types (groups vs items)
        try:
            if index and index.isValid():
                target_is_group = self._is_group_index(index)
                types = self._selection_types()
                if types == {'group'} and not target_is_group:
                    return QItemSelectionModel.NoUpdate
                if types == {'item'} and target_is_group:
                    return QItemSelectionModel.NoUpdate
        except Exception:
            pass
        return super().selectionCommand(index, event)


class ImportantItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    Item delegate that paints:
    - Attachment icon on the right side (centered vertically),
    - Pinned indicator (pin.svg icon) in the top-right corner (overlays if needed),
    - Label color as a full-height vertical bar on the left for labeled items,
    - Group enclosure indicator for expanded groups:
        - thin vertical bar (default 2 px) on the left side of child rows area,
        - thin horizontal bar (default 2 px) at the bottom of the last child row.
    """
    def __init__(self, parent=None, attachment_icon: QIcon = None, pin_icon: QIcon = None):
        super().__init__(parent)
        self._attachment_icon = attachment_icon or QIcon(":/icons/attachment.svg")
        # Use provided pin icon (transparent background) as pinned indicator
        self._pin_icon = pin_icon or QIcon(":/icons/pin.svg")

        # Predefined label colors (status -> QColor)
        self._status_colors = {
            0: QColor(100, 100, 100),
            1: QColor(255, 0, 0),
            2: QColor(255, 165, 0),
            3: QColor(255, 255, 0),
            4: QColor(0, 255, 0),
            5: QColor(0, 0, 255),
            6: QColor(75, 0, 130),
            7: QColor(238, 130, 238),
        }

        # Visual tuning constants
        self._pin_pen = QtGui.QPen(QtCore.Qt.black, 0.5, QtCore.Qt.SolidLine)  # kept for compatibility
        self._pin_diameter = 4            # legacy circle diameter (not used anymore)
        self._pin_margin = 3              # Margin from top and right edges
        self._attach_spacing = 4          # Kept for potential future layout tweaks
        self._label_bar_width = 4         # Full-height label bar width (left side)
        self._label_v_margin = 3          # 3px top/bottom margin for the label bar

        # Manual child indent to keep hierarchy visible when view indentation is 0
        self._child_indent = 15

        # Group indicator defaults (can be overridden by config)
        self._group_indicator_enabled = True
        self._group_indicator_width = 2
        self._group_indicator_color = QColor(67, 75, 78)  # soft gray
        self._group_indicator_gap = 6  # gap between child content left and the vertical bar
        self._group_indicator_bottom_offset = 6

        # Pinned icon sizing (kept deliberately small, similar to previous yellow dot)
        # The actual painted size is min(max_size, availableHeightWithMargins)
        self._pin_icon_max_size = 12  # px

        # Try to load customization from application config (safe if missing)
        self._init_group_indicator_from_config()

    def _init_group_indicator_from_config(self):
        """
        Initialize group indicator settings from config if available.
        Accepts:
          - color: list/tuple [r,g,b], dict {'r','g','b'}, "#RRGGBB", or "r,g,b"
          - width: int
          - enabled: bool
          - gap: int
        """
        try:
            view = self.parent()
            window = getattr(view, 'window', None)
            cfg = getattr(getattr(window, 'core', None), 'config', None)
            if not cfg:
                return

            enabled = cfg.get('ctx.records.groups.indicator.enabled')
            if enabled is not None:
                self._group_indicator_enabled = bool(enabled)

            width = cfg.get('ctx.records.groups.indicator.width')
            if isinstance(width, int) and width >= 0:
                self._group_indicator_width = int(width)

            gap = cfg.get('ctx.records.groups.indicator.gap')
            if isinstance(gap, int) and gap >= 0:
                self._group_indicator_gap = int(gap)

            color = cfg.get('ctx.records.groups.indicator.color')
            qcolor = self._parse_qcolor(color)
            if qcolor is not None:
                self._group_indicator_color = qcolor
        except Exception:
            # Fail-safe: keep defaults if anything goes wrong
            pass

    def _parse_qcolor(self, value):
        """
        Parses various color formats into QColor.
        Supports:
          - QColor
          - list/tuple [r, g, b]
          - dict {'r':..,'g':..,'b':..} or {'red':..,'green':..,'blue':..}
          - "#RRGGBB"
          - "r,g,b" (also "r;g;b")
        """
        if value is None:
            return None
        if isinstance(value, QColor):
            return value
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            try:
                r, g, b = int(value[0]), int(value[1]), int(value[2])
                return QColor(r, g, b)
            except Exception:
                return None
        if isinstance(value, dict):
            keys = value.keys()
            try:
                if all(k in keys for k in ('r', 'g', 'b')):
                    return QColor(int(value['r']), int(value['g']), int(value['b']))
                if all(k in keys for k in ('red', 'green', 'blue')):
                    return QColor(int(value['red']), int(value['green']), int(value['blue']))
            except Exception:
                return None
        if isinstance(value, str):
            s = value.strip()
            if s.startswith('#'):
                qc = QColor(s)
                return qc if qc.isValid() else None
            s = s.replace(';', ',')
            parts = [p.strip() for p in s.split(',') if p.strip()]
            if len(parts) >= 3:
                try:
                    r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                    return QColor(r, g, b)
                except Exception:
                    return None
        return None

    def paint(self, painter, option, index):
        # Shift children by +15 px to keep them visually nested.
        is_child = index.parent().isValid()
        if is_child:
            option.rect.adjust(self._child_indent, 0, 0, 0)

        # Detect if this row is a group/folder (top-level section).
        is_group = False
        try:
            model = index.model()
            item = model.itemFromIndex(index) if hasattr(model, "itemFromIndex") else None
            is_group = bool(item is not None and getattr(item, 'isFolder', False))
        except Exception:
            is_group = False

        # Default painting:
        # - For groups: translate painter -8 px to push folder/icon closer to the left edge.
        # - For others: paint normally.
        if is_group:
            painter.save()
            painter.translate(-2, 0)
            super(ImportantItemDelegate, self).paint(painter, option, index)
            painter.restore()
        else:
            super(ImportantItemDelegate, self).paint(painter, option, index)

        # Group enclosure indicator (left bar + bottom bar on last child)
        # This applies only to child rows (i.e., when a group is expanded).
        if self._group_indicator_enabled and not is_group and is_child and self._group_indicator_width > 0:
            try:
                painter.save()
                # Use solid fill for crisp 2px bars (no anti-alias blur)
                painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
                color = self._group_indicator_color
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(color)

                # Compute vertical bar geometry:
                # Place the bar to the LEFT of the child content area, leaving a small gap.
                child_left = option.rect.x()
                bar_w = self._group_indicator_width
                # Left edge of the vertical bar (never below 0)
                vbar_left = max(0, child_left - (self._group_indicator_gap + bar_w))
                vbar_rect = QtCore.QRect(vbar_left, option.rect.y(), bar_w, option.rect.height())
                painter.drawRect(vbar_rect)

                painter.restore()
            except Exception:
                # Fail-safe: do not block painting if anything goes wrong
                pass

        # Custom data painting for non-group items only (labels, pinned, attachments).
        if not is_group:
            data = index.data(QtCore.Qt.ItemDataRole.UserRole)
            if data:
                label = data.get("label", 0)
                is_important = data.get("is_important", False)
                is_attachment = data.get("is_attachment", False)

                painter.save()

                # Draw attachment icon on the right (centered vertically).
                # This is painted first, so the pin can overlay it when needed.
                icon_size = option.decorationSize or QtCore.QSize(16, 16)
                if is_attachment:
                    icon_pos_x = option.rect.right() - icon_size.width()
                    icon_pos_y = option.rect.top() + (option.rect.height() - icon_size.height()) // 2
                    icon_rect = QtCore.QRect(
                        icon_pos_x,
                        icon_pos_y,
                        icon_size.width(),
                        icon_size.height()
                    )
                    self._attachment_icon.paint(painter, icon_rect, QtCore.Qt.AlignCenter)

                # Pinned indicator: small pin.svg painted at fixed top-right position.
                # It overlays above any other right-side icons.
                if is_important:
                    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)

                    # Compute a compact size similar in footprint to previous circle,
                    # but readable for vector icon; clamp to available height.
                    available = max(8, option.rect.height() - 2 * self._pin_margin)
                    pin_size = min(self._pin_icon_max_size, available)

                    x = option.rect.right() - self._pin_margin - pin_size
                    y = option.rect.top() + self._pin_margin
                    pin_rect = QtCore.QRect(x, y, pin_size, pin_size)

                    # Paint the pin icon (transparent background)
                    self._pin_icon.paint(painter, pin_rect, QtCore.Qt.AlignCenter)

                # Label bar on the left with 3px vertical margins
                if label > 0:
                    color = self.get_color_for_status(label)
                    bar_y = option.rect.y() + self._label_v_margin
                    bar_h = max(1, option.rect.height() - 2 * self._label_v_margin)
                    bar_rect = QtCore.QRect(
                        option.rect.x(),
                        bar_y,
                        self._label_bar_width,
                        bar_h,
                    )
                    painter.setBrush(color)
                    painter.setPen(QtCore.Qt.NoPen)
                    painter.drawRect(bar_rect)

                painter.restore()

    def get_color_for_status(self, status: int) -> QColor:
        """
        Returns color mapped for given status value.
        """
        return self._status_colors.get(status, self._status_colors[0])


class GroupItem(QStandardItem):
    def __init__(self, icon, name, id):
        super().__init__(icon, name)
        self.id = id
        # Keep name as provided; display text is handled by the model/view
        self.name = name
        self.isFolder = True
        self.isPinned = False
        self.hasAttachments = False
        self.dt = None


class Item(QStandardItem):
    def __init__(self, name, id):
        super().__init__(name)
        self.id = id
        # Keep name as provided; display text is handled by the model/view
        self.name = name
        self.isFolder = False
        self.isPinned = False
        self.dt = None


class SectionItem(QStandardItem):
    def __init__(self, title, group: bool = False):
        super().__init__(title)
        self.title = title
        self.group = group
        self.setSelectable(False)
        self.setEnabled(False)
        self.setTextAlignment(QtCore.Qt.AlignRight)
        font = self.font()
        font.setBold(True)
        self.setFont(font)