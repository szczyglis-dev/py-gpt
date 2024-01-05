#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 21:00:00                  #
# ================================================== #
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans


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
        actions['edit'] = QAction(QIcon.fromTheme("edit-edit"), trans('action.edit'), self)
        actions['edit'].triggered.connect(
            lambda: self.window.controller.settings.toggle_file_editor('models.json'))

        menu = QMenu(self)
        menu.addAction(actions['edit'])

        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            # self.window.controller.mode.select(self.id, item.row())
            menu.exec_(event.globalPos())
