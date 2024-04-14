#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.14 21:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QResizeEvent, QImage
from PySide6.QtWidgets import QMenu, QApplication, QHeaderView

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class AttachmentList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Attachments menu

        :param window: main window
        :param id: input id
        """
        super(AttachmentList, self).__init__(window)
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
        for column in range(1, 3):
            self.setColumnWidth(column, (total_width - first_column_width) // (3 - 1))

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
                mode = self.window.core.config.get('mode')
                self.window.controller.attachment.select(mode, index.row())
        super(AttachmentList, self).mousePressEvent(event)

    def click(self, val):
        """
        Click event

        :param val: click event
        """
        return

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        mode = self.window.core.config.get('mode')
        self.window.controller.attachment.select(mode, val.row())

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        mode = self.window.core.config.get('mode')
        item = self.indexAt(event.pos())
        idx = item.row()
        preview_actions = []
        path = None

        if idx >= 0:
            path = self.window.controller.attachment.get_path_by_idx(mode, idx)
            preview_actions = []
            if self.window.core.filesystem.actions.has_preview(path):
                preview_actions = self.window.core.filesystem.actions.get_preview(self, path)

        actions = {}
        actions['open'] = QAction(QIcon(":/icons/view.svg"), trans('action.open'), self)
        actions['open'].triggered.connect(
            lambda: self.action_open(event))

        actions['open_dir'] = QAction(QIcon(":/icons/folder_filled.svg"), trans('action.open_dir'), self)
        actions['open_dir'].triggered.connect(
            lambda: self.action_open_dir(event))

        actions['rename'] = QAction(QIcon(":/icons/edit.svg"), trans('action.rename'), self)
        actions['rename'].triggered.connect(
            lambda: self.action_rename(event))

        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event))

        menu = QMenu(self)
        if idx >= 0 and preview_actions:
            for action in preview_actions:
                menu.addAction(action)
        menu.addAction(actions['open'])
        menu.addAction(actions['open_dir'])

        if idx >= 0:
            if self.window.core.filesystem.actions.has_use(path):
                use_actions = self.window.core.filesystem.actions.get_use(self, path)
                use_menu = QMenu(trans('action.use'), self)
                for action in use_actions:
                    use_menu.addAction(action)
                menu.addMenu(use_menu)

        menu.addAction(actions['rename'])
        menu.addAction(actions['delete'])

        if idx >= 0:
            self.window.controller.attachment.select(mode, item.row())
            menu.exec_(event.globalPos())

    def keyPressEvent(self, event):
        """
        Key press event to handle undo action

        :param event: Event
        """
        if event.key() == Qt.Key_V and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.handle_paste()

    def handle_paste(self):
        """Handle clipboard paste"""
        clipboard = QApplication.clipboard()
        source = clipboard.mimeData()
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage):
                self.window.controller.attachment.from_clipboard_image(image)
        elif source.hasUrls():
            urls = source.urls()
            for url in urls:
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    self.window.controller.attachment.from_clipboard_url(local_path, all=True)
        elif source.hasText():
            text = source.text()
            self.window.controller.attachment.from_clipboard_text(text, all=True)

    def action_open(self, event):
        """
        Open action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.open(mode, idx)

    def action_open_dir(self, event):
        """
        Open dir action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.open_dir(mode, idx)

    def action_rename(self, event):
        """
        Rename action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.rename(mode, idx)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.attachment.delete(idx)
