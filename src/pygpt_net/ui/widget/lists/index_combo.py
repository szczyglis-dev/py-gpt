#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.27 14:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QHBoxLayout, QWidget, QComboBox, QMenu

from pygpt_net.ui.widget.option.combo import NoScrollCombo
from pygpt_net.utils import trans

class IndexCombo(QWidget):
    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Index select combobox

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(IndexCombo, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option
        self.value = None
        self.keys = []
        self.title = ""
        self.real_time = False
        self.combo = NoScrollCombo()
        self.combo.currentIndexChanged.connect(self.on_combo_change)
        self.current_id = None

        # add items
        self.update()

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.combo)
        self.setLayout(self.layout)
        self.fit_to_content()

    def update(self):
        """Prepare items"""
        # init from option data
        if self.option is not None:
            if "label" in self.option and self.option["label"] is not None and self.option["label"] != "":
                self.title = trans(self.option["label"])
            if "keys" in self.option:
                self.keys = self.option["keys"]
            if "value" in self.option:
                self.value = self.option["value"]
                self.current_id = self.value
            if "real_time" in self.option:
                self.real_time = self.option["real_time"]

        # add items
        if type(self.keys) is list:
            for item in self.keys:
                if type(item) is dict:
                    for key, value in item.items():
                        self.combo.addItem(value, key)
                else:
                    self.combo.addItem(item, item)

    def set_value(self, value):
        """
        Set value

        :param value: value
        """
        index = self.combo.findData(value)
        if index != -1:
            self.combo.setCurrentIndex(index)

    def get_value(self):
        """
        Get value

        :return: value
        """
        return self.current_id

    def set_keys(self, keys):
        """
        Set keys

        :param keys: keys
        """
        self.keys = keys
        self.option["keys"] = keys
        self.combo.clear()
        self.update()

    def on_combo_change(self, index):
        """
        On combo change

        :param index: combo index
        :return:
        """
        self.current_id = self.combo.itemData(index)
        self.window.controller.idx.select_by_id(self.current_id)

    def fit_to_content(self):
        """Fit to content"""
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)

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