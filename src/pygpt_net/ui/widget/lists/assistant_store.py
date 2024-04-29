#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.29 16:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class AssistantVectorStoreEditorList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Store select menu (in editor)

        :param window: main window
        :param id: parent id
        """
        super(AssistantVectorStoreEditorList, self).__init__(window)
        self.window = window
        self.id = id

    def click(self, val):
        idx = val.row()
        self.window.controller.assistant.store.select(idx)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['refresh'] = QAction(QIcon(":/icons/reload.svg"),
                                      trans('dialog.assistant.store.menu.current.refresh_store'),
                                      self)
        actions['refresh'].triggered.connect(
            lambda: self.action_refresh(event))

        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event))

        actions['clear'] = QAction(QIcon(":/icons/close.svg"), trans('dialog.assistant.store.menu.current.clear_files'), self)
        actions['clear'].triggered.connect(
            lambda: self.action_clear(event))

        actions['truncate'] = QAction(QIcon(":/icons/delete.svg"), trans('dialog.assistant.store.menu.current.truncate_files'),
                                   self)
        actions['truncate'].triggered.connect(
            lambda: self.action_truncate(event))

        menu = QMenu(self)
        menu.addAction(actions['refresh'])
        menu.addAction(actions['delete'])
        menu.addAction(actions['clear'])
        menu.addAction(actions['truncate'])

        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            menu.exec_(event.globalPos())

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant.store.delete_by_idx(idx)

    def action_clear(self, event):
        """
        Clear action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant.batch.clear_store_files_by_idx(idx)

    def action_truncate(self, event):
        """
        Truncate action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant.batch.truncate_store_files_by_idx(idx)

    def action_refresh(self, event):
        """
        Refresh action handler
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant.store.refresh_by_idx(idx)

