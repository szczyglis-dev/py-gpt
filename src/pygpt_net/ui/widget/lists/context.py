#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.15 22:00:00                  #
# ================================================== #

import datetime
import functools

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, QPoint, QItemSelectionModel
from PySide6.QtGui import QIcon, QColor, QPixmap, QStandardItem
from PySide6.QtWidgets import QMenu

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
            'pin': QIcon(":/icons/pin.svg"),
            'clock': QIcon(":/icons/clock.svg"),
            'db': QIcon(":/icons/db.svg"),
            'folder': QIcon(":/icons/folder_filled.svg"),
            'attachment': QIcon(":/icons/attachment.svg"),
        }
        self._color_icon_cache = {}

        # Use a custom delegate for labels/pinned/attachment indicators and group border indicator
        self.setItemDelegate(ImportantItemDelegate(self, self._icons['attachment']))

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

    def click(self, index):
        """
        Click event (override, connected in BaseList class)

        :param index: index
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
            if not index.isValid():
                self.window.controller.ctx.unselect()
                return
            super().mousePressEvent(event)
        elif event.button() == Qt.RightButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                sel = self.selectionModel()
                self._backup_selection = list(sel.selectedIndexes())
                sel.clearSelection()
                sel.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
            event.accept()
        else:
            super().mousePressEvent(event)

    def show_context_menu(self, pos: QPoint):
        """
        Context menu event

        :param pos: QPoint
        """
        global_pos = self.viewport().mapToGlobal(pos)
        index = self.indexAt(pos)
        item = self._model.itemFromIndex(index)

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

    def action_open(self, id: int, idx: int = None):
        """
        Open context action handler

        :param id: context id
        :param idx: index id (optional)
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.load(id, select_idx=idx)

    def action_open_new_tab(self, id: int, idx: int = None):
        """
        Open context action handler in nowej karcie

        :param id: context id
        :param idx: index id (optional)
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.load(id, select_idx=idx, new_tab=True)

    def action_idx(self, id: int, idx: int):
        """
        Index with llama context action handler

        :param id: context id
        :param idx: index name
        """
        self.restore_after_ctx_menu = False
        self.window.controller.idx.indexer.index_ctx_meta(id, idx)

    def action_idx_remove(self, idx: str, meta_id: int):
        """
        Remove from index action handler

        :param idx: index id
        :param meta_id: meta id
        """
        self.restore_after_ctx_menu = False
        self.window.controller.idx.indexer.index_ctx_meta_remove(idx, meta_id)

    def action_rename(self, id):
        """
        Rename action handler

        :param id: context id
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.rename(id)

    def action_pin(self, id):
        """
        Pin action handler

        :param id: context id
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.set_important(id, True)

    def action_unpin(self, id):
        """
        Unpin action handler

        :param id: context id
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.set_important(id, False)

    def action_important(self, id):
        """
        Set as important action handler

        :param id: context id
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.set_important(id)

    def action_duplicate(self, id):
        """
        Duplicate handler

        :param id: context id
        """
        self.window.controller.ctx.common.duplicate(id)

    def action_delete(self, id):
        """
        Delete action handler

        :param id: context id
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.delete(id)

    def action_copy_id(self, id):
        """
        Copy ID tag action handler

        :param id: context id
        """
        self.window.controller.ctx.common.copy_id(id)

    def action_reset(self, id):
        """
        Reset action handler

        :param id: context id
        """
        self.restore_after_ctx_menu = False
        self.window.controller.ctx.common.reset(id)

    def action_set_label(self, id: int, label: int):
        """
        Set label action handler

        :param id: context id
        :param label: label id
        """
        self.window.controller.ctx.set_label(id, label)

    def selectionCommand(self, index, event=None):
        """
        Selection command
        :param index: Index
        :param event: Event
        """
        return super().selectionCommand(index, event)


class ImportantItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    Item delegate that paints:
    - Attachment icon on the right side (centered vertically),
    - Pinned indicator (small circle) in the top-right corner (overlays if needed),
    - Label color as a full-height vertical bar on the left for labeled items,
    - Group enclosure indicator for expanded groups:
        - thin vertical bar (default 2 px) on the left side of child rows area,
        - thin horizontal bar (default 2 px) at the bottom of the last child row.
    """
    def __init__(self, parent=None, attachment_icon: QIcon = None):
        super().__init__(parent)
        self._attachment_icon = attachment_icon or QIcon(":/icons/attachment.svg")

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
        self._pin_pen = QtGui.QPen(QtCore.Qt.black, 0.5, QtCore.Qt.SolidLine)
        self._pin_diameter = 4            # Small pinned circle diameter
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

                # Pinned indicator (small circle) kept at a fixed top-right position.
                # It does not shift left when the attachment is present; it overlays above it.
                if is_important:
                    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
                    color = self.get_color_for_status(3)

                    x = option.rect.x() + option.rect.width() - self._pin_margin - self._pin_diameter
                    y = option.rect.y() + self._pin_margin
                    pin_rect = QtCore.QRect(x, y, self._pin_diameter, self._pin_diameter)

                    painter.setBrush(color)
                    painter.setPen(self._pin_pen)
                    painter.drawEllipse(pin_rect)

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