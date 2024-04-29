#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.29 16:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QPushButton, QMenu

from pygpt_net.utils import trans


class ContextMenuButton(QPushButton):
    def __init__(self, title, parent=None, action=None):
        super().__init__(title, parent)
        self.action = action

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton or event.button() == Qt.RightButton:
            self.action(self, event.pos())
        else:
            super().mousePressEvent(event)


class NewCtxButton(QPushButton):
    def __init__(self, title: str = None, window=None):
        super().__init__(title)
        self.window = window
        self.clicked.connect(
            lambda: self.window.controller.ctx.new()
        )

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
        group_id = self.window.controller.ctx.group_id
        menu = QMenu(self)
        actions = {}
        actions['new'] = QAction(QIcon(":/icons/add.svg"), trans('action.ctx.new'), self)
        actions['new'].triggered.connect(
            lambda: self.window.controller.ctx.new_ungrouped()
        )
        if group_id is not None and group_id > 0:
            group_name = self.window.controller.ctx.get_group_name(group_id)
            actions['new_in_group'] = QAction(QIcon(":/icons/add.svg"), trans('action.ctx.new.in_group').format(group=group_name), self)
            actions['new_in_group'].triggered.connect(
                lambda checked=False, id=group_id: self.window.controller.ctx.new(force=False, group_id=id)
            )
        actions['new_group'] = QAction(QIcon(":/icons/folder_filled.svg"), trans('menu.file.group.new'), self)
        actions['new_group'].triggered.connect(
            lambda: self.window.controller.ctx.new_group()
        )

        if group_id is not None and group_id > 0:
            menu.addAction(actions['new_in_group'])
        menu.addAction(actions['new'])
        menu.addAction(actions['new_group'])
        menu.exec_(parent.mapToGlobal(pos))


class SyncButton(QPushButton):
    def __init__(self, title: str = None, window=None):
        super().__init__(title)
        self.window = window
        self.clicked.connect(
            lambda: self.window.controller.assistant.batch.import_files_current()
        )

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
        menu = QMenu(self)
        actions = {}
        actions['current'] = QAction(QIcon(":/icons/download.svg"), trans('attachments_uploaded.btn.sync.current'), self)
        actions['current'].triggered.connect(
            lambda: self.window.controller.assistant.batch.import_files_current()
        )
        actions['all'] = QAction(QIcon(":/icons/download.svg"), trans('attachments_uploaded.btn.sync.all'), self)
        actions['all'].triggered.connect(
            lambda: self.window.controller.assistant.batch.import_files()
        )
        menu.addAction(actions['current'])
        menu.addAction(actions['all'])
        menu.exec_(parent.mapToGlobal(pos))