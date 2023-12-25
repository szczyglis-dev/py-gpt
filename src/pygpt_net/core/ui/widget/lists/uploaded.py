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

from PySide6.QtGui import QAction, QIcon, QResizeEvent
from PySide6.QtWidgets import QMenu

from pygpt_net.core.ui.widget.lists.base import BaseList
from pygpt_net.core.utils import trans


class UploadedFileList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Attachments menu

        :param window: main window
        :param id: input id
        """
        super(UploadedFileList, self).__init__(window)
        self.window = window
        self.id = id
        self.doubleClicked.connect(self.dblclick)
        self.setHeaderHidden(False)

        self.header = self.header()
        self.header.setStretchLastSection(True)

        self.column_proportion = 0.5
        self.adjustColumnWidths()

    def adjustColumnWidths(self):
        total_width = self.width()
        first_column_width = int(total_width * self.column_proportion)
        self.setColumnWidth(0, first_column_width)
        for column in range(1, 2):
            self.setColumnWidth(column, (total_width - first_column_width) // (2 - 1))

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.adjustColumnWidths()

    def click(self, val):
        """
        Click event

        :param val: click event
        """
        self.window.controller.assistant_files.select_file(val.row())

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.assistant_files.select_file(val.row())

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['download'] = QAction(QIcon.fromTheme("edit-download"), trans('action.download'), self)
        actions['download'].triggered.connect(
            lambda: self.action_download(event))

        actions['rename'] = QAction(QIcon.fromTheme("edit-edit"), trans('action.rename'), self)
        actions['rename'].triggered.connect(
            lambda: self.action_rename(event))

        actions['delete'] = QAction(QIcon.fromTheme("edit-delete"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event))

        menu = QMenu(self)
        # menu.addAction(actions['download'])  # not allowed for download files with purpose: assistants :(
        menu.addAction(actions['rename'])
        menu.addAction(actions['delete'])

        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant_files.select_file(item.row())
            menu.exec_(event.globalPos())

    def action_rename(self, event):
        """
        Rename action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant_files.rename_file(idx)

    def action_download(self, event):
        """
        Download action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant_files.download_file(idx)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant_files.delete_file(idx)
