#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 21:00:00                  #
# ================================================== #
import os

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtGui import QAction, QIcon, QColor
from PySide6.QtWidgets import QMenu

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans


class ContextList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Presets select menu

        :param window: main window
        :param id: input id
        """
        super(ContextList, self).__init__(window)
        self.window = window
        self.id = id

        self.doubleClicked.connect(self.dblclick)
        self.setItemDelegate(ImportantItemDelegate())

    def click(self, val):
        """
        Click event

        :param val: click event
        """
        self.window.controller.ctx.select_by_idx(val.row())

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.ctx.select_by_idx(val.row())

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        item = self.indexAt(event.pos())
        idx = item.row()

        actions = {}
        actions['rename'] = QAction(QIcon.fromTheme("edit-edit"), trans('action.rename'), self)
        actions['rename'].triggered.connect(
            lambda: self.action_rename(event))

        actions['delete'] = QAction(QIcon.fromTheme("edit-delete"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event))

        menu = QMenu(self)
        menu.addAction(actions['rename'])
        menu.addAction(actions['delete'])

        # set label menu
        set_label_menu = menu.addMenu(trans('calendar.day.label'))
        for status_id, status_info in self.window.controller.calendar.statuses.items():
            name = trans('calendar.day.' + status_info['label'])
            if status_id == 0:
                name = '-'
            status_action = QAction(name, self)
            status_action.triggered.connect(
                lambda checked=False, s_id=status_id: self.window.controller.ctx.set_label(idx, s_id))
            set_label_menu.addAction(status_action)

        idx_menu = QMenu(trans('action.idx'), self)

        # indexes list
        idxs = self.window.core.config.get('llama.idx.list')
        if len(idxs) > 0:
            for index in idxs:
                id = index['id']
                name = index['name'] + " (" + index['id'] + ")"
                action = idx_menu.addAction("IDX: " + name)
                action.triggered.connect(lambda checked=False, idx=idx, index=id:
                                         self.action_idx(idx, index))

            menu.addMenu(idx_menu)

        if idx >= 0:
            self.window.controller.ctx.select_by_idx(item.row())
            menu.exec_(event.globalPos())

    def action_idx(self, ctx_idx, idx):
        """
        Index with llama context action handler

        :param ctx_idx: row idx in context list
        :param idx: index id
        """
        self.window.controller.idx.indexer.index_ctx_meta(ctx_idx, idx)

    def action_rename(self, event):
        """
        Rename action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.ctx.rename(idx)

    def action_important(self, event):
        """
        Set as important action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.ctx.set_important(idx)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.ctx.delete(idx)


class ImportantItemDelegate(QtWidgets.QStyledItemDelegate):
    """
    Label color delegate
    """
    def paint(self, painter, option, index):
        super(ImportantItemDelegate, self).paint(painter, option, index)
        if index.data(QtCore.Qt.ItemDataRole.UserRole) > 0:
            color = self.get_color_for_status(index.data(QtCore.Qt.ItemDataRole.UserRole))
            square_size = 5
            square_margin = 0
            square_rect = QtCore.QRect(option.rect.left() + square_margin, option.rect.center().y() - (square_size / 2)
                                       + 2, square_size, square_size)

            painter.save()
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
