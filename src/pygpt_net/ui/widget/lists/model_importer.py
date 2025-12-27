# models_list.py

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
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLabel, QCheckBox, QAbstractItemView, QMenu

from pygpt_net.ui.widget.lists.base import BaseList
from pygpt_net.utils import trans


class ImporterList(BaseList):
    def __init__(self, window=None, id=None):
        """
        Importer list view with virtual multi-select and context menu.

        - ExtendedSelection enables Ctrl/Shift multi-select gestures.
        - Single left click with no modifiers clears multi-selection when active.
        - Right-click context menu:
            * available list: Import
            * current list: Remove
        """
        super(ImporterList, self).__init__(window, id=id)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # RMB context menu
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
        super(ImporterList, self).mousePressEvent(event)

    def _selected_rows(self):
        """Return list of selected row indexes."""
        try:
            return list(self.selectionModel().selectedRows())
        except Exception:
            return []

    def show_context_menu(self, pos: QtCore.QPoint):
        """Context menu for available/current lists."""
        index = self.indexAt(pos)
        selected = self._selected_rows()
        multi = len(selected) > 1

        # Allow menu on empty area only when selection exists
        if not index.isValid() and not selected:
            return

        sel_model = self.selectionModel()

        # If right-clicked inside current multi-selection -> keep it
        # Else select the row under cursor temporarily
        if index.isValid():
            if multi:
                if index not in selected:
                    self._backup_selection = list(sel_model.selectedIndexes())
                    sel_model.clearSelection()
                    sel_model.select(index, sel_model.Select | sel_model.Rows)
                else:
                    self._backup_selection = None
            else:
                if not selected or index not in selected:
                    self._backup_selection = list(sel_model.selectedIndexes())
                    sel_model.clearSelection()
                    sel_model.select(index, sel_model.Select | sel_model.Rows)
                else:
                    self._backup_selection = None
        else:
            # empty area with some selection -> keep selection
            self._backup_selection = None

        menu = QMenu(self)
        if self.id == "models.importer.available":
            act_import = QAction(QIcon(":/icons/add.svg"), trans("action.import"), menu)
            act_import.triggered.connect(self._action_import)
            act_import.setEnabled(len(self._selected_rows()) > 0)
            menu.addAction(act_import)
        elif self.id == "models.importer.current":
            act_remove = QAction(QIcon(":/icons/close.svg"), trans("action.delete"), menu)
            act_remove.triggered.connect(self._action_remove)
            act_remove.setEnabled(len(self._selected_rows()) > 0)
            menu.addAction(act_remove)
        else:
            return  # unknown list; no menu

        global_pos = self.viewport().mapToGlobal(pos)
        menu.exec_(global_pos)

        # Restore original selection if it was temporarily changed and no action executed
        if self.restore_after_ctx_menu and self._backup_selection is not None:
            sel_model.clearSelection()
            for i in self._backup_selection:
                sel_model.select(i, sel_model.Select | sel_model.Rows)
        self._backup_selection = None
        self.restore_after_ctx_menu = True

    def _action_import(self):
        """Import selected models from available list (same as '>')."""
        self.restore_after_ctx_menu = False
        self.window.controller.model.importer.add()

    def _action_remove(self):
        """Remove selected models from current list (same as '<')."""
        self.restore_after_ctx_menu = False
        self.window.controller.model.importer.remove()


