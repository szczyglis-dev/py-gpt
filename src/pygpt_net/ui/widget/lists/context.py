#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.04 20:10:00                  #
# ================================================== #

import datetime
import functools
from typing import Union

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, QPoint, QItemSelectionModel, QPersistentModelIndex
from PySide6.QtGui import QIcon, QColor, QPixmap, QStandardItem, QDrag
from PySide6.QtWidgets import QMenu, QAbstractItemView, QFrame

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
        # Runtime-only visual expansion state for capped pinned/project/context
        # lists. The underlying context data remains fully loaded.
        self.show_all_pinned = False
        self.show_all_projects = False
        self.show_all_project_contexts = set()
        # Track an explicit user collapse separately from automatic reveal of
        # the currently active pinned/project context. This makes the trailing "less"
        # action authoritative even when the active row is beyond the cap.
        self.pinned_limit_collapsed_by_user = False
        self.projects_limit_collapsed_by_user = False
        self.project_contexts_limit_collapsed_by_user = set()
        # Top-level context-list sections (Pinned / Projects / Recent) have
        # their own persisted collapsed state. Missing/invalid config values
        # intentionally mean "all expanded" for backward compatibility.
        self.collapsed_sections = self._load_collapsed_sections()
        self._section_visibility_updating = False
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
            'folder': QIcon(":/icons/folder.svg"),
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
        self.setItemDelegate(ImportantItemDelegate(
            self,
            self._icons['attachment'],
            self._icons['pin'],
            self._icons['add'],
        ))

        # Hover actions. The delegate replaces the project context counter with
        # add.svg on project rows and shows add.svg on actionable section
        # headers (Projects / Recent). Mouse tracking is required so these
        # states update without a pressed mouse button.
        self._hover_group_index: QPersistentModelIndex | None = None
        self._hover_section_action_index: QPersistentModelIndex | None = None
        self.setMouseTracking(True)
        try:
            self.viewport().setMouseTracking(True)
        except Exception:
            pass

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

        # Persist expanded state also when user uses the disclosure arrow or programmatic expand/collapse
        self._connect_expand_collapse_signals()

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

        # Drag & Drop: enable internal drag of items onto group rows and a visual drop highlight
        self._drag_mime = "application/x-pygpt-ctx-ids"
        self._drop_highlight_index: QPersistentModelIndex | None = None

        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(False)
        try:
            # Available on QAbstractItemView in Qt6
            self.setDefaultDropAction(Qt.MoveAction)
        except Exception:
            pass

        # Drop target highlight overlay (same style as requested)
        self._dir_highlight = QFrame(self.viewport())
        self._dir_highlight.setObjectName("drop-dir-highlight")
        self._dir_highlight.setFrameShape(QFrame.NoFrame)
        self._dir_highlight.setStyleSheet(
            "#drop-dir-highlight { border: 2px solid rgba(40,120,255,0.95); border-radius: 3px; "
            "background-color: rgba(40,120,255,0.10); }"
        )
        self._dir_highlight.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._dir_highlight.hide()

        # Manual multi-select drag detection state
        self._drag_press_pos = QtCore.QPoint()
        self._drag_press_index: QPersistentModelIndex | None = None
        self._drag_pending_from_multi = False

        # Force-scroll runtime flags
        self._force_scroll_lock_active = False  # when True, blocks other auto-scrolls (guard restores)
        self._bypass_guard_once = False        # one-shot bypass for scroll guard

    def _connect_expand_collapse_signals(self):
        """
        Connect view expand/collapse signals to maintain persistent expanded_items state.
        """
        try:
            if hasattr(self, 'expanded'):
                self.expanded.connect(self._on_group_expanded)
            if hasattr(self, 'collapsed'):
                self.collapsed.connect(self._on_group_collapsed)
        except Exception:
            pass

    def _on_group_expanded(self, index: QtCore.QModelIndex):
        """
        Remember expanded group id when group is expanded from UI or programmatically.
        """
        try:
            item = self._model.itemFromIndex(index)
            if isinstance(item, GroupItem) and hasattr(item, "id"):
                self.expanded_items.add(item.id)
        except Exception:
            pass
        QtCore.QTimer.singleShot(0, self._refresh_hover_from_cursor)

    def _on_group_collapsed(self, index: QtCore.QModelIndex):
        """
        Forget group id when collapsed.
        """
        try:
            item = self._model.itemFromIndex(index)
            if isinstance(item, GroupItem) and hasattr(item, "id"):
                self.expanded_items.discard(item.id)
        except Exception:
            pass
        QtCore.QTimer.singleShot(0, self._refresh_hover_from_cursor)

    def _on_vertical_scroll(self, value: int):
        """
        Trigger infinite scroll: when scrollbar reaches bottom, request the next page.
        """
        if self._section_visibility_updating or 'recent' in self.collapsed_sections:
            return
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
            # When force-scroll lock is active, skip guard-driven restoration to avoid bouncing
            if getattr(self, "_force_scroll_lock_active", False):
                return
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
        Rows removed; schedule scroll restoration and clear any implicit parent
        project selection created by Qt after deleting a child context.
        """
        if self._scroll_guard_active or self._deletion_initiated:
            self._schedule_scroll_restore()
        if self._deletion_initiated:
            QtCore.QTimer.singleShot(0, self._clear_group_selection_after_delete)

    def _on_model_about_to_be_reset(self):
        """
        Model reset incoming. If it follows a delete operation, capture scroll now.
        """
        if self._deletion_initiated or self._scroll_guard_active:
            anchor_val = self._context_menu_anchor_scroll_value
            self._activate_scroll_guard("modelAboutToBeReset", anchor_val)

    def _on_model_reset(self):
        """
        Model has been reset; restore scroll if we armed the guard and clear any
        implicit parent-project selection caused by a delete-driven rebuild.
        """
        if self._scroll_guard_active or self._deletion_initiated:
            self._schedule_scroll_restore()
        if self._deletion_initiated:
            QtCore.QTimer.singleShot(0, self._clear_group_selection_after_delete)

    def _on_layout_about_to_change(self):
        """
        Layout change incoming; if it is a consequence of delete, capture scroll.
        """
        if self._deletion_initiated:
            anchor_val = self._context_menu_anchor_scroll_value
            self._activate_scroll_guard("layoutAboutToBeChanged", anchor_val)

    def _on_layout_changed(self):
        """
        Layout changed; restore scroll if guard is active and clear any implicit
        parent-project selection caused by a delete-driven layout update.
        """
        if self._scroll_guard_active or self._deletion_initiated:
            self._schedule_scroll_restore()
        if self._deletion_initiated:
            QtCore.QTimer.singleShot(0, self._clear_group_selection_after_delete)

    def scrollTo(self, index, hint=QAbstractItemView.EnsureVisible):
        """
        Block automatic scrolling requests while scroll guard is active
        (e.g., selection changes executed by controller after delete).
        Allow one-shot bypass for explicit force-scroll.
        """
        if self._deletion_initiated:
            return
        if self._scroll_guard_active or self._deletion_initiated:
            if not getattr(self, "_bypass_guard_once", False):
                return
        super().scrollTo(index, hint)
        self._bypass_guard_once = False  # consume bypass token

    def _is_index_visible_in_viewport(self, index: QtCore.QModelIndex, fully: bool = False) -> bool:
        """
        Returns True if the given index is currently visible in the viewport.
        When 'fully' is True, requires the whole rect to fit inside the viewport.
        """
        try:
            if not index or not index.isValid():
                return False
            rect = self.visualRect(index)
            if not rect.isValid():
                return False
            vp = self.viewport().rect()
            return vp.contains(rect) if fully else rect.intersects(vp)
        except Exception:
            return False

    def force_scroll_to_current(self, center: bool = True, duration_ms: int = 850):
        """
        Force-scroll to the current selection/index:
        - Temporarily blocks any auto scroll (guard-based restore),
        - One-shot bypasses scroll guard so this call cannot be blocked,
        - Expands ancestors so the target is visible in tree views,
        - If the target row is already visible in the current viewport, does nothing.

        :param center: when True, centers row; otherwise ensures it's just visible
        :param duration_ms: how long to block competing auto-scrolls (in ms)
        """
        try:
            index = self.currentIndex()
            if not index or not index.isValid():
                # Fallback to first selected row if current index is invalid
                sel = self.selectionModel()
                if sel:
                    rows = sel.selectedRows(0)
                    if rows:
                        index = rows[0]
            if not index or not index.isValid():
                return

            # If row is already visible with the current scroll, skip any scrolling
            if self._is_index_visible_in_viewport(index):
                return

            # Expand ancestors so index can become visible if it is currently hidden under a collapsed parent
            parent = index.parent()
            while parent.isValid():
                try:
                    if hasattr(self, "isExpanded") and not self.isExpanded(parent):
                        self.setExpanded(parent, True)
                except Exception:
                    break
                parent = parent.parent()

            # Check visibility again after potential expansion to avoid unnecessary scroll
            if self._is_index_visible_in_viewport(index):
                return

            # Arm force lock and guard bypass
            self._force_scroll_lock_active = True
            self._bypass_guard_once = True

            hint = QAbstractItemView.PositionAtCenter if center else QAbstractItemView.EnsureVisible
            self.scrollTo(index, hint)

            # Auto-release the force lock after the requested duration
            try:
                QtCore.QTimer.singleShot(
                    max(0, int(duration_ms)),
                    lambda: setattr(self, "_force_scroll_lock_active", False)
                )
            except Exception:
                # Fallback: ensure the flag is not left armed forever
                self._force_scroll_lock_active = False
        except Exception:
            pass

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

    def _is_show_more_index(self, index: QtCore.QModelIndex) -> bool:
        """Return True if index points to a visual capped-list expander row."""
        try:
            if not index.isValid():
                return False
            return isinstance(self._model.itemFromIndex(index), ShowMoreItem)
        except Exception:
            return False

    def _handle_show_more_click(self, index: QtCore.QModelIndex) -> bool:
        """Expand or collapse a capped pinned/project/project-context list."""
        if not self._is_show_more_index(index):
            return False
        try:
            item = self._model.itemFromIndex(index)
            if item.scope == ShowMoreItem.PINNED:
                if item.collapse:
                    self.show_all_pinned = False
                    self.pinned_limit_collapsed_by_user = True
                else:
                    self.show_all_pinned = True
                    self.pinned_limit_collapsed_by_user = False
            elif item.scope == ShowMoreItem.PROJECTS:
                if item.collapse:
                    self.show_all_projects = False
                    self.projects_limit_collapsed_by_user = True
                else:
                    self.show_all_projects = True
                    self.projects_limit_collapsed_by_user = False
            elif item.scope == ShowMoreItem.PROJECT_CONTEXTS and item.group_id is not None:
                group_id = int(item.group_id)
                if item.collapse:
                    self.show_all_project_contexts.discard(group_id)
                    self.project_contexts_limit_collapsed_by_user.add(group_id)
                else:
                    self.show_all_project_contexts.add(group_id)
                    self.project_contexts_limit_collapsed_by_user.discard(group_id)
            else:
                return False

            # Rebuild from already-loaded meta only. This is intentionally a
            # presentation toggle and must not trigger another DB page load.
            self.window.controller.ctx.update_list(reload=False, restore_scroll=True)
            QtCore.QTimer.singleShot(0, self._refresh_hover_from_cursor)
            return True
        except Exception:
            return False

    def _is_section_action_index(self, index: QtCore.QModelIndex) -> bool:
        """Return True if index points to an actionable top-level section row."""
        try:
            if not index.isValid() or index.parent().isValid():
                return False
            item = self._model.itemFromIndex(index)
            return isinstance(item, SectionItem) and bool(getattr(item, 'action', None))
        except Exception:
            return False

    def _is_collapsible_section_index(self, index: QtCore.QModelIndex) -> bool:
        """Return True if index points to a collapsible top-level section row."""
        try:
            if not index.isValid() or index.parent().isValid():
                return False
            item = self._model.itemFromIndex(index)
            return bool(
                isinstance(item, SectionItem)
                and getattr(item, 'section_key', None)
            )
        except Exception:
            return False

    def is_section_collapsed(self, index: QtCore.QModelIndex) -> bool:
        """Return True when the supplied top-level section is collapsed."""
        try:
            if not index.isValid() or not self._is_collapsible_section_index(index):
                return False
            item = self._model.itemFromIndex(index)
            section_key = getattr(item, 'section_key', None)
            return bool(section_key and section_key in self.collapsed_sections)
        except Exception:
            return False

    def _load_collapsed_sections(self) -> set[str]:
        """Load persisted collapsed section IDs; missing config means expanded."""
        try:
            value = self.window.core.config.get('ctx.list.sections.collapsed', [])
        except Exception:
            value = []
        if not isinstance(value, (list, tuple, set)):
            return set()
        allowed = {'pinned', 'projects', 'recent'}
        return {str(section) for section in value if str(section) in allowed}

    def _save_collapsed_sections(self):
        """Persist collapsed top-level section IDs."""
        try:
            self.window.core.config.set(
                'ctx.list.sections.collapsed',
                sorted(self.collapsed_sections),
            )
            self.window.core.config.save()
        except Exception:
            pass

    def apply_section_visibility(self):
        """Apply persisted collapsed state to all top-level section row ranges."""
        model = self.model()
        if model is None:
            return

        self._section_visibility_updating = True
        try:
            headers = []
            for row in range(model.rowCount()):
                item = model.item(row) if hasattr(model, 'item') else None
                if isinstance(item, SectionItem) and getattr(item, 'section_key', None):
                    headers.append((row, item.section_key))

            root = QtCore.QModelIndex()
            for i, (header_row, section_key) in enumerate(headers):
                next_header_row = headers[i + 1][0] if i + 1 < len(headers) else model.rowCount()
                last_row = next_header_row - 1

                # The empty spacer immediately before the next section visually
                # belongs to that next header, so keep it visible even when the
                # preceding section is collapsed.
                if last_row > header_row:
                    tail = model.item(last_row) if hasattr(model, 'item') else None
                    if (
                        isinstance(tail, SectionItem)
                        and not getattr(tail, 'section_key', None)
                        and not getattr(tail, 'title', '')
                    ):
                        last_row -= 1

                hidden = section_key in self.collapsed_sections
                for row in range(header_row + 1, last_row + 1):
                    self.setRowHidden(row, root, hidden)

                # Header and the next-section spacer must always stay visible.
                self.setRowHidden(header_row, root, False)
                if last_row + 1 < next_header_row:
                    self.setRowHidden(last_row + 1, root, False)
        finally:
            self._section_visibility_updating = False

    def _section_label_rect(self, index: QtCore.QModelIndex) -> QtCore.QRect:
        """Return the clickable rectangle occupied by a section's left label."""
        if not index.isValid() or not self._is_collapsible_section_index(index):
            return QtCore.QRect()
        try:
            delegate = self.itemDelegate()
            if hasattr(delegate, 'section_label_rect'):
                return delegate.section_label_rect(index, self.visualRect(index))
        except Exception:
            pass
        return QtCore.QRect()

    def _handle_section_toggle_click(self, index: QtCore.QModelIndex, pos: QtCore.QPoint) -> bool:
        """Toggle a top-level section only when its left text label is clicked."""
        if not index.isValid() or not self._is_collapsible_section_index(index):
            return False
        if not self._section_label_rect(index).contains(pos):
            return False

        try:
            item = self._model.itemFromIndex(index)
            section_key = getattr(item, 'section_key', None)
            if not section_key:
                return False
            if section_key in self.collapsed_sections:
                self.collapsed_sections.discard(section_key)
            else:
                self.collapsed_sections.add(section_key)
            self.apply_section_visibility()
            self._save_collapsed_sections()
            QtCore.QTimer.singleShot(0, self._refresh_hover_from_cursor)
            return True
        except Exception:
            return False

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

        Project rows are valid persistent selection targets only when selected
        explicitly through Ctrl/Shift multi-selection. Plain clicks are handled
        separately in mousePressEvent()/selectionCommand() and do not select a
        project row.
        """
        types = self._selection_types()
        if len(types) <= 1:
            return

        # Prefer the last explicit target type; otherwise keep the majority.
        if self._last_selection_target_is_group is not None:
            want_groups = bool(self._last_selection_target_is_group)
        else:
            g = len(self._selected_group_ids())
            i = len(self._selected_item_ids())
            want_groups = g >= i
        self._prune_selection_to_type(want_groups)

    def _clear_group_selection_after_delete(self):
        """
        Remove Qt's implicit fallback selection of a parent project after a
        destructive model update (for example deleting a context from a project).

        Explicit Ctrl/Shift project selection is unaffected during normal use;
        this cleanup is only scheduled from delete-related model-change handlers.
        """
        try:
            if not self._deletion_initiated:
                return
            sel = self.selectionModel()
            if not sel:
                return
            for idx in list(self._selected_rows()):
                if self._is_group_index(idx):
                    sel.select(idx, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)
            if self.currentIndex().isValid() and self._is_group_index(self.currentIndex()):
                self.setCurrentIndex(QtCore.QModelIndex())
        except Exception:
            pass

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

    def _event_pos_to_point(self, event) -> QtCore.QPoint:
        """
        Convert event position to QPoint, compatible with Qt6 and fallbacks.
        """
        try:
            return event.position().toPoint()
        except Exception:
            try:
                return event.pos()
            except Exception:
                return QtCore.QPoint()

    def _same_index(self, persistent_index, index: QtCore.QModelIndex) -> bool:
        """Return True when a persistent index points to the given model index."""
        try:
            return bool(
                persistent_index is not None
                and persistent_index.isValid()
                and index.isValid()
                and persistent_index.model() is index.model()
                and persistent_index.row() == index.row()
                and persistent_index.column() == index.column()
                and persistent_index.parent() == index.parent()
            )
        except Exception:
            return False

    def _index_under_cursor(self) -> QtCore.QModelIndex:
        """Return the model index currently under the physical mouse cursor."""
        try:
            viewport = self.viewport()
            pos = viewport.mapFromGlobal(QtGui.QCursor.pos())
            if not viewport.rect().contains(pos):
                return QtCore.QModelIndex()
            return self.indexAt(pos)
        except Exception:
            return QtCore.QModelIndex()

    def is_group_hovered(self, index: QtCore.QModelIndex) -> bool:
        """Return True when the pointer currently hovers the given project row."""
        # Resolve hover from the real cursor position first. This is important
        # after expand/collapse or a model rebuild: Qt may repaint the row while
        # the mouse stays perfectly still, so no mouseMoveEvent is generated and
        # a cached/persistent hover index can temporarily become stale.
        cursor_index = self._index_under_cursor()
        if cursor_index.isValid():
            return self._same_index(QPersistentModelIndex(cursor_index), index)
        return False

    def is_section_action_hovered(self, index: QtCore.QModelIndex) -> bool:
        """Return True when the pointer currently hovers an actionable section row."""
        # Collapsed sections intentionally expose the total item counter on
        # the right instead of add.svg, regardless of hover state.
        if self.is_section_collapsed(index):
            return False
        cursor_index = self._index_under_cursor()
        if cursor_index.isValid() and self._is_section_action_index(cursor_index):
            return self._same_index(QPersistentModelIndex(cursor_index), index)
        return False

    def _refresh_hover_from_cursor(self):
        """Synchronize cached hover state with the current physical cursor position."""
        index = self._index_under_cursor()
        self._set_hover_group_index(index)
        self._set_hover_section_action_index(index)

    def _repaint_index(self, index):
        """Request repaint only for the supplied row when it is still valid."""
        try:
            if index is not None and index.isValid():
                rect = self.visualRect(index)
                if rect.isValid():
                    self.viewport().update(rect)
        except Exception:
            pass

    def _set_hover_group_index(self, index: QtCore.QModelIndex):
        """Update the currently hovered project row and repaint old/new rows."""
        new_index = None
        if index.isValid() and self._is_group_index(index):
            new_index = QPersistentModelIndex(index)

        if new_index is not None:
            if self._same_index(self._hover_group_index, index):
                return
        elif self._hover_group_index is None:
            return

        old_index = self._hover_group_index
        self._hover_group_index = new_index
        self._repaint_index(old_index)
        self._repaint_index(new_index)

    def _clear_hover_group(self):
        """Clear project-row hover state and restore the normal counter."""
        if self._hover_group_index is None:
            return
        old_index = self._hover_group_index
        self._hover_group_index = None
        self._repaint_index(old_index)

    def _set_hover_section_action_index(self, index: QtCore.QModelIndex):
        """Update the hovered actionable section and repaint old/new rows."""
        new_index = None
        if index.isValid() and self._is_section_action_index(index):
            new_index = QPersistentModelIndex(index)

        if new_index is not None:
            if self._same_index(self._hover_section_action_index, index):
                return
        elif self._hover_section_action_index is None:
            return

        old_index = self._hover_section_action_index
        self._hover_section_action_index = new_index
        self._repaint_index(old_index)
        self._repaint_index(new_index)

    def _clear_hover_section_action(self):
        """Clear section-header hover action state."""
        if self._hover_section_action_index is None:
            return
        old_index = self._hover_section_action_index
        self._hover_section_action_index = None
        self._repaint_index(old_index)

    def _group_add_rect(self, index: QtCore.QModelIndex) -> QtCore.QRect:
        """Return the clickable add-icon rectangle for a project row."""
        if not index.isValid() or not self._is_group_index(index):
            return QtCore.QRect()
        try:
            delegate = self.itemDelegate()
            if hasattr(delegate, 'group_add_rect'):
                return delegate.group_add_rect(self.visualRect(index))
        except Exception:
            pass
        return QtCore.QRect()

    def _section_add_rect(self, index: QtCore.QModelIndex) -> QtCore.QRect:
        """Return the clickable add-icon rectangle for an actionable section row."""
        if not index.isValid() or not self._is_section_action_index(index):
            return QtCore.QRect()
        try:
            delegate = self.itemDelegate()
            if hasattr(delegate, 'section_add_rect'):
                return delegate.section_add_rect(self.visualRect(index))
        except Exception:
            pass
        return QtCore.QRect()

    def _handle_section_add_click(self, index: QtCore.QModelIndex, pos: QtCore.QPoint) -> bool:
        """Run the add action exposed by a Projects/Recent section header."""
        if not index.isValid() or not self._is_section_action_index(index):
            return False
        if self.is_section_collapsed(index):
            return False
        if not self.is_section_action_hovered(index):
            return False
        if not self._section_add_rect(index).contains(pos):
            return False

        try:
            item = self._model.itemFromIndex(index)
            action = getattr(item, 'action', None)
            if action == 'new_project':
                self.window.controller.ctx.new_group()
            elif action == 'new_context':
                # Always create outside a project, even if the controller still
                # remembers a previously active project.
                self.window.controller.ctx.new_ungrouped()
            else:
                return False

            QtCore.QTimer.singleShot(0, self._refresh_hover_from_cursor)
            return True
        except Exception:
            return False

    def _handle_group_add_click(self, index: QtCore.QModelIndex, pos: QtCore.QPoint) -> bool:
        """Create a new context in a project when its hover add icon is clicked."""
        if not index.isValid() or not self._is_group_index(index):
            return False
        if not self.is_group_hovered(index):
            return False
        if not self._group_add_rect(index).contains(pos):
            return False

        try:
            item = self._model.itemFromIndex(index)
            if item is None or not isinstance(item, GroupItem):
                return False
            group_id = item.id

            # Expand immediately and persist the state before the list is rebuilt
            # by creation of the new context.
            self.expanded_items.add(group_id)
            self.expand(index)
            self.window.controller.ctx.new_in_group(force=False, group_id=group_id)

            # new_in_group can rebuild the list and invalidate the cached
            # persistent index while the mouse has not moved at all.
            QtCore.QTimer.singleShot(0, self._refresh_hover_from_cursor)
            return True
        except Exception:
            return False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = self._event_pos_to_point(event)
            index = self.indexAt(pos)

            # Visual capped-list controls are handled manually because they use
            # the same disabled/header styling as section labels.
            if self._handle_show_more_click(index):
                event.accept()
                return

            # Section-header add icons are independent actions. Consume the
            # click before section collapsing so add.svg never toggles a section.
            if self._handle_section_add_click(index, pos):
                event.accept()
                return

            # Only the left text label toggles a whole Pinned / Projects /
            # Recent section. Clicking empty header space intentionally does
            # nothing.
            if self._handle_section_toggle_click(index, pos):
                event.accept()
                return
            if self._is_collapsible_section_index(index):
                event.accept()
                return

            # The project-row add icon is an independent action. Consume the
            # click here so the ordinary row click does not toggle/collapse the
            # project at the same time.
            if self._handle_group_add_click(index, pos):
                event.accept()
                return

            no_mod = (event.modifiers() == Qt.NoModifier)

            # A plain click on a project is navigation only: it may expand or
            # collapse the project, but must not create a persistent row
            # selection. Ctrl/Shift are intentionally excluded here so project
            # rows can still participate in explicit multi-selection.
            if no_mod and index.isValid() and self._is_group_index(index):
                self._last_selection_target_is_group = None
                self._drag_pending_from_multi = False
                self._drag_press_index = None
                self._force_single_click_index = None
                self._suppress_item_click = False

                # If projects were explicitly multi-selected before, a normal
                # click exits that project selection. Existing context selection
                # is left untouched.
                sel = self.selectionModel()
                if sel and self._selection_types() == {'group'}:
                    sel.clearSelection()

                super().mousePressEvent(event)
                return

            had_multi = self._has_multi_selection()
            self._drag_press_pos = pos
            self._drag_press_index = QPersistentModelIndex(index) if index.isValid() else None
            self._drag_pending_from_multi = False

            # Clear any stale suppression when user performs a plain left click
            if no_mod:
                self._suppress_item_click = False

            # When multiple selection is active and a plain left click occurs:
            # - clicking empty area clears the selection and consumes the click,
            # - clicking a selected row preserves selection and arms drag start,
            # - clicking an unselected row collapses multi-selection and arms one-shot activation.
            if had_multi and no_mod:
                sel = self.selectionModel()
                if not index.isValid():
                    if sel:
                        sel.clearSelection()
                    self.setCurrentIndex(QtCore.QModelIndex())
                    try:
                        self.window.controller.ctx.unselect()
                    except Exception:
                        pass
                    self._force_single_click_index = None
                    event.accept()
                    return

                if sel and sel.isSelected(index):
                    # Preserve current selection and arm manual drag for multi-select
                    self._drag_pending_from_multi = True
                    self._suppress_item_click = True
                    event.accept()
                    return
                else:
                    # Collapse multi-selection and allow normal single-row behavior
                    if sel:
                        self._backup_selection = list(sel.selectedIndexes())
                        sel.clearSelection()
                    self.setCurrentIndex(QtCore.QModelIndex())
                    try:
                        self.window.controller.ctx.unselect()
                    except Exception:
                        pass
                    # Arm one-shot activation for the clicked row; Qt will select it afterwards
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
            # Project rows are never persistently selected. Right-clicking a
            # project opens its menu from the index under the cursor while the
            # existing context selection remains untouched.
            if index.isValid() and self._is_group_index(index):
                self._backup_selection = list(sel.selectedIndexes())
            # Keep current multi-selection if right-click happens on one of the selected rows
            elif index.isValid() and sel.isSelected(index) and (multi_items or multi_groups):
                self._backup_selection = list(sel.selectedIndexes())
            else:
                # Default for contexts: right-click selects the row under cursor for single-row actions
                self._backup_selection = list(sel.selectedIndexes())
                if index.isValid():
                    sel.clearSelection()
                    sel.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Update row/header hover actions and handle manual multi-item drag start.
        """
        pos = self._event_pos_to_point(event)

        # Keep hover active also while the mouse button is pressed. Previously
        # any tiny movement during a click cleared the hover state and the count
        # came back until the next no-button mouseMoveEvent.
        hover_index = self.indexAt(pos)
        self._set_hover_group_index(hover_index)
        self._set_hover_section_action_index(hover_index)

        try:
            if (event.buttons() & Qt.LeftButton) and self._drag_pending_from_multi and not self._is_group_index(self._drag_press_index or QtCore.QModelIndex()):
                if (pos - self._drag_press_pos).manhattanLength() >= QtWidgets.QApplication.startDragDistance():
                    self._drag_pending_from_multi = False
                    self.startDrag(Qt.MoveAction)
                    event.accept()
                    return
        except Exception:
            # Fall back to default behavior on any error
            self._drag_pending_from_multi = False
        super().mouseMoveEvent(event)

    def viewportEvent(self, event):
        """Show add-action tooltips only when the pointer is over add.svg itself."""
        if event.type() == QtCore.QEvent.ToolTip:
            pos = self._event_pos_to_point(event)
            index = self.indexAt(pos)
            tooltip = None
            tooltip_rect = QtCore.QRect()

            if index.isValid():
                if self._is_group_index(index):
                    tooltip_rect = self._group_add_rect(index)
                    if tooltip_rect.contains(pos):
                        tooltip = trans('ctx.add.new_context.tooltip')
                elif self._is_section_action_index(index) and not self.is_section_collapsed(index):
                    tooltip_rect = self._section_add_rect(index)
                    if tooltip_rect.contains(pos):
                        try:
                            item = self._model.itemFromIndex(index)
                            action = getattr(item, 'action', None)
                            if action == 'new_project':
                                tooltip = trans('ctx.add.new_project.tooltip')
                            elif action == 'new_context':
                                tooltip = trans('ctx.add.new_context.tooltip')
                        except Exception:
                            tooltip = None

            if tooltip:
                try:
                    global_pos = event.globalPosition().toPoint()
                except Exception:
                    global_pos = QtGui.QCursor.pos()
                QtWidgets.QToolTip.showText(
                    global_pos,
                    tooltip,
                    self.viewport(),
                    tooltip_rect,
                )
                return True

            QtWidgets.QToolTip.hideText()

        return super().viewportEvent(event)

    def leaveEvent(self, event):
        """Restore normal row/header content when the pointer leaves the list."""
        self._clear_hover_group()
        self._clear_hover_section_action()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Clean up drag state on release and preserve hover without requiring
        an additional mouse movement.
        """
        if event.button() == Qt.LeftButton and self._drag_pending_from_multi:
            self._drag_pending_from_multi = False
            self._drag_press_index = None
        super().mouseReleaseEvent(event)

        # clicked/expanded/collapsed handlers can repaint or rebuild the model
        # during super().mouseReleaseEvent(). Re-resolve hover from QCursor so
        # the add icon remains visible under a stationary mouse pointer.
        self._refresh_hover_from_cursor()
        QtCore.QTimer.singleShot(0, self._refresh_hover_from_cursor)

    @staticmethod
    def _get_common_project_group_id(ctx_list) -> int | None:
        """Return a project ID when every selected context belongs to the same project."""
        if not ctx_list:
            return None
        group_ids = set()
        for ctx in ctx_list:
            group_id = getattr(ctx, "group_id", None)
            if group_id is None:
                return None
            try:
                group_id = int(group_id)
            except (TypeError, ValueError):
                return None
            if group_id <= 0:
                return None
            group_ids.add(group_id)
            if len(group_ids) > 1:
                return None
        return next(iter(group_ids)) if group_ids else None

    @staticmethod
    def _get_ctx_store_indexes(ctx, store: str) -> set[str]:
        """Return index IDs currently tracked for a context in the selected store."""
        indexes = getattr(ctx, "indexes", None)
        if not isinstance(indexes, dict):
            return set()
        store_indexes = indexes.get(store, {})
        if isinstance(store_indexes, dict):
            return {str(idx) for idx in store_indexes.keys()}
        # Compatibility with older/alternate serialized forms.
        if isinstance(store_indexes, (list, tuple, set)):
            return {str(idx) for idx in store_indexes}
        return set()

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
        project_group_id = self._get_common_project_group_id(ctx_list)
        project_idx = None
        indexed_by_ctx = [self._get_ctx_store_indexes(c, store) for c in ctx_list]
        has_index_target = False

        # A project-local target is available only when every selected context
        # belongs to the same project. Hide it when every selected context is
        # already tracked in that project index; it will then be available only
        # in the "Remove from index" section below.
        if project_group_id is not None:
            project_idx = self.window.core.idx.project.get_idx_id(project_group_id)
            if not indexed_by_ctx or not all(project_idx in current for current in indexed_by_ctx):
                action = idx_menu.addAction(
                    self._icons['db'],
                    "IDX: " + trans('idx.current_project'),
                )
                action.triggered.connect(functools.partial(self.action_idx, ids, project_idx))
                has_index_target = True

        # Provide configured global "index to" targets only when at least one
        # selected context is not already indexed there.
        if idxs:
            for idx_dict in idxs:
                index_id = str(idx_dict['id'])
                if indexed_by_ctx and all(index_id in current for current in indexed_by_ctx):
                    continue
                name = idx_dict['name'] + " (" + idx_dict['id'] + ")"
                action = idx_menu.addAction(self._icons['db'], "IDX: " + name)
                action.triggered.connect(functools.partial(self.action_idx, ids, index_id))
                has_index_target = True

        # Provide "remove from" for the union of indexes over the current store.
        union_store_indexes = set().union(*indexed_by_ctx) if indexed_by_ctx else set()
        if union_store_indexes:
            if has_index_target:
                idx_menu.addSeparator()
            for store_index in sorted(union_store_indexes):
                display_idx = (
                    trans('idx.current_project')
                    if project_idx is not None and store_index == project_idx
                    else store_index
                )
                action = idx_menu.addAction(
                    self._icons['delete'],
                    trans("action.idx.remove") + ": " + display_idx,
                )
                action.triggered.connect(
                    functools.partial(self.action_idx_remove, store_index, ids)
                )

        if has_index_target or union_store_indexes:
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

        a_rename = menu.addAction(self._icons['edit'], trans('action.edit'))
        a_rename.triggered.connect(functools.partial(self.action_group_edit, group_ids))

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
                a_rename = menu.addAction(self._icons['edit'], trans('action.edit'))
                a_rename.triggered.connect(functools.partial(self.window.controller.ctx.edit_group, id_value))
                a_duplicate = menu.addAction(self._icons['copy'], trans('action.group.duplicate'))
                a_duplicate.triggered.connect(functools.partial(self.window.controller.ctx.duplicate_group, id_value))

                menu.addSeparator()
                state = self.window.core.idx.project.get(id_value)
                last_update = int(state.get('last_update', 0)) if state else 0
                if last_update > 0:
                    last_str = datetime.datetime.fromtimestamp(last_update).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    last_str = trans('settings.llama.extra.db.never')
                update_label = trans('idx.project.update') + " (" + trans('idx.last') + ": " + last_str + ")"
                a_idx_update = menu.addAction(self._icons['db'], update_label)
                a_idx_update.triggered.connect(
                    functools.partial(self.window.controller.ctx.update_project_index, id_value)
                )
                a_idx_truncate = menu.addAction(self._icons['delete'], trans('idx.project.truncate'))
                a_idx_truncate.triggered.connect(
                    functools.partial(self.window.controller.ctx.truncate_project_index, id_value)
                )

                menu.addSeparator()
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
                project_group_id = self._get_common_project_group_id([ctx])
                project_idx = None
                store_indexes = self._get_ctx_store_indexes(ctx, store)
                has_index_target = False

                if project_group_id is not None:
                    project_idx = self.window.core.idx.project.get_idx_id(project_group_id)
                    if project_idx not in store_indexes:
                        action = idx_menu.addAction(
                            self._icons['db'],
                            "IDX: " + trans('idx.current_project'),
                        )
                        action.triggered.connect(
                            functools.partial(self.action_idx, ctx_id, project_idx)
                        )
                        has_index_target = True

                if idxs:
                    for idx_dict in idxs:
                        index_id = str(idx_dict['id'])
                        if index_id in store_indexes:
                            continue
                        name = idx_dict['name'] + " (" + idx_dict['id'] + ")"
                        action = idx_menu.addAction(self._icons['db'], "IDX: " + name)
                        action.triggered.connect(functools.partial(self.action_idx, ctx_id, index_id))
                        has_index_target = True

                if store_indexes:
                    if has_index_target:
                        idx_menu.addSeparator()
                    for store_index in sorted(store_indexes):
                        display_idx = (
                            trans('idx.current_project')
                            if project_idx is not None and store_index == project_idx
                            else store_index
                        )
                        action = idx_menu.addAction(
                            self._icons['delete'],
                            trans("action.idx.remove") + ": " + display_idx,
                        )
                        action.triggered.connect(
                            functools.partial(self.action_idx_remove, store_index, ctx_id)
                        )

                if has_index_target or store_indexes:
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

    def action_group_edit(self, group_id_or_ids):
        """Edit project(s)."""
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.edit_group(group_id_or_ids)

    def action_group_rename(self, group_id_or_ids):
        """Backward-compatible wrapper for project editing."""
        self.action_group_edit(group_id_or_ids)

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
        # Preserve scroll around group deletion as well to avoid jumps; anchor to RMB target if present
        anchor_val = self._context_menu_anchor_scroll_value
        self._deletion_initiated = True
        self._activate_scroll_guard("group_delete_all", anchor_val)
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.delete_group_all(group_id_or_ids)

    def selectionCommand(self, index, event=None):
        """
        Selection command.

        A plain click on a project is navigation-only and does not select the
        project row. Ctrl/Shift selection of projects is allowed. Additive
        selection is kept homogeneous, so project rows and context rows are not
        mixed in one persistent selection.

        :param index: Index
        :param event: Event
        """
        command = super().selectionCommand(index, event)

        try:
            if index and index.isValid():
                target_is_group = self._is_group_index(index)

                if target_is_group:
                    modifiers = Qt.NoModifier
                    try:
                        if event is not None and hasattr(event, 'modifiers'):
                            modifiers = event.modifiers()
                        else:
                            modifiers = QtWidgets.QApplication.keyboardModifiers()
                    except Exception:
                        modifiers = Qt.NoModifier

                    # Normal project click: never create a persistent selection.
                    if not (modifiers & (Qt.ControlModifier | Qt.ShiftModifier)):
                        return QItemSelectionModel.NoUpdate

                types = self._selection_types()
                type_mismatch = (
                    (types == {'group'} and not target_is_group)
                    or (types == {'item'} and target_is_group)
                )

                if type_mismatch:
                    # Replacement selection can safely switch between project
                    # and context rows without creating a mixed selection.
                    if command & QItemSelectionModel.Clear:
                        return command

                    # Additive/toggle selection of the opposite row type is
                    # blocked; mousePressEvent normalizes Ctrl/Shift selection
                    # to the clicked target type first.
                    return QItemSelectionModel.NoUpdate
        except Exception:
            pass

        return command

    # =========================
    # Drag & Drop implementation
    # =========================

    def _is_valid_drag_source_selection(self) -> bool:
        """
        Returns True if current selection contains only non-group items.
        """
        types = self._selection_types()
        return types in (set(), {'item'}) and len(self._selected_item_ids()) > 0

    def startDrag(self, supportedActions):
        """
        Start drag only for non-group items. Pack selected item IDs into custom mime.
        """
        if not self._is_valid_drag_source_selection():
            return  # do not start drag for groups or empty selection

        ids = self._selected_item_ids()
        if not ids:
            return

        mime = QtCore.QMimeData()
        payload = ",".join(str(i) for i in ids).encode("utf-8")
        mime.setData(self._drag_mime, payload)
        mime.setText(",".join(str(i) for i in ids))

        drag = QDrag(self)
        drag.setMimeData(mime)

        # Compact drag pixmap with count
        w, h = 140, 28
        pm = QPixmap(w, h)
        pm.fill(Qt.transparent)
        painter = QtGui.QPainter(pm)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        rect = QtCore.QRectF(0.5, 0.5, w - 1, h - 1)
        bg = QColor(40, 120, 255, 32)
        pen = QtGui.QPen(QColor(40, 120, 255, 200), 1.5)
        painter.setPen(pen)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 6, 6)
        painter.setPen(QColor(40, 120, 255, 230))
        text = "Move {} item{}".format(len(ids), "" if len(ids) == 1 else "s")
        painter.drawText(pm.rect(), Qt.AlignCenter, text)
        painter.end()
        drag.setPixmap(pm)
        drag.setHotSpot(QtCore.QPoint(pm.width() // 2, pm.height() // 2))

        drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        """
        Accept drags that carry our custom payload (item IDs).
        """
        md = event.mimeData()
        if md and md.hasFormat(self._drag_mime):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        """
        While dragging:
        - accept only when hovering over a group row,
        - show highlight frame over the target group row.
        """
        md = event.mimeData()
        if not md or not md.hasFormat(self._drag_mime):
            self._hide_drop_highlight()
            event.ignore()
            return

        pos = self._event_pos_to_point(event)
        index = self.indexAt(pos)

        if index.isValid() and self._is_group_index(index):
            self._update_drop_highlight(index)
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            self._hide_drop_highlight()
            event.ignore()

    def dragLeaveEvent(self, event: QtGui.QDragLeaveEvent):
        """
        Hide highlight when drag leaves the view.
        """
        self._hide_drop_highlight()
        event.accept()

    def dropEvent(self, event: QtGui.QDropEvent):
        """
        On drop:
        - parse dragged item IDs,
        - resolve group row under cursor,
        - call controller.move_to_group(ids, group_id).
        """
        try:
            md = event.mimeData()
            if not md or not md.hasFormat(self._drag_mime):
                self._hide_drop_highlight()
                event.ignore()
                return

            ids = self._parse_drag_ids(md)
            if not ids:
                self._hide_drop_highlight()
                event.ignore()
                return

            pos = self._event_pos_to_point(event)
            index = self.indexAt(pos)
            if not index.isValid() or not self._is_group_index(index):
                self._hide_drop_highlight()
                event.ignore()
                return

            group_item = self._model.itemFromIndex(index)
            group_id = int(getattr(group_item, "id", 0))

            # Preserve scroll around move operations to avoid jumps
            try:
                anchor_val = self.verticalScrollBar().value()
            except Exception:
                anchor_val = None
            self._activate_scroll_guard("dragdrop_move", anchor_val)

            # Perform move via controller (accepts single ID or list)
            self.window.controller.ctx.move_to_group(ids, group_id)

            self._hide_drop_highlight()
            event.setDropAction(Qt.MoveAction)
            event.accept()
            # schedule restore (layout changes should trigger, but ensure anyway)
            self._schedule_scroll_restore()
        except Exception:
            # Fail-safe: do not break DnD if something goes wrong
            self._hide_drop_highlight()
            event.ignore()

    def _parse_drag_ids(self, mime: QtCore.QMimeData) -> list[int]:
        """
        Decode list of dragged item IDs from mime data.
        """
        try:
            raw = bytes(mime.data(self._drag_mime)).decode("utf-8").strip()
            if not raw:
                return []
            out = []
            for part in raw.split(","):
                part = strip = part.strip()
                if not strip:
                    continue
                try:
                    out.append(int(strip))
                except Exception:
                    continue
            return out
        except Exception:
            return []

    def _update_drop_highlight(self, index: QtCore.QModelIndex):
        """
        Show and position the highlight frame around the given group row.
        """
        try:
            if not index.isValid() or not self._is_group_index(index):
                self._hide_drop_highlight()
                return

            rect = self.visualRect(index)
            if not rect.isValid() or rect.width() <= 0 or rect.height() <= 0:
                self._hide_drop_highlight()
                return

            self._drop_highlight_index = QPersistentModelIndex(index)
            # Slightly inflate the rect for a nicer look without clipping
            geom = rect.adjusted(1, 1, -1, -1)
            self._dir_highlight.setGeometry(geom)
            self._dir_highlight.raise_()
            if not self._dir_highlight.isVisible():
                self._dir_highlight.show()
        except Exception:
            self._hide_drop_highlight()

    def _hide_drop_highlight(self):
        """
        Hide the highlight frame and clear state.
        """
        try:
            if self._dir_highlight.isVisible():
                self._dir_highlight.hide()
        except Exception:
            pass
        self._drop_highlight_index = None


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
    def __init__(
            self,
            parent=None,
            attachment_icon: QIcon = None,
            pin_icon: QIcon = None,
            add_icon: QIcon = None,
    ):
        super().__init__(parent)
        self._attachment_icon = attachment_icon or QIcon(":/icons/attachment.svg")
        # Use provided pin icon (transparent background) as pinned indicator
        self._pin_icon = pin_icon or QIcon(":/icons/pin.svg")
        self._add_icon = add_icon or QIcon(":/icons/add.svg")

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
        self._pin_diameter = 4
        self._pin_margin = 3
        self._attach_spacing = 4
        self._label_bar_width = 4
        self._label_v_margin = 3

        # Manual child indent to keep hierarchy visible when view indentation is 0
        self._child_indent = 15

        # Group indicator defaults (can be overridden by config)
        self._group_indicator_enabled = True
        self._group_indicator_width = 2
        self._group_indicator_color = QColor(67, 75, 78)  # soft gray
        self._group_indicator_gap = 6
        self._group_indicator_bottom_offset = 6

        # Pinned icon sizing
        self._pin_icon_max_size = 12  # px

        # Right-aligned counter for group rows
        self._group_count_left_gap = 12
        self._group_count_right_margin = 8
        self._group_count_color = QColor(128, 128, 128)
        # Extra padding so wide values like "999" are never cramped
        self._group_count_extra_pad = 4
        self._group_add_icon_size = 14

        # Try to load customization from application config (safe if missing)
        self._init_group_indicator_from_config()

    def group_add_rect(self, row_rect: QtCore.QRect) -> QtCore.QRect:
        """Return the add.svg paint/hit-test rectangle for a project row."""
        if not row_rect.isValid() or row_rect.height() <= 0:
            return QtCore.QRect()
        size = min(self._group_add_icon_size, max(8, row_rect.height() - 4))
        icon_right = row_rect.right() - self._group_count_right_margin
        icon_x = icon_right - size
        icon_y = row_rect.top() + (row_rect.height() - size) // 2
        return QtCore.QRect(icon_x, icon_y, size, size)

    def section_add_rect(self, row_rect: QtCore.QRect) -> QtCore.QRect:
        """Return the add.svg paint/hit-test rectangle for a section header."""
        return self.group_add_rect(row_rect)

    def section_label_rect(self, index: QtCore.QModelIndex, row_rect: QtCore.QRect) -> QtCore.QRect:
        """Return the actual left-title hit area for a collapsible section."""
        if not index.isValid() or not row_rect.isValid():
            return QtCore.QRect()
        try:
            model = index.model()
            item = model.itemFromIndex(index) if hasattr(model, 'itemFromIndex') else None
            if not isinstance(item, SectionItem) or not getattr(item, 'section_key', None):
                return QtCore.QRect()

            opt = QtWidgets.QStyleOptionViewItem()
            opt.rect = QtCore.QRect(row_rect)
            self.initStyleOption(opt, index)
            view = self.parent()
            if view is not None:
                opt.widget = view
            opt.text = item.title
            opt.displayAlignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
            style = view.style() if view is not None else QtWidgets.QApplication.style()
            text_rect = style.subElementRect(
                QtWidgets.QStyle.SE_ItemViewItemText,
                opt,
                opt.widget,
            )
            if not text_rect.isValid() or text_rect.width() <= 0:
                text_rect = row_rect.adjusted(2, 0, -2, 0)

            fm = QtGui.QFontMetrics(opt.font)
            width = min(text_rect.width(), max(1, fm.horizontalAdvance(item.title)))
            return QtCore.QRect(
                text_rect.left(),
                row_rect.top(),
                width,
                row_rect.height(),
            )
        except Exception:
            return QtCore.QRect()

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
        # Section rows may optionally contain a fixed left title plus an
        # independently elidable, right-aligned secondary label.
        item = None
        try:
            model = index.model()
            item = model.itemFromIndex(index) if hasattr(model, "itemFromIndex") else None
        except Exception:
            item = None

        # Project-list limit controls are clickable presentation rows but deliberately use
        # the exact disabled/bold typography of context-list headers. Paint it
        # through the native item-view style and center the text across the row.
        if isinstance(item, ShowMoreItem):
            opt = QtWidgets.QStyleOptionViewItem(option)
            self.initStyleOption(opt, index)
            opt.state &= ~QtWidgets.QStyle.State_MouseOver
            opt.text = item.title
            opt.displayAlignment = QtCore.Qt.AlignCenter
            style = opt.widget.style() if opt.widget is not None else QtWidgets.QApplication.style()
            style.drawControl(
                QtWidgets.QStyle.CE_ItemViewItem,
                opt,
                painter,
                opt.widget,
            )
            return

        # A collapsed top-level section always shows its full item count on
        # the right. This takes precedence over hover actions (add.svg) and
        # over Recent's inline date label.
        if isinstance(item, SectionItem) and getattr(item, 'section_key', None):
            view = self.parent()
            is_collapsed = False
            try:
                is_collapsed = bool(
                    view is not None
                    and view.is_section_collapsed(index)
                )
            except Exception:
                is_collapsed = False

            if is_collapsed and getattr(item, 'section_count', None) is not None:
                self._paint_split_section(
                    painter,
                    option,
                    index,
                    item,
                    right_text=str(item.section_count),
                )
                return

        if isinstance(item, SectionItem) and item.action:
            view = self.parent()
            is_hovered = False
            try:
                is_hovered = bool(
                    view is not None
                    and view.is_section_action_hovered(index)
                )
            except Exception:
                is_hovered = False

            # Actionable headers without secondary text (e.g. Projects) must
            # use the *same* paint path both before and during hover. Switching
            # from Qt's default delegate painting to our custom action painter
            # changes the text baseline by a pixel with some styles, which made
            # the header visibly jump when add.svg appeared.
            if not item.right_text:
                self._paint_action_section(
                    painter,
                    option,
                    index,
                    item,
                    show_icon=is_hovered,
                )
                return

            if is_hovered:
                self._paint_action_section(
                    painter,
                    option,
                    index,
                    item,
                    show_icon=True,
                )
                return

        if isinstance(item, SectionItem) and item.right_text:
            self._paint_split_section(painter, option, index, item)
            return

        # Plain top-level section headers (currently Pinned) must use the same
        # painter as their collapsed/count state. Otherwise Qt's default item
        # painter and _paint_split_section() can produce a one-pixel baseline
        # difference when the section is collapsed and the counter appears.
        if isinstance(item, SectionItem) and getattr(item, 'section_key', None):
            self._paint_split_section(painter, option, index, item)
            return

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

        if is_group:
            # Fetch group metadata stored in UserRole
            data = index.data(QtCore.Qt.ItemDataRole.UserRole) or {}
            count = int(data.get("count", 0)) if isinstance(data, dict) and "count" in data else 0
            has_attachment = bool(data.get("is_attachment", False))

            view = self.parent()
            is_hovered = False
            try:
                is_hovered = bool(view is not None and view.is_group_hovered(index))
            except Exception:
                is_hovered = False

            fm = option.fontMetrics
            icon_size = option.decorationSize or QtCore.QSize(16, 16)

            count_text = str(count) if count > 0 else ""
            has_count = bool(count_text)
            count_w = fm.horizontalAdvance(count_text) if has_count else 0
            show_action = is_hovered or has_count
            if is_hovered:
                action_w = self.group_add_rect(option.rect).width()
            elif has_count:
                action_w = count_w + self._group_count_extra_pad
            else:
                action_w = 0

            # Compute reserved right-side space:
            # right margin + [counter/add action] + [attachment + spacing] + left gap
            reserve = self._group_count_right_margin
            if show_action:
                reserve += action_w
            if has_attachment:
                reserve += icon_size.width()
                if show_action:
                    reserve += self._attach_spacing
            if show_action or has_attachment:
                reserve += self._group_count_left_gap

            opt = QtWidgets.QStyleOptionViewItem(option)

            # Plain clicks on projects are navigation-only, so suppress any
            # transient current-row highlight Qt may paint. Explicit Ctrl/Shift
            # project selections remain visible like ordinary selected rows.
            try:
                is_selected = bool(
                    view is not None
                    and view.selectionModel() is not None
                    and view.selectionModel().isSelected(index)
                )
                if not is_selected:
                    opt.state &= ~QtWidgets.QStyle.State_Selected
                    opt.state &= ~QtWidgets.QStyle.State_HasFocus
            except Exception:
                pass

            if reserve > 0:
                opt.rect = opt.rect.adjusted(0, 0, -int(reserve), 0)

            # Paint base content
            painter.save()
            painter.translate(-2, 0)
            super(ImportantItemDelegate, self).paint(painter, opt, index)
            painter.restore()

            # Draw right-side widgets with the required order:
            # attachment first (to the left), counter/add action at the far right.
            painter.save()
            right_edge = option.rect.right()
            top = option.rect.top()
            height = option.rect.height()

            action_rect = None
            if is_hovered:
                action_rect = self.group_add_rect(option.rect)
                self._add_icon.paint(painter, action_rect, QtCore.Qt.AlignCenter)
            elif has_count:
                count_right = right_edge - self._group_count_right_margin
                # Constrain counter area to avoid conflicting with left content/gap
                min_left = opt.rect.right() + self._group_count_left_gap
                count_width = count_w + self._group_count_extra_pad
                count_left = max(min_left, count_right - count_width)
                action_rect = QtCore.QRect(
                    count_left,
                    top,
                    max(0, count_right - count_left),
                    height
                )
                painter.setPen(self._group_count_color)
                painter.drawText(action_rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight, count_text)

            if has_attachment:
                if action_rect is not None:
                    icon_right = action_rect.left() - self._attach_spacing
                else:
                    icon_right = right_edge - self._group_count_right_margin
                icon_x = icon_right - icon_size.width()
                icon_y = top + (height - icon_size.height()) // 2
                icon_rect = QtCore.QRect(icon_x, icon_y, icon_size.width(), icon_size.height())
                self._attachment_icon.paint(painter, icon_rect, QtCore.Qt.AlignCenter)

            painter.restore()
        else:
            # Default painting for non-group rows
            super(ImportantItemDelegate, self).paint(painter, option, index)

        # Group enclosure indicator (left bar) for child rows
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
                vbar_left = max(0, child_left - (self._group_indicator_gap + bar_w))
                vbar_rect = QtCore.QRect(vbar_left, option.rect.y(), bar_w, option.rect.height())
                painter.drawRect(vbar_rect)

                painter.restore()
            except Exception:
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

                # Pinned indicator at top-right
                if is_important:
                    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
                    available = max(8, option.rect.height() - 2 * self._pin_margin)
                    pin_size = min(self._pin_icon_max_size, available)
                    x = option.rect.right() - self._pin_margin - pin_size
                    y = option.rect.top() + self._pin_margin
                    pin_rect = QtCore.QRect(x, y, pin_size, pin_size)
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

    def _paint_action_section(
            self,
            painter,
            option,
            index,
            item,
            show_icon: bool = True,
    ):
        """
        Paint an actionable section header with stable title geometry.

        For headers without secondary text (e.g. Projects) this painter is used
        in both normal and hover states so the title baseline cannot change when
        add.svg appears. For headers with right-side text (e.g. Recent), hover
        replaces that text with add.svg.
        """
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        # Keep the section title in exactly the same visual position as in
        # the non-hovered state. Some Qt styles/stylesheets alter item text
        # padding for State_MouseOver, which otherwise makes e.g. "Projects"
        # jump by a pixel when the add icon appears. The icon itself is
        # painted separately, so the native hover state is not needed here.
        opt.state &= ~QtWidgets.QStyle.State_MouseOver

        action_rect = self.section_add_rect(option.rect)
        if not action_rect.isValid():
            super(ImportantItemDelegate, self).paint(painter, opt, index)
            return

        reserve = max(
            0,
            option.rect.right() - action_rect.left() + 1 + self._group_count_left_gap,
        )
        if reserve > 0:
            opt.rect = opt.rect.adjusted(0, 0, -reserve, 0)

        opt.text = item.title
        opt.displayAlignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter

        style = opt.widget.style() if opt.widget is not None else QtWidgets.QApplication.style()
        style.drawControl(
            QtWidgets.QStyle.CE_ItemViewItem,
            opt,
            painter,
            opt.widget,
        )
        if show_icon:
            self._add_icon.paint(painter, action_rect, QtCore.Qt.AlignCenter)

    def _paint_split_section(self, painter, option, index, item, right_text=None):
        """
        Paint a section row with a full left title and a right label.

        Both labels are rendered through the native item-view style instead
        of being drawn manually. This keeps the font, disabled text color,
        vertical alignment and padding exactly the same as ordinary date
        SectionItem rows. The left section title always has priority; the
        right label is constrained to the remaining space and is elided by
        Qt when necessary.
        """
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        # Keep title/counter geometry identical while the pointer moves over
        # a collapsed section. The hover itself has no action in this state.
        opt.state &= ~QtWidgets.QStyle.State_MouseOver

        style = opt.widget.style() if opt.widget is not None else QtWidgets.QApplication.style()

        # First draw the section title exactly as a regular SectionItem would
        # be drawn, changing only its alignment from the date-row default
        # (right) to the section-header alignment (left).
        left_opt = QtWidgets.QStyleOptionViewItem(opt)
        left_opt.text = item.title
        left_opt.displayAlignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        style.drawControl(
            QtWidgets.QStyle.CE_ItemViewItem,
            left_opt,
            painter,
            left_opt.widget,
        )

        # Determine the actual text area used by the current Qt style. This
        # is important because stylesheet/platform margins can differ.
        text_rect = style.subElementRect(
            QtWidgets.QStyle.SE_ItemViewItemText,
            left_opt,
            left_opt.widget,
        )
        if not text_rect.isValid() or text_rect.width() <= 0:
            text_rect = option.rect.adjusted(2, 0, -2, 0)

        fm = QtGui.QFontMetrics(left_opt.font)
        left_width = fm.horizontalAdvance(item.title)
        gap = 12

        # Reserve the complete section title. The secondary/date label gets
        # only the remaining width and therefore elides first on narrow lists.
        right_content_left = text_rect.left() + left_width + gap
        if right_content_left >= text_rect.right():
            return

        # Plain top-level headers such as Pinned intentionally use this same
        # paint path even when they have no right-side label. Keeping the left
        # title on one painter path prevents its baseline from changing when a
        # collapsed-state counter later appears.
        resolved_right_text = item.right_text if right_text is None else str(right_text)
        if resolved_right_text is None or resolved_right_text == "":
            return

        # Use a second native item-style pass for the right label. Its outer
        # rect ends at the original row edge, so its right padding is exactly
        # the same as for a standalone right-aligned date SectionItem.
        right_opt = QtWidgets.QStyleOptionViewItem(opt)
        right_opt.text = resolved_right_text
        right_opt.displayAlignment = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        right_opt.textElideMode = QtCore.Qt.ElideRight

        # Account for the style's own left content inset when choosing the
        # sub-rect, while never allowing it to overlap the left title.
        style_left_inset = max(0, text_rect.left() - option.rect.left())
        right_outer_left = max(
            option.rect.left(),
            right_content_left - style_left_inset,
        )
        right_opt.rect = QtCore.QRect(
            right_outer_left,
            option.rect.top(),
            max(0, option.rect.right() - right_outer_left + 1),
            option.rect.height(),
        )
        if right_opt.rect.width() <= 0:
            return

        style.drawControl(
            QtWidgets.QStyle.CE_ItemViewItem,
            right_opt,
            painter,
            right_opt.widget,
        )

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
    def __init__(
            self,
            title,
            group: bool = False,
            right_text: str | None = None,
            action: str | None = None,
            section_key: str | None = None,
            section_count: int | None = None,
    ):
        super().__init__(title)
        self.title = title
        self.group = group
        self.right_text = right_text
        self.action = action
        self.section_key = section_key
        self.section_count = section_count
        self.setSelectable(False)
        self.setEnabled(False)
        self.setTextAlignment(QtCore.Qt.AlignRight)
        font = self.font()
        font.setBold(True)
        self.setFont(font)


class ShowMoreItem(SectionItem):
    """Centered expand/collapse control for capped context-list sections."""

    PINNED = 'pinned'
    PROJECTS = 'projects'
    PROJECT_CONTEXTS = 'project_contexts'

    def __init__(
            self,
            title: str,
            scope: str,
            group_id: int | None = None,
            remaining_count: int = 0,
            collapse: bool = False,
    ):
        super().__init__(title, group=group_id is not None)
        self.title = title
        self.scope = scope
        self.group_id = group_id
        self.remaining_count = int(remaining_count or 0)
        self.collapse = bool(collapse)
        self.setTextAlignment(QtCore.Qt.AlignCenter)
