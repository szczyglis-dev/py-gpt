#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.23 00:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon, QResizeEvent, Qt
from PySide6.QtWidgets import QMenu

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class AttachmentCtxList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Ctx Attachments menu

        :param window: main window
        :param id: input id
        """
        super(AttachmentCtxList, self).__init__(window)
        self.window = window
        self.id = id
        self.doubleClicked.connect(self.dblclick)
        self.setHeaderHidden(False)
        self.clicked.disconnect(self.click)

        self.header = self.header()
        self.header.setStretchLastSection(False)

        self.column_proportion = 0.3
        self.adjustColumnWidths()

    def adjustColumnWidths(self):
        total_width = self.width()
        first_column_width = int(total_width * self.column_proportion)
        self.setColumnWidth(0, first_column_width)
        for column in range(1, 4):
            self.setColumnWidth(column, (total_width - first_column_width) // (4 - 1))

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.adjustColumnWidths()

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: mouse event
        """
        if event.buttons() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                self.window.controller.assistant.files.select(index.row())
        super(AttachmentCtxList, self).mousePressEvent(event)

    def click(self, val):
        """
        Click event

        :param val: click event
        """
        pass

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.assistant.files.select(val.row())

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}

        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event)
        )

        menu = QMenu(self)
        menu.addAction(actions['delete'])

        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant.files.select(item.row())
            menu.exec_(event.globalPos())

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.chat.attachment.delete_by_idx(idx)
