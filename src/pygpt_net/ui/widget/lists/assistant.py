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


class AssistantList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Presets select menu

        :param window: main window
        :param id: input id
        """
        super(AssistantList, self).__init__(window)
        self.window = window
        self.id = id

        self.doubleClicked.connect(self.dblclick)

    def click(self, val):
        self.window.controller.assistant.select(val.row())

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.assistant.editor.edit(val.row())

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('assistant.action.edit'), self)
        actions['edit'].triggered.connect(
            lambda: self.action_edit(event))

        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('assistant.action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event))

        menu = QMenu(self)
        menu.addAction(actions['edit'])
        menu.addAction(actions['delete'])

        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant.select(item.row())
            menu.exec_(event.globalPos())

    def action_edit(self, event):
        """
        Edit action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant.editor.edit(idx)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant.delete(idx)
