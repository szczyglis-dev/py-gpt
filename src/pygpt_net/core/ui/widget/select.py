#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.08 22:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QTreeView, QAbstractItemView, QMenu

from ...utils import trans


class SelectMenu(QTreeView):
    NAME = range(1)  # list of columns

    def __init__(self, window=None, id=None):
        """
        Select menu

        :param window: main window
        :param id: input id
        """
        super(SelectMenu, self).__init__(window)
        self.window = window
        self.id = id
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setIndentation(0)
        self.setHeaderHidden(True)

        self.clicked.connect(self.click)

    def click(self, val):
        self.window.controller.model.select(self.id, val.row())


class PresetSelectMenu(SelectMenu):
    def __init__(self, window=None, id=None):
        """
        Presets select menu

        :param window: main window
        :param id: input id
        """
        super(PresetSelectMenu, self).__init__(window)
        self.window = window
        self.id = id

        self.doubleClicked.connect(self.dblclick)

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.presets.edit(val.row())

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['edit'] = QAction(QIcon.fromTheme("edit-edit"), trans('preset.action.edit'), self)
        actions['edit'].triggered.connect(
            lambda: self.action_edit(event))

        actions['duplicate'] = QAction(QIcon.fromTheme("edit-copy"), trans('preset.action.duplicate'), self)
        actions['duplicate'].triggered.connect(
            lambda: self.action_duplicate(event))

        actions['delete'] = QAction(QIcon.fromTheme("edit-delete"), trans('preset.action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event))

        menu = QMenu(self)
        menu.addAction(actions['edit'])
        menu.addAction(actions['duplicate'])
        menu.addAction(actions['delete'])

        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 1:
            # self.window.controller.model.select(self.id, item.row())
            menu.exec_(event.globalPos())

    def action_edit(self, event):
        """
        Edit action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.presets.edit(idx)

    def action_duplicate(self, event):
        """
        Duplicate action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.presets.duplicate(idx)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.presets.delete(idx)


class AssistantSelectMenu(SelectMenu):
    def __init__(self, window=None, id=None):
        """
        Presets select menu

        :param window: main window
        :param id: input id
        """
        super(AssistantSelectMenu, self).__init__(window)
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
        self.window.controller.assistant.edit(val.row())

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['edit'] = QAction(QIcon.fromTheme("edit-edit"), trans('assistant.action.edit'), self)
        actions['edit'].triggered.connect(
            lambda: self.action_edit(event))

        actions['delete'] = QAction(QIcon.fromTheme("edit-delete"), trans('assistant.action.delete'), self)
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
            self.window.controller.assistant.edit(idx)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant.delete(idx)


class ContextSelectMenu(SelectMenu):
    def __init__(self, window=None, id=None):
        """
        Presets select menu

        :param window: main window
        :param id: input id
        """
        super(ContextSelectMenu, self).__init__(window)
        self.window = window
        self.id = id

        self.doubleClicked.connect(self.dblclick)

    def click(self, val):
        """
        Click event

        :param val: click event
        """
        self.window.controller.context.select(val.row())

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.context.select(val.row())

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['rename'] = QAction(QIcon.fromTheme("edit-edit"), trans('action.rename'), self)
        actions['rename'].triggered.connect(
            lambda: self.action_rename(event))

        actions['delete'] = QAction(QIcon.fromTheme("edit-delete"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event))

        menu = QMenu(self)
        menu.addAction(actions['rename'])
        menu.addAction(actions['delete'])

        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.context.select(item.row())
            menu.exec_(event.globalPos())

    def action_rename(self, event):
        """
        Rename action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.context.rename(idx)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.context.delete(idx)


class AttachmentSelectMenu(SelectMenu):
    def __init__(self, window=None, id=None):
        """
        Attachments menu

        :param window: main window
        :param id: input id
        """
        super(AttachmentSelectMenu, self).__init__(window)
        self.window = window
        self.id = id
        self.doubleClicked.connect(self.dblclick)
        self.setHeaderHidden(False)

    def click(self, val):
        """
        Click event

        :param val: click event
        """
        mode = self.window.config.data['mode']
        self.window.controller.attachment.select(mode, val.row())

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        mode = self.window.config.data['mode']
        self.window.controller.attachment.select(mode, val.row())

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['open_dir'] = QAction(QIcon.fromTheme("system-file-manager"), trans('action.open_dir'), self)
        actions['open_dir'].triggered.connect(
            lambda: self.action_open_dir(event))

        actions['rename'] = QAction(QIcon.fromTheme("edit-edit"), trans('action.rename'), self)
        actions['rename'].triggered.connect(
            lambda: self.action_rename(event))

        actions['delete'] = QAction(QIcon.fromTheme("edit-delete"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event))

        menu = QMenu(self)
        menu.addAction(actions['rename'])
        menu.addAction(actions['open_dir'])
        menu.addAction(actions['delete'])

        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            mode = self.window.config.data['mode']
            self.window.controller.attachment.select(mode, item.row())
            menu.exec_(event.globalPos())

    def action_open_dir(self, event):
        """
        Open dir action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            mode = self.window.config.data['mode']
            self.window.controller.attachment.open_dir(mode, idx)

    def action_rename(self, event):
        """
        Rename action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            mode = self.window.config.data['mode']
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


class AttachmentUploadedSelectMenu(SelectMenu):
    def __init__(self, window=None, id=None):
        """
        Attachments menu

        :param window: main window
        :param id: input id
        """
        super(AttachmentUploadedSelectMenu, self).__init__(window)
        self.window = window
        self.id = id
        self.doubleClicked.connect(self.dblclick)
        self.setHeaderHidden(False)

    def click(self, val):
        """
        Click event

        :param val: click event
        """
        self.window.controller.assistant.select_file(val.row())

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.assistant.select_file(val.row())

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['rename'] = QAction(QIcon.fromTheme("edit-edit"), trans('action.rename'), self)
        actions['rename'].triggered.connect(
            lambda: self.action_rename(event))

        actions['delete'] = QAction(QIcon.fromTheme("edit-delete"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_delete(event))

        menu = QMenu(self)
        menu.addAction(actions['rename'])
        menu.addAction(actions['delete'])

        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant.select_file(item.row())
            menu.exec_(event.globalPos())

    def action_rename(self, event):
        """
        Rename action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant.rename_file(idx)

    def action_delete(self, event):
        """
        Delete action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.assistant.delete_file(idx)
