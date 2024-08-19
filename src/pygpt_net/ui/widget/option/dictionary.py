#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.20 00:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex, QSize
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTreeView, QMenu, QStyledItemDelegate, QComboBox, \
    QCheckBox, QHeaderView, QHBoxLayout

from pygpt_net.utils import trans
import pygpt_net.icons_rc


class OptionDict(QWidget):
    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Settings dictionary items

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(OptionDict, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option
        self.title = ""
        self.real_time = False
        self.keys = {}
        self.items = []

        # init from option data
        if self.option is not None:
            if "label" in self.option:
                self.title = self.option["label"]
            if "value" in self.option:
                self.items = self.option["value"]
            if "keys" in self.option:
                self.keys = self.option["keys"]
            if "items" in self.option:
                self.items = list(self.option["items"])
            if "real_time" in self.option:
                self.real_time = self.option["real_time"]

        # setup dict model
        headers = list(self.keys.keys())

        self.list = OptionDictItems(self)
        max_height_delegate = MaxHeightDelegate(40, self.list)
        self.list.setItemDelegate(max_height_delegate)
        self.model = OptionDictModel(self.items, headers)
        self.model.dataChanged.connect(self.model.saveData)

        # append dict model
        self.list.setModel(self.model)

        # init layout
        self.init_layout()

        # update model list
        self.update()

    def init_layout(self):
        # add button
        self.add_btn = QPushButton(trans('action.add'), self)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.add)
        self.add_btn.setAutoDefault(False)

        self.buttons = QHBoxLayout()
        self.buttons.addWidget(self.add_btn)
        self.buttons.setContentsMargins(0, 0, 0, 0)

        # layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addLayout(self.buttons)
        self.layout.addWidget(self.list)
        self.setLayout(self.layout)

    def add(self):
        """Add new empty item to settings dict"""
        # create empty dict
        empty = {header: '' for header in self.model.headers}
        count = self.model.rowCount()

        # add new item
        self.model.items.append(empty)
        self.model.updateData(self.model.items)

        # mark new item
        new_index = self.model.index(count, 0)
        self.list.setCurrentIndex(new_index)
        self.list.scrollTo(new_index)

    def edit_item(self, event):
        """
        Open item editor dialog

        :param event: Menu event
        """
        index = self.list.indexAt(event.pos())
        if index.isValid():
            idx = index.row()
            data = self.model.items[idx]
            id = self.parent_id + "." + self.id  # dictionary id
            self.window.ui.dialogs.open_dictionary_editor(id, self.option, data, idx)

    def update_item(self, idx, data):
        """
        Update item data in model by idx

        :param idx: Index of item
        :param data: Item data dict (key: value)
        """
        self.model.items[idx] = data
        self.model.updateData(self.model.items)

    def delete_item(self, event):
        """
        Delete item (show confirm)

        :param event: Menu event
        """
        index = self.list.indexAt(event.pos())
        if index.isValid():
            idx = index.row()
            self.window.controller.config.dictionary.delete_item(self, idx)

    def delete_item_execute(self, idx):
        """
        Delete item (execute)

        :param idx: Index of item
        """
        if len(self.model.items) > idx:
            self.model.items.pop(idx)
        self.model.removeRows(idx, 1)

        # update model list
        self.update()
        self.list.updateGeometries()
        self.items = self.model.items
        self.model.updateData(self.items)

    def remove(self):
        """
        Remove all items
        """
        self.model.removeRows(0, self.model.rowCount())

    def update(self):
        """
        Updates list of items
        """
        self.model.removeRows(0, self.model.rowCount())
        i = 0
        for item in list(self.items):
            self.model.insertRow(i)
            j = 0
            for k in self.keys:
                if k in item:
                    # add item to model list
                    self.model.setData(self.model.index(i, j), item[k])
                j += 1
            i += 1


