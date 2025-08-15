#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 03:00:00                  #
# ================================================== #

from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QResizeEvent, QImage
from PySide6.QtWidgets import QMenu, QApplication

from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class AttachmentList(BaseList):
    _ICON_VIEW = QIcon(":/icons/view.svg")
    _ICON_FOLDER = QIcon(":/icons/folder_filled.svg")
    _ICON_EDIT = QIcon(":/icons/edit.svg")
    _ICON_DELETE = QIcon(":/icons/delete.svg")

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

        hdr = self.header()
        hdr.setStretchLastSection(False)

        self.column_proportion = 0.3
        self._last_width = -1
        self.adjustColumnWidths()

    def adjustColumnWidths(self):
        hdr = self.header()
        cols = hdr.count()
        if cols <= 0:
            return
        total_width = self.viewport().width() or self.width()
        first_column_width = int(total_width * self.column_proportion)
        remaining = max(total_width - first_column_width, 0)
        if self.columnWidth(0) != first_column_width:
            self.setColumnWidth(0, first_column_width)
        if cols > 1:
            other = remaining // (cols - 1)
            for column in range(1, cols):
                if self.columnWidth(column) != other:
                    self.setColumnWidth(column, other)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        w = event.size().width()
        if w != self._last_width:
            self._last_width = w
            self.adjustColumnWidths()

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: mouse event
        """
        if event.button() == Qt.LeftButton:
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
        if idx < 0:
            return

        attachment = self.window.controller.attachment.get_by_idx(mode, idx)
        path = attachment.path if attachment else None

        menu = QMenu(self)

        actions = {}
        actions['open'] = QAction(self._ICON_VIEW, trans('action.open'), menu)
        actions['open'].triggered.connect(partial(self._action_open_idx, idx))

        actions['open_dir'] = QAction(self._ICON_FOLDER, trans('action.open_dir'), menu)
        actions['open_dir'].triggered.connect(partial(self._action_open_dir_idx, idx))

        actions['rename'] = QAction(self._ICON_EDIT, trans('action.rename'), menu)
        actions['rename'].triggered.connect(partial(self._action_rename_idx, idx))

        actions['delete'] = QAction(self._ICON_DELETE, trans('action.delete'), menu)
        actions['delete'].triggered.connect(partial(self._action_delete_idx, idx))

        if attachment and attachment.type == AttachmentItem.TYPE_FILE:
            fs_actions = self.window.core.filesystem.actions
            if fs_actions.has_preview(path):
                preview_actions = fs_actions.get_preview(self, path)
                for preview_action in preview_actions or []:
                    try:
                        preview_action.setParent(menu)
                    except Exception:
                        pass
                    menu.addAction(preview_action)

            menu.addAction(actions['open'])
            menu.addAction(actions['open_dir'])

            if fs_actions.has_use(path):
                use_actions = fs_actions.get_use(self, path)
                use_menu = QMenu(trans('action.use'), menu)
                for use_action in use_actions or []:
                    try:
                        use_action.setParent(use_menu)
                    except Exception:
                        pass
                    use_menu.addAction(use_action)
                menu.addMenu(use_menu)

            menu.addAction(actions['rename'])

        menu.addAction(actions['delete'])

        self.window.controller.attachment.select(mode, item.row())
        menu.exec_(event.globalPos())

    def keyPressEvent(self, event):
        """
        Key press event to handle undo action

        :param event: Event
        """
        if event.key() == Qt.Key_V and (event.modifiers() & Qt.ControlModifier):
            self.handle_paste()

    def handle_paste(self):
        """Handle clipboard paste"""
        clipboard = QApplication.clipboard()
        source = clipboard.mimeData()
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage):
                self.window.controller.attachment.from_clipboard_image(image)
            return
        if source.hasUrls():
            urls = source.urls()
            for url in urls:
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    self.window.controller.attachment.from_clipboard_url(local_path, all=True)
            return
        if source.hasText():
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

    def _action_open_idx(self, idx, checked=False):
        if idx >= 0:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.open(mode, idx)

    def _action_open_dir_idx(self, idx, checked=False):
        if idx >= 0:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.open_dir(mode, idx)

    def _action_rename_idx(self, idx, checked=False):
        if idx >= 0:
            mode = self.window.core.config.get('mode')
            self.window.controller.attachment.rename(mode, idx)

    def _action_delete_idx(self, idx, checked=False):
        if idx >= 0:
            self.window.controller.attachment.delete(idx)