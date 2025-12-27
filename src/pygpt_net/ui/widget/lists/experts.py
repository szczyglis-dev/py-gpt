# list.py

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.27 21:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel, QAction, QIcon
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLabel, QAbstractItemView, QMenu
from PySide6.QtCore import QItemSelectionModel

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class ExpertsList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Experts list view with virtual multi-select and context menu.

        - ExtendedSelection enables Ctrl/Shift multi-select gestures.
        - Single left click with no modifiers clears multi-selection when active.
        - Right-click context menu:
            * available list: Add
            * selected list: Remove
        """
        super(ExpertsList, self).__init__(window, id=id)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self._backup_selection = None
        self.restore_after_ctx_menu = True

    def mousePressEvent(self, event):
        """
        Clear multi-selection on a single left click (any position or empty area),
        then proceed with default selection behavior for the clicked row.
        """
        if event.button() == QtCore.Qt.LeftButton and event.modifiers() == QtCore.Qt.NoModifier:
            sel_model = self.selectionModel()
            if sel_model is not None and len(sel_model.selectedRows()) > 1:
                index = self.indexAt(event.pos())
                sel_model.clearSelection()
                if not index.isValid():
                    event.accept()
                    return
        super(ExpertsList, self).mousePressEvent(event)

    def _selected_rows(self):
        """Return list of selected row indexes."""
        try:
            return list(self.selectionModel().selectedRows())
        except Exception:
            return []

    def show_context_menu(self, pos: QtCore.QPoint):
        """Context menu for available/selected experts lists."""
        index = self.indexAt(pos)
        selected = self._selected_rows()

        if not index.isValid() and not selected:
            return

        sel_model = self.selectionModel()
        # Preserve multi-selection if RMB inside it; otherwise temporarily select clicked row
        if index.isValid():
            selected_rows = [ix.row() for ix in selected]
            if len(selected_rows) > 1 and index.row() in selected_rows:
                self._backup_selection = None
            else:
                self._backup_selection = list(sel_model.selectedIndexes())
                sel_model.clearSelection()
                sel_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        else:
            self._backup_selection = None

        menu = QMenu(self)
        if self.id == "preset.experts.available":
            act_add = QAction(QIcon(":/icons/add.svg"), trans('action.add'), menu)
            act_add.triggered.connect(self._action_add)
            act_add.setEnabled(len(self._selected_rows()) > 0)
            menu.addAction(act_add)
        elif self.id == "preset.experts.selected":
            act_remove = QAction(QIcon(":/icons/close.svg"), trans('action.delete'), menu)
            act_remove.triggered.connect(self._action_remove)
            act_remove.setEnabled(len(self._selected_rows()) > 0)
            menu.addAction(act_remove)
        else:
            return

        global_pos = self.viewport().mapToGlobal(pos)
        menu.exec_(global_pos)

        if self.restore_after_ctx_menu and self._backup_selection is not None:
            sel_model.clearSelection()
            for i in self._backup_selection:
                sel_model.select(i, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self._backup_selection = None
        self.restore_after_ctx_menu = True

    def _action_add(self):
        """Add selected experts from available list (same as '>')."""
        self.restore_after_ctx_menu = False
        self.window.controller.presets.editor.experts.add_expert()

    def _action_remove(self):
        """Remove selected experts from selected list (same as '<')."""
        self.restore_after_ctx_menu = False
        self.window.controller.presets.editor.experts.remove_expert()


class ExpertsEditor(QWidget):
    def __init__(self, window=None):
        """
        Experts select menu

        :param window: main window
        """
        super(ExpertsEditor, self).__init__(window)
        self.window = window
        self.id = "preset.experts"
        self.layout = self.setup()
        self.window.ui.models["preset.experts.available"] = self.create_model(self.window)
        self.window.ui.nodes["preset.experts.available"].setModel(self.window.ui.models["preset.experts.available"])
        self.window.ui.nodes["preset.experts.available"].selectionModel().selectionChanged.connect(
            lambda: self.window.controller.presets.editor.experts.change_available()
        )
        self.window.ui.models["preset.experts.selected"] = self.create_model(self.window)
        self.window.ui.nodes["preset.experts.selected"].setModel(self.window.ui.models["preset.experts.selected"])
        self.window.ui.nodes["preset.experts.selected"].selectionModel().selectionChanged.connect(
            lambda: self.window.controller.presets.editor.experts.change_selected()
        )
        self.setLayout(self.layout)

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        return QStandardItemModel(0, 1, parent)

    def setup(self):
        """Setup layout"""
        layout = QHBoxLayout()
        arrows_layout = QVBoxLayout()
        self.window.ui.nodes["preset.experts.add"] = QPushButton(">")
        self.window.ui.nodes["preset.experts.add"].clicked.connect(
            lambda: self.window.controller.presets.editor.experts.add_expert()
        )
        self.window.ui.nodes["preset.experts.remove"] = QPushButton("<")
        self.window.ui.nodes["preset.experts.remove"].clicked.connect(
            lambda: self.window.controller.presets.editor.experts.remove_expert()
        )
        arrows_layout.addWidget(self.window.ui.nodes["preset.experts.add"])
        arrows_layout.addWidget(self.window.ui.nodes["preset.experts.remove"])

        self.window.ui.nodes["preset.experts.available.label"] = QLabel(trans("preset.experts.available.label"))
        self.window.ui.nodes["preset.experts.available"] = ExpertsList(self.window, id="preset.experts.available")
        self.window.ui.nodes["preset.experts.available"].clicked.disconnect()

        self.window.ui.nodes["preset.experts.selected.label"] = QLabel(trans("preset.experts.selected.label"))
        self.window.ui.nodes["preset.experts.selected"] = ExpertsList(self.window, id="preset.experts.selected")
        self.window.ui.nodes["preset.experts.selected"].clicked.disconnect()

        available_layout = QVBoxLayout()
        available_layout.addWidget(self.window.ui.nodes["preset.experts.available"])
        available_layout.addWidget(self.window.ui.nodes["preset.experts.available.label"])

        selected_layout = QVBoxLayout()
        selected_layout.addWidget(self.window.ui.nodes["preset.experts.selected"])
        selected_layout.addWidget(self.window.ui.nodes["preset.experts.selected.label"])

        layout.addLayout(available_layout)
        layout.addLayout(arrows_layout)
        layout.addLayout(selected_layout)
        layout.setContentsMargins(0, 0, 0, 0)
        return layout

    def update_available(self, data):
        """
        Update available experts

        :param data: Data to update
        """
        id = "preset.experts.available"
        self.window.ui.nodes[id].backup_selection()
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = data[n].name + "  [" + data[n].filename + "]"
            index = self.window.ui.models[id].index(i, 0)
            tooltip = data[n].uuid
            self.window.ui.models[id].setData(index, tooltip, QtCore.Qt.ToolTipRole)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1
        self.window.ui.nodes[id].restore_selection()

    def update_selected(self, data):
        """
        Update selected experts

        :param data: Data to update
        """
        id = "preset.experts.selected"
        self.window.ui.nodes[id].backup_selection()
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = data[n].name + "  [" + data[n].filename + "]"
            index = self.window.ui.models[id].index(i, 0)
            tooltip = data[n].uuid
            self.window.ui.models[id].setData(index, tooltip, QtCore.Qt.ToolTipRole)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1
        self.window.ui.nodes[id].restore_selection()

    def update_lists(self, available: dict, selected: dict):
        """
        Update lists

        :param available: data with available experts
        :param selected: data with selected experts
        """
        self.update_available(available)
        self.update_selected(selected)