class OptionDictItems(QTreeView):
    NAME = range(1)  # list of columns

    def __init__(self, owner=None):
        """
        Select menu

        :param window: main window
        :param id: input id
        """
        super(OptionDictItems, self).__init__(owner)
        self.parent = owner
        self.setIndentation(0)
        self.setHeaderHidden(False)

        header = self.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Stretch)

        # setup fields
        keys = self.parent.keys
        idx = 0
        for key in keys:
            item = keys[key]
            if type(item) is dict:
                if "type" in item:
                    if item["type"] == "combo":
                        handler = ComboBoxDelegate(self, item["keys"])
                        self.setItemDelegateForColumn(idx, handler)
            elif type(item) is str:
                if item == "bool":
                    handler = CheckBoxDelegate(self)
                    self.setItemDelegateForColumn(idx, handler)
                elif item == "hidden":
                    continue
            idx += 1

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['edit'] = QAction(QIcon(":/icons/edit.svg"), trans('action.edit'), self)
        actions['edit'].triggered.connect(
            lambda: self.parent.edit_item(event))
        actions['delete'] = QAction(QIcon(":/icons/delete.svg"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.parent.delete_item(event))
        menu = QMenu(self)
        menu.addAction(actions['edit'])
        menu.addAction(actions['delete'])

        # get index of item
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            menu.exec_(event.globalPos())


class OptionDictModel(QAbstractItemModel):
    def __init__(self, items, headers, parent=None):
        super(OptionDictModel, self).__init__(parent)
        self.items = items
        self.headers = headers
        self.checkbox_key = 'enabled'

    def headerData(self, section, orientation, role):
        """
        Header data
        :param section: Section
        :param orientation: Orientation
        :param role: Role
        :return: Header data
        """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def rowCount(self, parent=QModelIndex()):
        """
        Row count
        :param parent: Parent
        :return: Row count
        """
        return len(self.items) if not parent.isValid() else 0

    def columnCount(self, parent=QModelIndex()):
        """
        Column count
        :param parent: Parent
        :return: Column count
        """
        return len(self.headers) if not parent.isValid() else 0

    def data(self, index, role=Qt.DisplayRole):
        """
        Data
        :param index: Index
        :param role: Role
        :return: Data
        """
        if not index.isValid():
            return None
        if role == Qt.CheckStateRole and index.column() == 0 and self.headers[index.column()] == "enabled":
            value = self.items[index.row()].get('enabled', False)
            return Qt.Checked if value else Qt.Unchecked
        if role == Qt.EditRole and index.column() == 0 and self.headers[index.column()] == "enabled":
            return self.items[index.row()].get('enabled', False)
        if role == Qt.DisplayRole or role == Qt.EditRole:
            entry = self.items[index.row()]
            key = self.headers[index.column()]
            return entry.get(key, "")
        return None

    def setData(self, index, value, role=Qt.EditRole):
        """
        Set data
        :param index: Index
        :param value: Value
        :param role: Role
        :return: Set data
        """
        if index.isValid() and role == Qt.CheckStateRole and self.headers[index.column()] == "enabled":
            self.items[index.row()]['enabled'] = (value == Qt.Checked)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True

        if index.isValid() and role == Qt.EditRole:
            entry = self.items[index.row()]
            key = self.headers[index.column()]
            entry[key] = value
            self.dataChanged.emit(index, index, [Qt.EditRole])
            return True
        return False

    def flags(self, index):
        """
        Flags
        :param index: Index
        :return: Flags
        """
        if not index.isValid():
            return Qt.NoItemFlags
        if index.column() == 0 and self.headers[index.column()] == "enabled":
            return super(OptionDictModel, self).flags(index) | Qt.ItemIsUserCheckable | Qt.ItemIsEditable
        return super(OptionDictModel, self).flags(index) | Qt.ItemIsEditable

    def parent(self, index):
        """
        Parent
        :param index: Index
        :return: Parent
        """
        return QModelIndex()

    def index(self, row, column, parent=QModelIndex()):
        """
        Index
        :param row: Row
        :param column: Column
        :param parent: Parent
        :return: Index
        """
        if parent.isValid() or row >= len(self.items) or column >= len(self.headers):
            return QModelIndex()
        return self.createIndex(row, column)

    def saveData(self):
        """
        Save data
        """
        pass

    def updateData(self, data):
        """
        Update data
        :param new_data_list: New data list
        """
        self.beginResetModel()
        self.items = data
        self.endResetModel()


class CheckBoxDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QCheckBox(parent)
        return editor

    def setEditorData(self, editor, index):
        checked = index.model().data(index, Qt.EditRole)
        if type(checked) is str:
            checked = checked == 'true'
        editor.setChecked(checked)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.isChecked(), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class ComboBoxDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, keys=None):
        super(ComboBoxDelegate, self).__init__(parent)
        self.keys = keys

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        for item in self.keys:
            if isinstance(item, dict):
                for key, value in item.items():
                    editor.addItem(value, key)
            else:
                editor.addItem(item)
        return editor

    def setEditorData(self, editor, index):
        key = index.model().data(index, Qt.EditRole)
        if key is not None:
            index = editor.findData(key)
            if index >= 0:
                editor.setCurrentIndex(index)

    def setModelData(self, editor, model, index):
        key = editor.currentData()
        model.setData(index, key, Qt.EditRole)

    def displayText(self, value, locale):
        for item in self.keys:
            if isinstance(item, dict):
                if value in item:
                    return item[value]
        return value


class MaxHeightDelegate(QStyledItemDelegate):
    def __init__(self, max, parent=None):
        super().__init__(parent)
        self.maxHeight = max

    def sizeHint(self, option, index):
        original = super().sizeHint(option, index)
        limited = min(original.height(), self.maxHeight)
        return QSize(original.width(), limited)