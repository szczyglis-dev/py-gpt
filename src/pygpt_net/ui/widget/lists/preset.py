#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.21 20:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
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

    def click(self, val):
        self.window.controller.presets.select(val.row())
        self.selection = self.selectionModel().selection()

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.presets.editor.edit(val.row())

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        mode = self.window.core.config.get('mode')
        item = self.indexAt(event.pos())
        idx = item.row()

        preset = None
        preset_id = self.window.core.presets.get_by_idx(idx, mode)
        if preset_id is not None and preset_id != "":
            if preset_id in self.window.core.presets.items:
                preset = self.window.core.presets.items[preset_id]

        actions = {}

        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('preset.action.edit'), self)
        actions['edit'].triggered.connect(
            lambda: self.action_edit(event))

        actions['duplicate'] = QAction(QIcon(":/icons/copy.svg"), trans('preset.action.duplicate'), self)
        actions['duplicate'].triggered.connect(
            lambda: self.action_duplicate(event))

        if self.window.controller.presets.is_current(idx):
            actions['restore'] = QAction(QIcon(":/icons/undo.svg"), trans('dialog.editor.btn.defaults'), self)
            actions['restore'].triggered.connect(
                lambda: self.action_restore(event))
        else:
            actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('preset.action.delete'), self)
            actions['delete'].triggered.connect(
                lambda: self.action_delete(event))

        menu = QMenu(self)
        menu.addAction(actions['edit'])
        if mode == MODE_EXPERT:
            if not preset.filename.startswith("current."):
                if not preset.enabled:
                    actions['enable'] = QAction(QIcon(":/icons/check.svg"), trans('preset.action.enable'), self)
                    actions['enable'].triggered.connect(
                        lambda: self.action_enable(event))
                    menu.addAction(actions['enable'])
                else:
                    actions['disable'] = QAction(QIcon(":/icons/close.svg"), trans('preset.action.disable'), self)
                    actions['disable'].triggered.connect(
                        lambda: self.action_disable(event))
                    menu.addAction(actions['disable'])
        if self.window.controller.presets.is_current(idx):
            actions['edit'].setEnabled(False)
            menu.addAction(actions['restore'])
            menu.addAction(actions['duplicate'])
        else:
            menu.addAction(actions['duplicate'])
            menu.addAction(actions['delete'])

        if idx >= 0:
            self.window.controller.presets.select(idx)
            self.selection = self.selectionModel().selection()
            # self.window.controller.mode.select(self.id, item.row())
            menu.exec_(event.globalPos())

    def action_edit(self, event):
        """
        Edit action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.presets.editor.edit(idx)

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

    def action_restore(self, event):
        """
        Restore action handler

        :param event: mouse event
        """
        self.window.controller.presets.restore()


    def action_enable(self, event):
        """
        Enable action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.presets.enable(idx)


    def action_disable(self, event):
        """
        Disable action handler

        :param event: mouse event
        """
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            self.window.controller.presets.disable(idx)
