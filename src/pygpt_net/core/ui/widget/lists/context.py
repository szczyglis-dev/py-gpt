#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 18:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu

from pygpt_net.core.ui.widget.lists.base import BaseList
from pygpt_net.core.utils import trans


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

        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.ctx.select_by_idx(item.row())
            menu.exec_(event.globalPos())

    def action_rename(self, event):
        """
        Rename action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.ctx.rename(idx)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.ctx.delete(idx)
