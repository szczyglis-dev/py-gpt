#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.02.01 16:00:00                  #
# ================================================== #

import datetime

from PySide6 import QtWidgets, QtCore, QtGui
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
        """
        Mouse press event
        :param event: event
        """
        index = self.indexAt(event.pos())
        if not index.isValid():
            self.window.controller.ctx.unselect()
            return
        super(BaseList, self).mousePressEvent(event)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        index = self.indexAt(event.pos())
        item = self.window.ui.models['ctx.list'].itemFromIndex(index)

        if (item is not None
                and index.isValid()
                and hasattr(item, 'id')):

            idx = item.row()
            id = item.id

            # group context menu
            if hasattr(item, 'isFolder') and item.isFolder:
                actions = {}
                actions['new'] = QAction(QIcon(":/icons/add.svg"), trans('action.ctx.new'), self)
                actions['new'].triggered.connect(
                    lambda checked=False, id=id: self.window.controller.ctx.new(force=False, group_id=id)
                )
                actions['rename'] = QAction(QIcon(":/icons/edit.svg"), trans('action.rename'), self)
                actions['rename'].triggered.connect(
                    lambda checked=False, id=id: self.window.controller.ctx.rename_group(id)
                )
                actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.group.delete.only'), self)
                actions['delete'].triggered.connect(
                    lambda checked=False, id=id: self.window.controller.ctx.delete_group(id)
                )
                actions['delete_all'] = QAction(QIcon(":/icons/delete.svg"), trans('action.group.delete.all'), self)
                actions['delete_all'].triggered.connect(
                    lambda checked=False, id=id: self.window.controller.ctx.delete_group_all(id)
                )

                menu = QMenu(self)
                menu.addAction(actions['new'])
                menu.addAction(actions['rename'])
                menu.addAction(actions['delete'])  # delete group
                menu.addAction(actions['delete_all'])  # delete group and all contexts

                if idx >= 0:
                    menu.exec_(event.globalPos())

            # children context menu
            else:
                ctx_id = id
                ctx = self.window.core.ctx.get_meta_by_id(id)
                if ctx is None:
                    return

                is_important = ctx.important

                actions = {}
                actions['rename'] = QAction(QIcon(":/icons/edit.svg"), trans('action.rename'), self)
                actions['rename'].triggered.connect(
                    lambda checked=False, ctx_id=ctx_id: self.action_rename(ctx_id)
                )

                if is_important:
                    actions['important'] = QAction(QIcon(":/icons/pin.svg"), trans('action.unpin'), self)
                    actions['important'].triggered.connect(
                        lambda checked=False, ctx_id=ctx_id: self.action_unpin(ctx_id)
                    )
                else:
                    actions['important'] = QAction(QIcon(":/icons/pin.svg"), trans('action.pin'), self)
                    actions['important'].triggered.connect(
                        lambda checked=False, ctx_id=ctx_id: self.action_pin(ctx_id)
                    )

                actions['duplicate'] = QAction(QIcon(":/icons/copy.svg"), trans('action.duplicate'), self)
                actions['duplicate'].triggered.connect(
                    lambda checked=False, ctx_id=ctx_id: self.action_duplicate(ctx_id)
                )

                actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
                actions['delete'].triggered.connect(
                    lambda checked=False, ctx_id=ctx_id: self.action_delete(ctx_id)
                )

                actions['copy_id'] = QAction(QIcon(":/icons/copy.svg"), trans('action.ctx_copy_id') + " @" + str(id), self)
                actions['copy_id'].triggered.connect(
                    lambda checked=False, ctx_id=ctx_id: self.action_copy_id(ctx_id)
                )

                actions['reset'] = QAction(QIcon(":/icons/close.svg"), trans('action.ctx_reset'), self)
                actions['reset'].triggered.connect(
                    lambda checked=False, ctx_id=ctx_id: self.action_reset(ctx_id)
                )

                menu = QMenu(self)
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
                        lambda checked=False,
                               ctx_id=ctx_id,
                               s_id=status_id: self.window.controller.ctx.set_label(ctx_id, s_id)
                    )
                    set_label_menu.addAction(status_action)

                idx_menu = QMenu(trans('action.idx'), self)

                # indexes list
                idxs = self.window.core.config.get('llama.idx.list')
                store = self.window.core.idx.get_current_store()  # get current idx store provider
                if len(idxs) > 0:
                    for index in idxs:
                        id = index['id']
                        name = index['name'] + " (" + index['id'] + ")"

                        # add to index
                        action = idx_menu.addAction("IDX: " + name)
                        action.setIcon(QIcon(":/icons/db.svg"))
                        action.triggered.connect(
                            lambda checked=False,
                                   ctx_id=ctx_id,
                                   index=id: self.action_idx(ctx_id, index)
                        )

                    # remove from index
                    if ctx.indexed is not None and ctx.indexed > 0:
                        # get list of indexes in which context is indexed
                        if store in ctx.indexes:
                            store_indexes = ctx.indexes[store]
                            idx_menu.addSeparator()
                            for store_index in store_indexes:
                                action = idx_menu.addAction(trans("action.idx.remove") + ": " + store_index)
                                action.setIcon(QIcon(":/icons/delete.svg"))
                                action.triggered.connect(
                                    lambda checked=False,
                                           store_index=store_index,
                                           ctx_id=ctx_id: self.action_idx_remove(store_index, ctx_id)  # by context meta id
                                )
                    menu.addMenu(idx_menu)

                # -----------------------------------------

                # move to group menu
                group_menu = QMenu(trans('action.move_to'), self)
                groups = self.window.core.ctx.get_groups()

                # add group
                action = group_menu.addAction(trans("action.group.new"))
                action.setIcon(QIcon(":/icons/add.svg"))
                action.triggered.connect(
                    lambda checked=False, ctx_id=ctx_id: self.window.controller.ctx.new_group(ctx_id)
                )

                # add separator if groups exists
                if len(groups) > 0:
                    group_menu.addSeparator()

                # list of groups
                for group_id in groups:
                    group = groups[group_id]
                    action = group_menu.addAction(group.name)
                    action.setIcon(QIcon(":/icons/folder_filled.svg"))
                    action.triggered.connect(
                        lambda checked=False,
                               group_id=group_id,
                               ctx_id=ctx_id: self.window.controller.ctx.move_to_group(ctx_id, group_id)
                    )

                # add separator if groups exists
                if len(groups) > 0:
                    group_menu.addSeparator()

                # if in group add remove from group
                if ctx.group_id is not None and ctx.group_id > 0:
                    group_name = str(ctx.group_id)
                    if ctx.group_id in groups:
                        group_name = groups[ctx.group_id].name
                    action = group_menu.addAction(trans("action.group.remove") + ": " + group_name)
                    action.setIcon(QIcon(":/icons/delete.svg"))
                    action.triggered.connect(
                        lambda checked=False,
                               ctx_id=ctx_id: self.window.controller.ctx.remove_from_group(ctx_id)
                    )

                menu.addMenu(group_menu)

                menu.addAction(actions['copy_id'])

                # -----------------------------------------

                # show last indexed date if available
                if ctx.indexed is not None and ctx.indexed > 0:
                    suffix = ""
                    if ctx.updated > ctx.indexed:
                        suffix = " *"
                    dt = datetime.datetime.fromtimestamp(ctx.indexed).strftime("%Y-%m-%d %H:%M")
                    action = QAction(QIcon(":/icons/clock.svg"), trans('action.ctx.indexed') + ": " + dt + suffix, self)
                    action.setEnabled(False)  # disable action, only for info
                    menu.addAction(action)

                menu.addAction(actions['reset'])

                if idx >= 0:
                    self.window.controller.ctx.select_by_id(ctx_id)
                    menu.exec_(event.globalPos())

    def action_idx(self, id: int, idx: int):
        """
        Index with llama context action handler

        :param id: context id
        :param idx: index name
        """
        self.window.controller.idx.indexer.index_ctx_meta(id, idx)

    def action_idx_remove(self, idx: str, meta_id: int):
        """
        Remove from index action handler

        :param idx: index id
        :param meta_id: meta id
        """
        self.window.controller.idx.indexer.index_ctx_meta_remove(idx, meta_id)

    def action_rename(self, id):
        """
        Rename action handler

        :param id: context id
        """
        self.window.controller.ctx.rename(id)

    def action_pin(self, id):
        """
        Pin action handler

        :param id: context id
        """
        self.window.controller.ctx.set_important(id, True)

    def action_unpin(self, id):
        """
        Unpin action handler

        :param id: context id
        """
        self.window.controller.ctx.set_important(id, False)

    def action_important(self, id):
        """
        Set as important action handler

        :param id: context id
        """
        self.window.controller.ctx.set_important(id)

    def action_duplicate(self, id):
        """
        Rename duplicate handler

        :param id: context id
        """
        self.window.controller.ctx.common.duplicate(id)

    def action_delete(self, id):
        """
        Delete action handler

        :param id: context id
        """
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
        self.window.controller.ctx.common.reset(id)


class ImportantItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    Label color delegate

    :param QtWidgets.QStyledItemDelegate: parent class
    """
    def paint(self, painter, option, index):
        if index.parent().isValid():
            option.rect.adjust(15, 0, 0, 0)

        super(ImportantItemDelegate, self).paint(painter, option, index)

        # pin (>= 10)
        if index.data(QtCore.Qt.ItemDataRole.UserRole):
            data = index.data(QtCore.Qt.ItemDataRole.UserRole)
            label = 0
            is_important = False
            is_attachment = False
            is_group = False
            in_group = False

            if "label" in data:
                label = data["label"]
            if "is_important" in data and data["is_important"]:
                is_important = True
            if "is_attachment" in data and data["is_attachment"]:
                is_attachment = True
            if "is_group" in data and data["is_group"]:
                is_group = True
            if "in_group" in data and data["in_group"]:
                in_group = True

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

            # label (0-9)
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
        """
        Get color for status

        :param status: status id
        :return: color
        """
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
        if status in statuses:
            return statuses[status]['color']
        else:
            return statuses[0]['color']

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
        if self.group:
            self.setTextAlignment(QtCore.Qt.AlignRight)
        else:
            self.setTextAlignment(QtCore.Qt.AlignRight)
        font = self.font()
        font.setBold(True)
        self.setFont(font)