class ModelImporter(QWidget):
    def __init__(self, window=None):
        """
        Models importer widget

        :param window: main window
        """
        super(ModelImporter, self).__init__(window)
        self.window = window
        self.id = "models.importer"
        self.layout = self.setup()
        self.window.ui.models["models.importer.available"] = self.create_model(self.window)
        self.window.ui.nodes["models.importer.available"].setModel(self.window.ui.models["models.importer.available"])
        self.window.ui.nodes["models.importer.available"].selectionModel().selectionChanged.connect(
            lambda: self.window.controller.model.importer.change_available()
        )
        self.window.ui.models["models.importer.current"] = self.create_model(self.window)
        self.window.ui.nodes["models.importer.current"].setModel(self.window.ui.models["models.importer.current"])
        self.window.ui.nodes["models.importer.current"].selectionModel().selectionChanged.connect(
            lambda: self.window.controller.model.importer.change_current()
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
        self.window.ui.nodes["models.importer.add"] = QPushButton(">")
        self.window.ui.nodes["models.importer.add"].clicked.connect(
            lambda: self.window.controller.model.importer.add()
        )
        self.window.ui.nodes["models.importer.remove"] = QPushButton("<")
        self.window.ui.nodes["models.importer.remove"].clicked.connect(
            lambda: self.window.controller.model.importer.remove()
        )
        self.window.ui.nodes["models.importer.add"].setEnabled(False)  # initially disabled
        self.window.ui.nodes["models.importer.remove"].setEnabled(False)  # initially disabled
        arrows_layout.addWidget(self.window.ui.nodes["models.importer.add"])
        arrows_layout.addWidget(self.window.ui.nodes["models.importer.remove"])

        self.window.ui.nodes["models.importer.available.label"] = QLabel(trans("models.importer.available.label"))
        # importer-specific list with virtual multi-select + context menu
        self.window.ui.nodes["models.importer.available"] = ImporterList(self.window, id="models.importer.available")
        self.window.ui.nodes["models.importer.available"].clicked.disconnect()

        self.window.ui.nodes["models.importer.current.label"] = QLabel(trans("models.importer.current.label"))
        # importer-specific list with virtual multi-select + context menu
        self.window.ui.nodes["models.importer.current"] = ImporterList(self.window, id="models.importer.current")
        self.window.ui.nodes["models.importer.current"].clicked.disconnect()

        self.window.ui.nodes["models.importer.available.all"] = QCheckBox(trans("models.importer.all"), self.window)
        self.window.ui.nodes["models.importer.available.all"].clicked.connect(
            lambda: self.window.controller.model.importer.toggle_all(
                self.window.ui.nodes["models.importer.available.all"].isChecked())
        )

        available_layout = QVBoxLayout()
        available_layout.addWidget(self.window.ui.nodes["models.importer.available.label"])
        available_layout.addWidget(self.window.ui.nodes["models.importer.available"])
        available_layout.addWidget(self.window.ui.nodes["models.importer.available.all"])

        selected_layout = QVBoxLayout()
        selected_layout.addWidget(self.window.ui.nodes["models.importer.current.label"])
        selected_layout.addWidget(self.window.ui.nodes["models.importer.current"])

        layout.addLayout(available_layout)
        layout.addLayout(arrows_layout)
        layout.addLayout(selected_layout)
        return layout

    def update_available(self, data):
        """
        Update available models

        :param data: Data to update
        """
        id = "models.importer.available"
        self.window.ui.nodes[id].backup_selection()
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = data[n].id
            if data[n].name != data[n].id:
                name += f" ({data[n].name})"
            index = self.window.ui.models[id].index(i, 0)
            tooltip = data[n].id
            # store model ID in tooltip role for stable retrieval from view
            self.window.ui.models[id].setData(index, tooltip, QtCore.Qt.ToolTipRole)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1
        self.window.ui.nodes[id].restore_selection()

    def update_current(self, data):
        """
        Update current models

        :param data: Data to update
        """
        id = "models.importer.current"
        self.window.ui.nodes[id].backup_selection()
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            self.window.ui.models[id].insertRow(i)
            name = data[n].id
            if data[n].name != data[n].id:
                name += f" --> {data[n].name}"
            if data[n].imported:
                name = "* " + name  # mark imported models
            index = self.window.ui.models[id].index(i, 0)
            tooltip = data[n].id
            # store model ID in tooltip role for stable retrieval from view
            self.window.ui.models[id].setData(index, tooltip, QtCore.Qt.ToolTipRole)
            self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
            i += 1
        self.window.ui.nodes[id].restore_selection()

    def update_lists(self, available: dict, current: dict):
        """
        Update lists

        :param available: data with available models
        :param current: data with current models
        """
        self.update_available(available)
        self.update_current(current)