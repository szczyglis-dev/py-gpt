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

        item = self.indexAt(event.pos())
        idx = item.row()

        has_file = False
        has_src = False
        has_dest = False

        if idx >= 0:
            has_file = self.window.controller.chat.attachment.has_file_by_idx(idx)
            has_src = self.window.controller.chat.attachment.has_src_by_idx(idx)
            has_dest = self.window.controller.chat.attachment.has_dest_by_idx(idx)

        actions['open'] = QAction(QIcon(":/icons/view.svg"), trans('action.open'), self)
        actions['open'].triggered.connect(
            lambda: self.action_open(event)
        )
        actions['open_dir_src'] = QAction(QIcon(":/icons/folder.svg"), trans('action.open_dir_src'), self)
        actions['open_dir_src'].triggered.connect(
            lambda: self.action_open_dir_src(event)
        )
        actions['open_dir_dest'] = QAction(QIcon(":/icons/folder.svg"), trans('action.open_dir_storage'), self)
        actions['open_dir_dest'].triggered.connect(
            lambda: self.action_open_dir_dest(event)
        )

        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event)
        )

        menu = QMenu(self)
        if has_file:
            menu.addAction(actions['open'])
        if has_src:
            menu.addAction(actions['open_dir_src'])
        if has_dest:
            menu.addAction(actions['open_dir_dest'])
        menu.addAction(actions['delete'])

        if idx >= 0:
            self.window.controller.chat.attachment.select(item.row())
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

    def action_open(self, event):
        """
        Open action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.chat.attachment.open_by_idx(idx)

    def action_open_dir_src(self, event):
        """
        Open source directory action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.chat.attachment.open_dir_src_by_idx(idx)

    def action_open_dir_dest(self, event):
        """
        Open destination directory action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.chat.attachment.open_dir_dest_by_idx(idx)
