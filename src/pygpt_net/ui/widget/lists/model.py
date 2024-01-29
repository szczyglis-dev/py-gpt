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


class ModelList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Presets select menu

        :param window: main window
        :param id: input id
        """
        super(ModelList, self).__init__(window)
        self.window = window
        self.id = id

    def click(self, val):
        self.window.controller.model.select(val.row())
        self.selection = self.selectionModel().selection()

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('action.edit'), self)
        actions['edit'].triggered.connect(
            lambda: self.action_edit(event))

        menu = QMenu(self)
        menu.addAction(actions['edit'])

        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            menu.exec_(event.globalPos())

    def action_edit(self, event):
        """
        Edit action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.model.editor.open_by_idx(idx)
