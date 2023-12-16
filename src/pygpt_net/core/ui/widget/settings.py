#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.16 12:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QLineEdit, QDialog, QLabel, QCheckBox, QHBoxLayout, QWidget, QSlider, QTextEdit, \
    QVBoxLayout, QPushButton, QTreeView, QMenu

from .select import SelectMenu
from ...utils import trans


class NoScrollSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super(NoScrollSlider, self).__init__(orientation, parent)

    def wheelEvent(self, event):
        event.ignore()  # disable mouse wheel


class SettingsSlider(QWidget):
    def __init__(self, window=None, id=None, title=None, min=None, max=None, step=None, value=None, max_width=True,
                 section=None):
        """
        Settings slider

        :param window: main window
        :param id: option id
        :param title: option title
        :param min: min value
        :param max: max value
        :param step: value step
        :param value: current value
        :param max_width: max width
        :param section: settings section
        """
        super(SettingsSlider, self).__init__(window)
        self.window = window
        self.id = id
        self.title = title
        self.min = min
        self.max = max
        self.step = step
        self.value = value
        self.section = section

        self.label = QLabel(title)
        self.slider = NoScrollSlider(Qt.Horizontal)
        self.slider.setMinimum(min)
        self.slider.setMaximum(max)
        self.slider.setSingleStep(step)
        self.slider.setValue(value)
        self.slider.valueChanged.connect(
            lambda: self.window.controller.settings.apply(self.id, self.slider.value(), 'slider', self.section))

        if max_width:
            self.slider.setMaximumWidth(240)

        self.input = SettingsInputInline(self.window, self.id, self.section)
        self.input.setText(str(value))

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.input)

        self.setLayout(self.layout)


class SettingsCheckbox(QWidget):
    def __init__(self, window=None, id=None, title=None, value=False, section=None):
        """
        Settings checkbox

        :param window: main window
        :param id: option id
        :param title: option title
        :param value: current value
        :param section: settings section
        """
        super(SettingsCheckbox, self).__init__(window)
        self.window = window
        self.id = id
        self.title = title
        self.value = value
        self.section = section

        self.box = QCheckBox(title, self.window)
        self.box.setChecked(value)
        self.box.stateChanged.connect(
            lambda: self.window.controller.settings.toggle(self.id, self.box.isChecked(), self.section))

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.box)

        self.setLayout(self.layout)


class SettingsInputInline(QLineEdit):
    def __init__(self, window=None, id=None, section=None):
        """
        Settings input inline

        :param window: main window
        :param id: option id
        :param section: settings section
        """
        super(SettingsInputInline, self).__init__(window)
        self.window = window
        self.id = id
        self.section = section
        self.setMaximumWidth(60)

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(SettingsInputInline, self).keyPressEvent(event)
        self.window.controller.settings.apply(self.id, self.text(), 'input', self.section)


class SettingsInput(QLineEdit):
    def __init__(self, window=None, id=None, autoupdate=False, section=None):
        """
        Settings input

        :param window: main window
        :param id: option id
        :param autoupdate: auto update
        :param section: settings section
        """
        super(SettingsInput, self).__init__(window)
        self.window = window
        self.id = id
        self.section = section
        self.autoupdate = autoupdate

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(SettingsInput, self).keyPressEvent(event)
        if not self.autoupdate:
            return
        self.window.controller.ui.update()
        self.window.controller.settings.change(self.id, self.text(), self.section)


class SettingsTextarea(QTextEdit):
    def __init__(self, window=None, id=None, autoupdate=False, section=None):
        """
        Settings input

        :param window: main window
        :param id: option id
        :param autoupdate: auto update
        :param section: settings section
        """
        super(SettingsTextarea, self).__init__(window)
        self.window = window
        self.id = id
        self.section = section
        self.autoupdate = autoupdate

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        super(SettingsTextarea, self).keyPressEvent(event)
        if not self.autoupdate:
            return
        self.window.controller.ui.update()
        self.window.controller.settings.change(self.id, self.toPlainText(), self.section)


class SettingsDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Settings dialog

        :param window: main window
        :param id: settings id
        """
        super(SettingsDialog, self).__init__(window)
        self.window = window
        self.id = id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.window.settings.active[self.id] = False
        self.window.controller.settings.close(self.id)
        self.window.controller.settings.update()


class PluginSettingsDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Plugin settings dialog

        :param window: main window
        :param id: settings id
        """
        super(PluginSettingsDialog, self).__init__(window)
        self.window = window
        self.id = id

    def closeEvent(self, event):
        """
        Close event

        :param event: close event
        """
        self.window.controller.plugins.config_dialog = False
        self.window.controller.plugins.update()


class PluginSelectMenu(SelectMenu):
    def __init__(self, window=None, id=None):
        """
        Plugin select menu (in settings dialog)

        :param window: main window
        :param id: input id
        """
        super(PluginSelectMenu, self).__init__(window)
        self.window = window
        self.id = id

        self.doubleClicked.connect(self.dblclick)

    def click(self, val):
        idx = val.row()
        self.window.tabs['plugin.settings'].setCurrentIndex(idx)
        self.window.controller.plugins.set_plugin_by_tab(idx)

    def dblclick(self, val):
        """
        Double click event

        :param val: double click event
        """
        self.window.controller.presets.edit(val.row())


class SettingsDictModel(QAbstractItemModel):
    def __init__(self, items, headers, parent=None):
        super(SettingsDictModel, self).__init__(parent)
        self.items = items
        self.headers = headers

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
        return super(SettingsDictModel, self).flags(index) | Qt.ItemIsEditable

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


class SettingsDictItems(QTreeView):
    NAME = range(1)  # list of columns

    def __init__(self, owner=None):
        """
        Select menu

        :param window: main window
        :param id: input id
        """
        super(SettingsDictItems, self).__init__(owner)
        self.parent = owner
        self.setIndentation(0)
        self.setHeaderHidden(False)

    def contextMenuEvent(self, event):
        """
        Context menu event

        :param event: context menu event
        """
        actions = {}
        actions['delete'] = QAction(QIcon.fromTheme("edit-delete"), trans('action.delete'), self)
        actions['delete'].triggered.connect(
            lambda: self.parent.delete_item(event))
        menu = QMenu(self)
        menu.addAction(actions['delete'])

        # get index of item
        item = self.indexAt(event.pos())
        idx = item.row()
        if idx >= 0:
            menu.exec_(event.globalPos())


class SettingsDict(QWidget):
    def __init__(self, window=None, option_id=None, autoupdate=True, section=None, parent_id=None, keys=None, values=None):
        """
        Settings dictionary items

        :param window: main window
        :param option_id: option id
        :param autoupdate: auto update
        :param section: settings section
        :param parent_id: parent id
        :param keys: dict keys
        :param values: dict values
        """
        super(SettingsDict, self).__init__(window)
        self.window = window
        self.id = option_id  # option id (key)
        self.section = section  # settings or plugin
        self.parent_id = parent_id  # plugin id or None if settings
        self.autoupdate = autoupdate
        self.keys = keys  # dict keys
        self.items = list(values)  # dict items

        # setup dict model
        headers = list(self.keys.keys())

        self.list = SettingsDictItems(self)
        self.model = SettingsDictModel(self.items, headers)
        self.model.dataChanged.connect(self.model.saveData)

        # append dict model
        self.list.setModel(self.model)
        self.list.selectionModel().selectionChanged.connect(
            lambda: self.window.controller.context.selection_change())

        # add button
        self.add_btn = QPushButton(trans('action.add'), self)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.add)

        # layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.add_btn)
        self.layout.addWidget(self.list)
        self.setLayout(self.layout)

        # update model list
        self.update()

    def add(self):
        """
        Add new empty item to settings dict
        """
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

    def delete_item(self, event):
        """
        Delete item (show confirm)

        :param event: Menu event
        """
        index = self.list.indexAt(event.pos())
        if index.isValid():
            # remove item
            idx = index.row()
            self.window.controller.settings.delete_item(self, idx)

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
