#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.16 18:35:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMenu

from pygpt_net.utils import trans


class AgentEditorList(QListWidget):
    def __init__(self, window=None, parent=None):
        super().__init__(parent or window)
        self.window = window
        self.itemClicked.connect(self._on_click)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    @staticmethod
    def _agent_id(item: QListWidgetItem) -> str:
        return str(item.data(Qt.UserRole) or "") if item is not None else ""

    def make_item(self, agent_id: str, name: str, built_in: bool) -> QListWidgetItem:
        label = str(name or agent_id)
        if built_in:
            label += f" ({trans('agents.editor.builtin.badge')})"
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, str(agent_id))
        item.setData(Qt.UserRole + 1, bool(built_in))
        return item

    def _on_click(self, item: QListWidgetItem):
        self.window.controller.agents_v2.editor.select(self._agent_id(item))

    def _context_menu(self, pos: QPoint):
        item = self.itemAt(pos)
        if item is None:
            return
        self.setCurrentItem(item)
        agent_id = self._agent_id(item)
        built_in = bool(item.data(Qt.UserRole + 1))
        menu = QMenu(self)
        action_delete = QAction(QIcon(":/icons/delete.svg"), trans("action.delete"), menu)
        action_delete.setEnabled(not built_in)
        action_delete.triggered.connect(
            lambda checked=False, aid=agent_id: self.window.controller.agents_v2.editor.delete(aid)
        )
        menu.addAction(action_delete)
        menu.exec(self.viewport().mapToGlobal(pos))
