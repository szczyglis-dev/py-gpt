#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction, QIcon, Qt, QStandardItemModel
from PySide6.QtWidgets import QMenu, QVBoxLayout, QPushButton, QWidget

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans


class AgentsWidget:
    def __init__(self, window=None, tool=None):
        """
        Agents select widget

        :param window: main window
        :param tool: tool instance
        """
        self.window = window
        self.tool = tool
        self.id = "agent.builder.list"
        self.list = None

    def setup(self):
        """
        Setup agents list widget

        :return: QWidget
        """
        new_btn = QPushButton(QIcon(":/icons/add.svg"), "")
        new_btn.clicked.connect(self.action_new)

        self.list = AgentsList(self.window, tool=self.tool, id=self.id)
        layout = QVBoxLayout()
        layout.addWidget(new_btn)
        layout.addWidget(self.list)

        self.window.ui.models[self.id] = self.create_model(self.window)
        self.list.setModel(self.window.ui.models[self.id])

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def action_new(self):
        """
        New agent action
        """
        self.tool.add_agent()

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create list model
        :param parent: parent widget
        :return: QStandardItemModel
        """
        return QStandardItemModel(0, 1, parent)

    def update_list(self, data):
        """
        Update presets list

        :param data: Data to update
        """
        nodes = self.window.ui.nodes
        models = self.window.ui.models

        view = nodes[self.id]
        model = models.get(self.id)

        if model is None:
            model = self.create_model(self.window)
            models[self.id] = model
            view.setModel(model)
        try:
            if not data:
                model.setRowCount(0)
            else:
                count = len(data)
                model.setRowCount(count)
                index_fn = model.index
                set_item_data = model.setItemData
                display_role = QtCore.Qt.DisplayRole

                for i, (key, item) in enumerate(data.items()):
                    agent_id = item.id  # <---------- from this
                    name = item.name
                    idx = index_fn(i, 0)
                    set_item_data(idx, {
                        display_role: name,
                        QtCore.Qt.UserRole: agent_id,
                    })
        finally:
            pass

class AgentsList(BaseList):
    _ICO_EDIT = QIcon(":/icons/edit.svg")
    _ICO_COPY = QIcon(":/icons/copy.svg")
    _ICO_UNDO = QIcon(":/icons/undo.svg")
    _ICO_DELETE = QIcon(":/icons/delete.svg")
    _ICO_CHECK = QIcon(":/icons/check.svg")
    _ICO_CLOSE = QIcon(":/icons/close.svg")

    def __init__(self, window=None, tool=None, id=None):
        """
        Agents select menu

        :param window: main window
        :param id: input id
        """
        super(AgentsList, self).__init__(window)
        self.window = window
        self.id = id
        self.tool = tool
        self.doubleClicked.connect(self.dblclick)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def click(self, item):
        idx = item.row()
        if idx >= 0:
            model = self.model()
            agent_id = model.data(model.index(idx, 0), QtCore.Qt.UserRole)
            if agent_id is not None:
                self.tool.edit_agent(agent_id)

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        pass

    def show_context_menu(self, pos: QPoint):
        """
        Context menu event

        :param pos: QPoint
        """
        global_pos = self.viewport().mapToGlobal(pos)
        index = self.indexAt(pos)
        if not index.isValid():
            return

        menu = QMenu(self)

        edit_act = QAction(self._ICO_EDIT, trans('preset.action.edit'), menu)
        edit_act.triggered.connect(lambda checked=False, it=index: self.action_edit(it))
        menu.addAction(edit_act)

        duplicate_act = QAction(self._ICO_COPY, trans('preset.action.duplicate'), menu)
        duplicate_act.triggered.connect(lambda checked=False, it=index: self.action_duplicate(it))
        menu.addAction(duplicate_act)

        delete_act = QAction(self._ICO_DELETE, trans('preset.action.delete'), menu)
        delete_act.triggered.connect(lambda checked=False, it=index: self.action_delete(it))
        menu.addAction(delete_act)

        menu.exec_(global_pos)

    def action_edit(self, item):
        """
        Edit action handler

        :param item: list item
        """
        idx = item.row()
        if idx >= 0:
            model = self.model()
            agent_id = model.data(model.index(idx, 0), QtCore.Qt.UserRole)
            if agent_id is not None:
                self.tool.rename_agent(agent_id)

    def action_duplicate(self, item):
        """
        Duplicate action handler

        :param item: list item
        """
        idx = item.row()
        if idx >= 0:
            model = self.model()
            agent_id = model.data(model.index(idx, 0), QtCore.Qt.UserRole)
            if agent_id is not None:
                self.tool.duplicate_agent(agent_id)

    def action_delete(self, item):
        """
        Delete action handler

       :param item: list item
        """
        idx = item.row()
        if idx >= 0:
            model = self.model()
            agent_id = model.data(model.index(idx, 0), QtCore.Qt.UserRole)
            if agent_id is not None:
                self.tool.delete_agent(agent_id)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            if not index.isValid():
                return
            super().mousePressEvent(event)
        elif event.button() == Qt.RightButton:
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