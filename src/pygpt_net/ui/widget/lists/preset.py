#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.19 17:00:00                  #
# ================================================== #

from PySide6.QtCore import QPoint, QItemSelectionModel
from PySide6.QtGui import QAction, QIcon, Qt
from PySide6.QtWidgets import QMenu

from pygpt_net.core.types import (
    MODE_EXPERT,
)
from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class PresetList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Presets select menu

        :param window: main window
        :param id: input id
        """
        super(PresetList, self).__init__(window)
        self.window = window
        self.id = id

        self.doubleClicked.connect(self.dblclick)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self._backup_selection = None
        self.restore_after_ctx_menu = True

    def click(self, val):
        self.window.controller.presets.select(val.row())
        self.selection = self.selectionModel().selection()

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.presets.editor.edit(val.row())

    def show_context_menu(self, pos: QPoint):
        """
        Context menu event

        :param pos: QPoint
        """
        global_pos = self.viewport().mapToGlobal(pos)
        mode = self.window.core.config.get('mode')
        item = self.indexAt(pos)
        idx = item.row()

        preset = None
        preset_id = self.window.core.presets.get_by_idx(idx, mode)
        if preset_id is not None and preset_id != "":
            if preset_id in self.window.core.presets.items:
                preset = self.window.core.presets.items[preset_id]

        actions = {}

        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('preset.action.edit'), self)
        actions['edit'].triggered.connect(
            lambda checked=False, item=item: self.action_edit(item))

        actions['duplicate'] = QAction(QIcon(":/icons/copy.svg"), trans('preset.action.duplicate'), self)
        actions['duplicate'].triggered.connect(
            lambda checked=False, item=item: self.action_duplicate(item))

        if self.window.controller.presets.is_current(idx):
            actions['restore'] = QAction(QIcon(":/icons/undo.svg"), trans('dialog.editor.btn.defaults'), self)
            actions['restore'].triggered.connect(
                lambda checked=False, item=item: self.action_restore(item))
        else:
            actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('preset.action.delete'), self)
            actions['delete'].triggered.connect(
                lambda checked=False, item=item: self.action_delete(item))

        menu = QMenu(self)
        menu.addAction(actions['edit'])
        if mode == MODE_EXPERT:
            if not preset.filename.startswith("current."):
                if not preset.enabled:
                    actions['enable'] = QAction(QIcon(":/icons/check.svg"), trans('preset.action.enable'), self)
                    actions['enable'].triggered.connect(
                        lambda checked=False, item=item: self.action_enable(item))
                    menu.addAction(actions['enable'])
                else:
                    actions['disable'] = QAction(QIcon(":/icons/close.svg"), trans('preset.action.disable'), self)
                    actions['disable'].triggered.connect(
                        lambda checked=False, item=item: self.action_disable(item))
                    menu.addAction(actions['disable'])
        if self.window.controller.presets.is_current(idx):
            actions['edit'].setEnabled(False)
            menu.addAction(actions['restore'])
            menu.addAction(actions['duplicate'])
        else:
            menu.addAction(actions['duplicate'])
            menu.addAction(actions['delete'])

        if idx >= 0:
            #self.window.controller.presets.select(idx)
            self.selection = self.selectionModel().selection()
            # self.window.controller.mode.select(self.id, item.row())
            menu.exec_(global_pos)

        # store previous scroll position
        self.store_scroll_position()

        # restore selection if it was backed up
        if self.restore_after_ctx_menu:
            if self._backup_selection is not None:
                self.selectionModel().clearSelection()
                for idx in self._backup_selection:
                    self.selectionModel().select(
                        idx, QItemSelectionModel.Select | QItemSelectionModel.Rows
                    )
                self._backup_selection = None

        # restore scroll position
        self.restore_after_ctx_menu = True
        self.restore_scroll_position()

    def action_edit(self, item):
        """
        Edit action handler

        :param item: list item
        """
        idx = item.row()
        if idx >= 0:
            self.restore_after_ctx_menu = False  # do not restore selection after context menu
            self.window.controller.presets.editor.edit(idx)

    def action_duplicate(self, item):
        """
        Duplicate action handler

        :param item: list item
        """
        idx = item.row()
        if idx >= 0:
            self.restore_after_ctx_menu = False  # do not restore selection after context menu
            self.window.controller.presets.duplicate(idx)

    def action_delete(self, item):
        """
        Delete action handler

       :param item: list item
        """
        idx = item.row()
        if idx >= 0:
            self.restore_after_ctx_menu = False  # do not restore selection after context menu
            self.window.controller.presets.delete(idx)

    def action_restore(self, item):
        """
        Restore action handler

        :param item: list item
        """
        self.window.controller.presets.restore()


    def action_enable(self, item):
        """
        Enable action handler

        :param item: list item
        """
        idx = item.row()
        if idx >= 0:
            self.window.controller.presets.enable(idx)


    def action_disable(self, item):
        """
        Disable action handler

        :param item: list item
        """
        idx = item.row()
        if idx >= 0:
            self.window.controller.presets.disable(idx)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            if not index.isValid():
                return
            super().mousePressEvent(event)
        elif event.button() == Qt.RightButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                self._backup_selection = list(self.selectionModel().selectedIndexes())
                self.selectionModel().clearSelection()
                self.selectionModel().select(
                    index, QItemSelectionModel.Select | QItemSelectionModel.Rows
                )
            event.accept()
        else:
            super().mousePressEvent(event)

    def selectionCommand(self, index, event=None):
        """
        Selection command
        :param index: Index
        :param event: Event
        """
        return super().selectionCommand(index, event)
