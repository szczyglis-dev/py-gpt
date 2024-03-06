#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.06 22:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class PresetPluginsList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Preset plugins menu (in editor)

        :param window: main window
        :param id: parent id
        """
        super(PresetPluginsList, self).__init__(window)
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
        actions['rename'] = QAction(QIcon(":/icons/edit.svg"), trans('action.rename'), self)
        actions['rename'].triggered.connect(
            lambda: self.action_rename(event))
        actions['duplicate'] = QAction(QIcon(":/icons/copy.svg"), trans('action.duplicate'), self)
        actions['duplicate'].triggered.connect(
            lambda: self.action_duplicate(event))
        actions['reset'] = QAction(QIcon(":/icons/close.svg"), trans('action.reset'), self)
        actions['reset'].triggered.connect(
            lambda: self.action_reset(event))
        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event))

        menu = QMenu(self)
        menu.addAction(actions['use'])
        menu.addAction(actions['rename'])
        menu.addAction(actions['duplicate'])
        menu.addAction(actions['reset'])
        menu.addAction(actions['delete'])

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
            self.window.controller.plugins.presets.select_by_idx(idx)

    def action_duplicate(self, event):
        """
        Duplicate action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.plugins.presets.duplicate_by_idx(idx)

    def action_reset(self, event):
        """
        Reset action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.plugins.presets.reset_by_idx(idx)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.plugins.presets.delete_by_idx(idx)

    def action_rename(self, event):
        """
        Rename action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.plugins.presets.rename_by_idx(idx)

