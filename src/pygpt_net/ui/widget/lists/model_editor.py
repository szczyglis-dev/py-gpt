#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.29 14:00:00                  #
# ================================================== #
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class ModelEditorList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Model select menu (in editor)

        :param window: main window
        :param id: parent id
        """
        super(ModelEditorList, self).__init__(window)
        self.window = window
        self.id = id

    def click(self, val):
        idx = val.row()
        self.window.controller.model.editor.select(idx)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event))

        menu = QMenu(self)
        menu.addAction(actions['delete'])

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
            self.window.controller.model.editor.delete_by_idx(idx)

