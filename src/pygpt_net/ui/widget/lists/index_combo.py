#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.25 04:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu

from pygpt_net.utils import trans
from .base_combo import BaseCombo

class IndexCombo(BaseCombo):
    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Index select combobox

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(IndexCombo, self).__init__(window, parent_id, id, option)

    def on_combo_change(self, index):
        """
        On combo change

        :param index: combo index
        :return:
        """
        self.current_id = self.combo.itemData(index)
        self.window.controller.idx.select_by_id(self.current_id)

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: event
        """
        if event.button() == Qt.RightButton:
            self.on_context_menu(self, event.pos())
        else:
            super().mousePressEvent(event)

    def on_context_menu(self, parent, pos):
        """
        Context menu event

        :param parent: parent widget
        :param pos: position
        """
        actions = {}
        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('action.edit'), self)
        actions['edit'].triggered.connect(
            lambda: self.action_edit()
        )

        txt = trans('idx.index_now') + ': ' + trans('settings.llama.extra.btn.idx_db_all')
        actions['idx_db_all'] = QAction(QIcon(":/icons/db.svg"), txt, self)
        actions['idx_db_all'].triggered.connect(
            lambda: self.action_idx_db_all()
        )

        txt = trans('idx.index_now') + ': ' + trans('settings.llama.extra.btn.idx_db_update')
        actions['idx_db_update'] = QAction(QIcon(":/icons/db.svg"), txt, self)
        actions['idx_db_update'].triggered.connect(
            lambda: self.action_idx_db_update()
        )

        txt = trans('idx.index_now') + ': ' + trans('settings.llama.extra.btn.idx_files_all')
        actions['idx_files_all'] = QAction(QIcon(":/icons/db.svg"), txt, self)
        actions['idx_files_all'].triggered.connect(
            lambda: self.action_idx_files_all()
        )

        actions['clear'] = QAction(QIcon(":/icons/close.svg"), trans('idx.btn.clear'), self)
        actions['clear'].triggered.connect(
            lambda: self.action_clear()
        )

        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('idx.btn.truncate'), self)
        actions['delete'].triggered.connect(
            lambda: self.action_truncate()
        )

        menu = QMenu(self)
        menu.addAction(actions['edit'])
        menu.addAction(actions['idx_db_all'])
        menu.addAction(actions['idx_db_update'])
        menu.addAction(actions['idx_files_all'])
        menu.addAction(actions['clear'])
        menu.addAction(actions['delete'])
        menu.exec_(parent.mapToGlobal(pos))

    def action_idx_db_all(self):
        """Idx action handler"""
        if self.current_id is not None:
            self.window.controller.idx.indexer.index_ctx_from_ts(self.current_id, 0)

    def action_idx_db_update(self):
        """Idx action handler"""
        if self.current_id is not None:
            self.window.controller.idx.indexer.index_ctx_current(self.current_id)

    def action_idx_files_all(self):
        """Idx action handler"""
        if self.current_id is not None:
            self.window.controller.idx.indexer.index_all_files(self.current_id)

    def action_edit(self):
        """Edit action handler"""
        if self.current_id is not None:
            self.window.controller.settings.open_section('llama-index')

    def action_clear(self):
        """Clear idx action handler"""
        if self.current_id is not None:
            self.window.controller.idx.indexer.clear(self.current_id)

    def action_truncate(self):
        """Truncate idx action handler"""
        if self.current_id is not None:
            self.window.controller.idx.indexer.clear(self.current_id)