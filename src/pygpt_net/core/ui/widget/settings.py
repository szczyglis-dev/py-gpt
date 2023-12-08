#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.08 22:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QLineEdit, QDialog, QLabel, QCheckBox, QHBoxLayout, QWidget, QSlider, QTextEdit, \
    QVBoxLayout, QPushButton, QTreeView, QAbstractItemView, QMenu

from .select import SelectMenu


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
        self.slider = QSlider(Qt.Horizontal)
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
    def __init__(self, data_list, headers, parent=None):
        super(SettingsDictModel, self).__init__(parent)
        self.data_list = data_list
        self.headers = headers

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self.data_list) if not parent.isValid() else 0

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers) if not parent.isValid() else 0

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            dict_entry = self.data_list[index.row()]
            key = self.headers[index.column()]
            return dict_entry.get(key, "")
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and role == Qt.EditRole:
            dict_entry = self.data_list[index.row()]
            key = self.headers[index.column()]
            dict_entry[key] = value
            self.dataChanged.emit(index, index, [Qt.EditRole])
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return super(SettingsDictModel, self).flags(index) | Qt.ItemIsEditable

    def parent(self, index):
        return QModelIndex()

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid() or row >= len(self.data_list) or column >= len(self.headers):
            return QModelIndex()
        return self.createIndex(row, column)

    def saveData(self):
        print("Dane zaktualizowane w modelu:")
        print(self.data_list)

    def updateData(self, new_data_list):
        self.beginResetModel()
        self.data_list = new_data_list
        self.endResetModel()


class SettingsDictItens(QTreeView):
    NAME = range(1)  # list of columns

    def __init__(self, window=None, id=None):
        """
        Select menu

        :param window: main window
        :param id: input id
        """
        super(SettingsDictItens, self).__init__(window)
        self.window = window
        self.id = id
        self.setIndentation(0)
        self.setHeaderHidden(False)

    def click(self, val):
        self.window.controller.model.select(self.id, val.row())


class SettingsDict(QWidget):
    def __init__(self, window=None, option_id=None, autoupdate=True, section=None, parent_id=None, keys=None, values=None):
        """
        Settings dictionary items

        :param window: main window
        :param option_id: option id
        :param autoupdate: auto update
        :param section: settings section
        """
        super(SettingsDict, self).__init__(window)
        self.window = window
        self.id = option_id  # option id (key)
        self.section = section  # settings or plugin
        self.parent_id = parent_id  # plugin id or None if settings
        self.autoupdate = autoupdate
        self.keys = keys  # dict keys
        self.items = list(values)  # dict items

        # setup model
        headers = list(self.keys.keys())
        self.list = SettingsDictItens(self)
        self.model = SettingsDictModel(self.items, headers)
        self.model.dataChanged.connect(self.model.saveData)

        # append model
        self.list.setModel(self.model)
        self.list.selectionModel().selectionChanged.connect(
            lambda: self.window.controller.context.selection_change())

        # add button
        add_btn = QPushButton('ADD NEW', self)
        add_btn.clicked.connect(self.add)

        # layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(add_btn)
        self.layout.addWidget(self.list)
        self.setLayout(self.layout)

        # context menu
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.openContextMenu)

        # update model list
        self.update()

    def add(self):
        empty_dict = {header: '' for header in self.model.headers}
        row_count = self.model.rowCount()
        self.model.data_list.append(empty_dict)
        self.model.updateData(self.model.data_list)
        new_index = self.model.index(row_count, 0)
        self.list.setCurrentIndex(new_index)
        self.list.scrollTo(new_index)

    def openContextMenu(self, position):
        menu = QMenu()
        deleteAction = menu.addAction("Delete Row")
        action = menu.exec_(self.list.viewport().mapToGlobal(position))
        if action == deleteAction:
            index = self.list.currentIndex()
            if index.isValid():
                idx = index.row()
                print("remove row {}".format(idx))
                if len(self.model.data_list) > idx:
                    self.model.data_list.pop(idx)
                self.model.removeRows(idx, 1)
                self.update()
                self.list.updateGeometries()
                self.items = self.model.data_list
                self.model.updateData(self.items)

    def remove(self):
        self.model.removeRows(0, self.model.rowCount())

    def update(self):
        """
        Updates list of items
        """
        self.model.removeRows(0, self.model.rowCount())
        i = 0
        for item in list(self.items):  # self.items is list of dicts, n is dict, k is key
            self.model.insertRow(i)
            j = 0
            for k in self.keys:
                if k in item:
                    self.model.setData(self.model.index(i, j), item[k])
                j += 1
            i += 1
