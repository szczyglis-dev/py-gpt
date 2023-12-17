#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 19:00:00                  #
# ================================================== #
from PySide6.QtCore import QItemSelectionModel
from PySide6.QtGui import QAction, QIcon, QResizeEvent
from PySide6.QtWidgets import QTreeView, QAbstractItemView, QMenu

from ...utils import trans


class SelectMenu(QTreeView):
    NAME = range(1)  # list of columns

    def __init__(self, window=None, id=None):
        """
        Select menu

        :param window: Window instance
        :param id: input id
        """
        super(SelectMenu, self).__init__(window)
        self.window = window
        self.id = id
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setIndentation(0)
        self.selection_locked = None
        self.selection = None
        self.unlocked = False
        self.clicked.connect(self.click)
        self.header().hide()

    def click(self, val):
        self.window.controller.model.select(self.id, val.row())
        self.selection = self.selectionModel().selection()

    def lockSelection(self, selected, deselected):
        if self.selection is not None:
            self.selectionModel().select(self.selection, QItemSelectionModel.Select)

    def backup_selection(self):
        self.selection = self.selectionModel().selection()

    def restore_selection(self):
        if self.selection is not None:
            self.selectionModel().select(self.selection, QItemSelectionModel.Select)

    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        super(SelectMenu, self).mousePressEvent(event)

    def focusOutEvent(self, event):
        pass

    def selectionCommand(self, index, event=None):
        """
        Selection command
        :param index: Index
        :param event: Event
        """
        # check tmp unlock
        if self.unlocked:
            return super().selectionCommand(index, event)

        if self.selection_locked is not None and self.selection_locked():
            return QItemSelectionModel.NoUpdate
        return super().selectionCommand(index, event)


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
        self.window.controller.context.select_by_idx(val.row())

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.context.select_by_idx(val.row())

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
            self.window.controller.context.select_by_idx(item.row())
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
        mode = self.window.config.get('mode')
        self.window.controller.attachment.select(mode, val.row())

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        mode = self.window.config.get('mode')
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
            mode = self.window.config.get('mode')
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
            mode = self.window.config.get('mode')
            self.window.controller.attachment.open_dir(mode, idx)

    def action_rename(self, event):
        """
        Rename action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            mode = self.window.config.get('mode')
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
