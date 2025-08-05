#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt    #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.20 23:00:00                  #
# ================================================== #

import datetime
import functools

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtCore import Qt, QPoint, QItemSelectionModel
from PySide6.QtGui import QAction, QIcon, QColor, QPixmap, QStandardItem
from PySide6.QtWidgets import QMenu
from overrides import overrides

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc


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
        self.setItemDelegate(ImportantItemDelegate())
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self._backup_selection = None
        self.restore_after_ctx_menu = True

    def click(self, index):
        """
        Click event (override, connected in BaseList class)

        :param index: index
        """
        item = self.window.ui.models['ctx.list'].itemFromIndex(index)
        if item is not None:
            if not hasattr(item, 'isFolder'):
                return
            if item.isFolder:
                self.window.controller.ctx.set_group(item.id)
                if self.window.ui.nodes['ctx.list'].isExpanded(index):
                    self.expanded_items.discard(item.id)
                    self.window.ui.nodes['ctx.list'].collapse(index)
                else:
                    self.expanded_items.add(item.id)
                    self.window.ui.nodes['ctx.list'].expand(index)
            else:
                self.window.controller.ctx.select_by_id(item.id)
        else:
            pass  # unselected

    def expand_group(self, id):
        """
        Expand group

        :param id: group id
        """
        for i in range(self.window.ui.models['ctx.list'].rowCount()):
            item = self.window.ui.models['ctx.list'].item(i)
            if isinstance(item, GroupItem):
                if item.id == id:
                    index = self.window.ui.models['ctx.list'].indexFromItem(item)
                    self.window.ui.nodes['ctx.list'].expand(index)
                    self.expanded_items.add(id)

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
                self._backup_selection = list(self.selectionModel().selectedIndexes())
                self.selectionModel().clearSelection()
                self.selectionModel().select(
                    index, QItemSelectionModel.Select | QItemSelectionModel.Rows
                )
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
        item = self.window.ui.models['ctx.list'].itemFromIndex(index)

        if (item is not None
                and index.isValid()
                and hasattr(item, 'id')):

            idx = item.row()
            id_value = item.id

            # group context menu
            if hasattr(item, 'isFolder') and item.isFolder:
                actions = {}
                actions['new'] = QAction(QIcon(":/icons/add.svg"), trans('action.ctx.new'), self)
                actions['new'].triggered.connect(
                    functools.partial(self.window.controller.ctx.new, force=False, group_id=id_value)
                )
                actions['rename'] = QAction(QIcon(":/icons/edit.svg"), trans('action.rename'), self)
                actions['rename'].triggered.connect(
                    functools.partial(self.window.controller.ctx.rename_group, id_value)
                )
                actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.group.delete.only'), self)
                actions['delete'].triggered.connect(
                    functools.partial(self.window.controller.ctx.delete_group, id_value)
                )
                actions['delete_all'] = QAction(QIcon(":/icons/delete.svg"), trans('action.group.delete.all'), self)
                actions['delete_all'].triggered.connect(
                    functools.partial(self.window.controller.ctx.delete_group_all, id_value)
                )

                menu = QMenu(self)
                menu.addAction(actions['new'])
                menu.addAction(actions['rename'])
                menu.addAction(actions['delete'])
                menu.addAction(actions['delete_all'])

                if idx >= 0:
                    menu.exec_(global_pos)

            # children context menu
            else:
                ctx_id = id_value
                ctx = self.window.core.ctx.get_meta_by_id(ctx_id)
                if ctx is None:
                    return

                is_important = ctx.important

                actions = {}
                actions['open'] = QAction(QIcon(":/icons/chat.svg"), trans('action.open'), self)
                actions['open'].triggered.connect(
                    functools.partial(self.action_open, ctx_id, idx)
                )

                actions['open_new_tab'] = QAction(QIcon(":/icons/chat.svg"), trans('action.open_new_tab'), self)
                actions['open_new_tab'].triggered.connect(
                    functools.partial(self.action_open_new_tab, ctx_id, idx)
                )

                actions['rename'] = QAction(QIcon(":/icons/edit.svg"), trans('action.rename'), self)
                actions['rename'].triggered.connect(
                    functools.partial(self.action_rename, ctx_id)
                )

                if is_important:
                    actions['important'] = QAction(QIcon(":/icons/pin.svg"), trans('action.unpin'), self)
                    actions['important'].triggered.connect(
                        functools.partial(self.action_unpin, ctx_id)
                    )
                else:
                    actions['important'] = QAction(QIcon(":/icons/pin.svg"), trans('action.pin'), self)
                    actions['important'].triggered.connect(
                        functools.partial(self.action_pin, ctx_id)
                    )

                actions['duplicate'] = QAction(QIcon(":/icons/copy.svg"), trans('action.duplicate'), self)
                actions['duplicate'].triggered.connect(
                    functools.partial(self.action_duplicate, ctx_id)
                )

                actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
                actions['delete'].triggered.connect(
                    functools.partial(self.action_delete, ctx_id)
                )

                actions['copy_id'] = QAction(QIcon(":/icons/copy.svg"), trans('action.ctx_copy_id') + " @" + str(ctx_id), self)
                actions['copy_id'].triggered.connect(
                    functools.partial(self.action_copy_id, ctx_id)
                )

                actions['reset'] = QAction(QIcon(":/icons/close.svg"), trans('action.ctx_reset'), self)
                actions['reset'].triggered.connect(
                    functools.partial(self.action_reset, ctx_id)
                )

                menu = QMenu(self)
                menu.addAction(actions['open'])
                menu.addAction(actions['open_new_tab'])
                menu.addAction(actions['rename'])
                menu.addAction(actions['duplicate'])
                menu.addAction(actions['important'])
                menu.addAction(actions['delete'])

                # set label menu
                colors = self.window.controller.ui.get_colors()
                set_label_menu = menu.addMenu(trans('calendar.day.label'))
                for status_id, status_info in colors.items():
                    name = trans('calendar.day.' + status_info['label'])
                    if status_id == 0:
                        name = '-'
                    color = status_info['color']
                    pixmap = QPixmap(16, 16)
                    pixmap.fill(color)
                    icon = QIcon(pixmap)
                    status_action = QAction(icon, name, self)
                    status_action.triggered.connect(
                        functools.partial(self.window.controller.ctx.set_label, ctx_id, status_id)
                    )
                    set_label_menu.addAction(status_action)

                idx_menu = QMenu(trans('action.idx'), self)

                # indexes list
                idxs = self.window.core.config.get('llama.idx.list')
                store = self.window.core.idx.get_current_store()  # get current idx store provider
                if len(idxs) > 0:
                    for idx_dict in idxs:
                        index_id = idx_dict['id']
                        name = idx_dict['name'] + " (" + idx_dict['id'] + ")"
                        action = idx_menu.addAction("IDX: " + name)
                        action.setIcon(QIcon(":/icons/db.svg"))
                        action.triggered.connect(
                            functools.partial(self.action_idx, ctx_id, index_id)
                        )

                    # remove from index
                    if ctx.indexed is not None and ctx.indexed > 0:
                        if store in ctx.indexes:
                            store_indexes = ctx.indexes[store]
                            idx_menu.addSeparator()
                            for store_index in store_indexes:
                                action = idx_menu.addAction(trans("action.idx.remove") + ": " + store_index)
                                action.setIcon(QIcon(":/icons/delete.svg"))
                                action.triggered.connect(
                                    functools.partial(self.action_idx_remove, store_index, ctx_id)
                                )
                    menu.addMenu(idx_menu)

                # move to group menu
                group_menu = QMenu(trans('action.move_to'), self)
                groups = self.window.core.ctx.get_groups()

                # add group
                action = group_menu.addAction(trans("action.group.new"))
                action.setIcon(QIcon(":/icons/add.svg"))
                action.triggered.connect(
                    functools.partial(self.window.controller.ctx.new_group, ctx_id)
                )

                if len(groups) > 0:
                    group_menu.addSeparator()

                for group_id, group in groups.items():
                    action = group_menu.addAction(group.name)
                    action.setIcon(QIcon(":/icons/folder_filled.svg"))
                    action.triggered.connect(
                        functools.partial(self.window.controller.ctx.move_to_group, ctx_id, group_id)
                    )

                if len(groups) > 0:
                    group_menu.addSeparator()

                if ctx.group_id is not None and ctx.group_id > 0:
                    group_name = str(ctx.group_id)
                    if ctx.group_id in groups:
                        group_name = groups[ctx.group_id].name
                    action = group_menu.addAction(trans("action.group.remove") + ": " + group_name)
                    action.setIcon(QIcon(":/icons/delete.svg"))
                    action.triggered.connect(
                        functools.partial(self.window.controller.ctx.remove_from_group, ctx_id)
                    )

                menu.addMenu(group_menu)

                menu.addAction(actions['copy_id'])

                # show last indexed date if available
                if ctx.indexed is not None and ctx.indexed > 0:
                    suffix = ""
                    if ctx.updated > ctx.indexed:
                        suffix = " *"
                    dt = datetime.datetime.fromtimestamp(ctx.indexed).strftime("%Y-%m-%d %H:%M")
                    action = QAction(QIcon(":/icons/clock.svg"), trans('action.ctx.indexed') + ": " + dt + suffix, self)
                    action.setEnabled(False)
                    menu.addAction(action)

                menu.addAction(actions['reset'])

                if idx >= 0:
                    self.window.controller.ctx.set_selected(ctx_id)
                    menu.exec_(global_pos)

        self.store_scroll_position()

        if self.restore_after_ctx_menu:
            if self._backup_selection is not None:
                self.selectionModel().clearSelection()
                for sel_idx in self._backup_selection:
                    self.selectionModel().select(
                        sel_idx, QItemSelectionModel.Select | QItemSelectionModel.Rows
                    )
                self._backup_selection = None

        self.restore_after_ctx_menu = True
        self.restore_scroll_position()

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

    def selectionCommand(self, index, event=None):
        """
        Selection command
        :param index: Index
        :param event: Event
        """
        return super().selectionCommand(index, event)


class ImportantItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    Label color delegate
    """
    def paint(self, painter, option, index):
        if index.parent().isValid():
            option.rect.adjust(15, 0, 0, 0)

        super(ImportantItemDelegate, self).paint(painter, option, index)

        if index.data(QtCore.Qt.ItemDataRole.UserRole):
            data = index.data(QtCore.Qt.ItemDataRole.UserRole)
            label = data.get("label", 0)
            is_important = data.get("is_important", False)
            is_attachment = data.get("is_attachment", False)

            painter.save()

            if is_attachment:
                icon = QtGui.QIcon(":/icons/attachment.svg")
                icon_size = option.decorationSize or QtCore.QSize(16, 16)
                icon_pos = option.rect.right() - icon_size.width()
                icon_rect = QtCore.QRect(
                    icon_pos,
                    option.rect.top() + (option.rect.height() - icon_size.height()) / 2,
                    icon_size.width(),
                    icon_size.height()
                )
                icon.paint(painter, icon_rect, QtCore.Qt.AlignCenter)

            if is_important:
                color = self.get_color_for_status(3)
                square_size = 3
                square_margin = 0
                square_rect = QtCore.QRect(
                    option.rect.left() + square_margin,
                    option.rect.top() + 2,
                    square_size,
                    square_size,
                )
                painter.setBrush(color)
                painter.setPen(
                    QtGui.QPen(
                        QtCore.Qt.black,
                        0.5,
                        QtCore.Qt.SolidLine,
                    )
                )
                painter.drawRect(square_rect)

            if label > 0:
                color = self.get_color_for_status(label)
                square_size = 5
                square_margin = 0
                square_rect = QtCore.QRect(
                    option.rect.left() + square_margin,
                    option.rect.center().y() - (square_size / 2) + 2,
                    square_size,
                    square_size,
                )
                painter.setBrush(color)
                painter.setPen(QtCore.Qt.NoPen)
                painter.drawRect(square_rect)

            painter.restore()

    def get_color_for_status(self, status: int) -> QColor:
        statuses = {
            0: {'label': 'label.color.default', 'color': QColor(100, 100, 100)},
            1: {'label': 'label.color.red', 'color': QColor(255, 0, 0)},
            2: {'label': 'label.color.orange', 'color': QColor(255, 165, 0)},
            3: {'label': 'label.color.yellow', 'color': QColor(255, 255, 0)},
            4: {'label': 'label.color.green', 'color': QColor(0, 255, 0)},
            5: {'label': 'label.color.blue', 'color': QColor(0, 0, 255)},
            6: {'label': 'label.color.indigo', 'color': QColor(75, 0, 130)},
            7: {'label': 'label.color.violet', 'color': QColor(238, 130, 238)},
        }
        return statuses.get(status, statuses[0])['color']


class GroupItem(QStandardItem):
    def __init__(self, icon, name, id):
        super().__init__(icon, name)
        self.id = id
        self.name = name
        self.isFolder = True
        self.isPinned = False
        self.hasAttachments = False
        self.dt = None


class Item(QStandardItem):
    def __init__(self, name, id):
        super().__init__(name)
        self.id = id
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