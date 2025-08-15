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
    _ICO_EDIT = QIcon(":/icons/edit.svg")
    _ICO_COPY = QIcon(":/icons/copy.svg")
    _ICO_UNDO = QIcon(":/icons/undo.svg")
    _ICO_DELETE = QIcon(":/icons/delete.svg")
    _ICO_CHECK = QIcon(":/icons/check.svg")
    _ICO_CLOSE = QIcon(":/icons/close.svg")

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
        row = val.row()
        if row >= 0:
            self.window.controller.presets.select(row)
            self.selection = self.selectionModel().selection()

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        row = val.row()
        if row >= 0:
            self.window.controller.presets.editor.edit(row)

    def show_context_menu(self, pos: QPoint):
        """
        Context menu event

        :param pos: QPoint
        """
        global_pos = self.viewport().mapToGlobal(pos)
        mode = self.window.core.config.get('mode')
        index = self.indexAt(pos)
        idx = index.row()

        preset = None
        if idx >= 0:
            preset_id = self.window.core.presets.get_by_idx(idx, mode)
            if preset_id:
                preset = self.window.core.presets.items.get(preset_id)

        is_current = idx >= 0 and self.window.controller.presets.is_current(idx)

        if idx >= 0:
            menu = QMenu(self)

            edit_act = QAction(self._ICO_EDIT, trans('preset.action.edit'), menu)
            edit_act.triggered.connect(lambda checked=False, it=index: self.action_edit(it))
            menu.addAction(edit_act)

            if mode == MODE_EXPERT and preset and not preset.filename.startswith("current."):
                if not preset.enabled:
                    enable_act = QAction(self._ICO_CHECK, trans('preset.action.enable'), menu)
                    enable_act.triggered.connect(lambda checked=False, it=index: self.action_enable(it))
                    menu.addAction(enable_act)
                else:
                    disable_act = QAction(self._ICO_CLOSE, trans('preset.action.disable'), menu)
                    disable_act.triggered.connect(lambda checked=False, it=index: self.action_disable(it))
                    menu.addAction(disable_act)

            duplicate_act = QAction(self._ICO_COPY, trans('preset.action.duplicate'), menu)
            duplicate_act.triggered.connect(lambda checked=False, it=index: self.action_duplicate(it))

            if is_current:
                edit_act.setEnabled(False)
                restore_act = QAction(self._ICO_UNDO, trans('dialog.editor.btn.defaults'), menu)
                restore_act.triggered.connect(lambda checked=False, it=index: self.action_restore(it))
                menu.addAction(restore_act)
                menu.addAction(duplicate_act)
            else:
                delete_act = QAction(self._ICO_DELETE, trans('preset.action.delete'), menu)
                delete_act.triggered.connect(lambda checked=False, it=index: self.action_delete(it))
                menu.addAction(duplicate_act)
                menu.addAction(delete_act)

            self.selection = self.selectionModel().selection()
            menu.exec_(global_pos)

        # store previous scroll position
        self.store_scroll_position()

        # restore selection if it was backed up
        if self.restore_after_ctx_menu:
            if self._backup_selection is not None:
                sel_model = self.selectionModel()
                sel_model.clearSelection()
                for i in self._backup_selection:
                    sel_model.select(
                        i, QItemSelectionModel.Select | QItemSelectionModel.Rows
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
                sel_model = self.selectionModel()
                self._backup_selection = list(sel_model.selectedIndexes())
                sel_model.clearSelection()
                sel_model.select(
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