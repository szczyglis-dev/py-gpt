#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.09 23:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class ProfileList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Profile menu (in editor)

        :param window: main window
        :param id: parent id
        """
        super(ProfileList, self).__init__(window)
        self.window = window
        self.id = id

    def click(self, val):
        pass

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['use'] = QAction(QIcon(":/icons/check.svg"), trans('action.use'), self)
        actions['use'].triggered.connect(
            lambda: self.action_use(event))
        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('action.edit'), self)
        actions['edit'].triggered.connect(
            lambda: self.action_edit(event))
        actions['duplicate'] = QAction(QIcon(":/icons/copy.svg"), trans('action.duplicate'), self)
        actions['duplicate'].triggered.connect(
            lambda: self.action_duplicate(event))


        actions['reset'] = QAction(QIcon(":/icons/close.svg"), trans('action.reset'), self)
        actions['reset'].triggered.connect(
            lambda: self.action_reset(event))
        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.profile.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event))
        actions['delete_all'] = QAction(QIcon(":/icons/delete.svg"), trans('action.profile.delete_all'), self)
        actions['delete_all'].triggered.connect(
            lambda: self.action_delete_all(event))

        menu = QMenu(self)
        menu.addAction(actions['edit'])
        menu.addAction(actions['use'])
        menu.addAction(actions['duplicate'])
        menu.addAction(actions['reset'])
        menu.addAction(actions['delete'])
        menu.addAction(actions['delete_all'])

        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            menu.exec_(event.globalPos())

    def action_use(self, event):
        """
        Use action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.settings.profile.select_by_idx(idx)

    def action_duplicate(self, event):
        """
        Duplicate action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.settings.profile.duplicate_by_idx(idx)

    def action_reset(self, event):
        """
        Reset action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.settings.profile.reset_by_idx(idx)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.settings.profile.delete_by_idx(idx)

    def action_delete_all(self, event):
        """
        Delete all action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.settings.profile.delete_all_by_idx(idx)

    def action_edit(self, event):
        """
        Edit action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.settings.profile.edit_by_idx(idx)

