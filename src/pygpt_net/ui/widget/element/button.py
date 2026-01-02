#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 19:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QMenu

from pygpt_net.utils import trans


class ContextMenuButton(QPushButton):
    def __init__(self, title, parent=None, action=None):
        super().__init__(title, parent)
        self.action = action

    def mousePressEvent(self, event):
        btn = event.button()
        if btn == Qt.LeftButton or btn == Qt.RightButton:
            self.action(self, event.pos())
        else:
            super().mousePressEvent(event)


class NewCtxButton(QPushButton):
    _icon_add = None
    _icon_folder_filled = None

    def __init__(self, title: str = None, window=None):
        super().__init__(title)
        self.window = window
        self.clicked.connect(
            lambda: self.window.controller.ctx.new()
        )

    @classmethod
    def _ensure_icons(cls):
        if cls._icon_add is None:
            cls._icon_add = QIcon(":/icons/add.svg")
            cls._icon_folder_filled = QIcon(":/icons/folder_filled.svg")

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.new_context_menu(self, event.pos())
        else:
            super().mousePressEvent(event)

    def new_context_menu(self, parent, pos):
        """
        Index all btn context menu

        :param parent: parent widget
        :param pos: mouse  position
        """
        type(self)._ensure_icons()
        group_id = self.window.controller.ctx.group_id
        menu = QMenu(parent)
        if group_id is not None and group_id > 0:
            group_name = self.window.controller.ctx.get_group_name(group_id)
            act_new_in_group = menu.addAction(type(self)._icon_add, trans('action.ctx.new.in_group').format(group=group_name))
            act_new_in_group.triggered.connect(
                lambda checked=False, id=group_id: self.window.controller.ctx.new(force=False, group_id=id)
            )
        act_new = menu.addAction(type(self)._icon_add, trans('action.ctx.new'))
        act_new.triggered.connect(
            lambda checked=False: self.window.controller.ctx.new_ungrouped()
        )
        act_new_group = menu.addAction(type(self)._icon_folder_filled, trans('menu.file.group.new'))
        act_new_group.triggered.connect(
            lambda checked=False: self.window.controller.ctx.new_group()
        )
        menu.exec_(parent.mapToGlobal(pos))
        menu.deleteLater()


class SyncButton(QPushButton):
    _icon_download = None

    def __init__(self, title: str = None, window=None):
        super().__init__(title)
        self.window = window
        self.clicked.connect(
            lambda: self.window.controller.remote_store.openai.batch.import_files_current()
        )

    @classmethod
    def _ensure_icons(cls):
        if cls._icon_download is None:
            cls._icon_download = QIcon(":/icons/download.svg")

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.new_context_menu(self, event.pos())
        else:
            super().mousePressEvent(event)

    def new_context_menu(self, parent, pos):
        """
        Index all btn context menu

        :param parent: parent widget
        :param pos: mouse  position
        """
        type(self)._ensure_icons()
        menu = QMenu(parent)
        act_current = menu.addAction(type(self)._icon_download, trans('attachments_uploaded.btn.sync.current'))
        act_current.triggered.connect(
            lambda checked=False: self.window.controller.remote_store.openai.batch.import_files_current()
        )
        act_all = menu.addAction(type(self)._icon_download, trans('attachments_uploaded.btn.sync.all'))
        act_all.triggered.connect(
            lambda checked=False: self.window.controller.remote_store.openai.batch.import_files()
        )
        menu.exec_(parent.mapToGlobal(pos))
        menu.deleteLater()