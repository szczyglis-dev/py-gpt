#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.12 19:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QWidget, QComboBox
from PySide6.QtGui import QFontMetrics

from pygpt_net.utils import trans

class SeparatorComboBox(QComboBox):
    """A combo box that supports adding separator items."""

    def addSeparator(self, text):
        """
        Adds a separator item to the combo box.

        :param text: The text to display for the separator.
        """
        index = self.count()
        self.addItem(text)
        try:
            role = Qt.UserRole - 1
            self.setItemData(index, 0, role)
        except:
            pass


class NoScrollCombo(SeparatorComboBox):
    """A combo box that disables mouse wheel scrolling."""

    def __init__(self, parent=None):
        super(NoScrollCombo, self).__init__(parent)

    def wheelEvent(self, event):
        event.ignore()  # disable mouse wheel

    def showPopup(self):
        max_width = 0
        font_metrics = QFontMetrics(self.font())
        for i in range(self.count()):
            text = self.itemText(i)
            width = font_metrics.horizontalAdvance(text)
            max_width = max(max_width, width)
        extra_margin = 80
        max_width += extra_margin
        self.view().setMinimumWidth(max_width)
        super().showPopup()


class OptionCombo(QWidget):
    """A combobox for selecting options in the settings."""

    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Settings combobox

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(OptionCombo, self).__init__(window)
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
        self.locked = False

        # add items
        self.update()

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.combo)
        self.layout.setContentsMargins(0, 0, 0, 0)
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
                        if key.startswith("separator::"):
                            self.combo.addSeparator(value)
                        else:
                            self.combo.addItem(value, key)
                else:
                    self.combo.addItem(item, item)
        elif type(self.keys) is dict:
            for key, value in self.keys.items():
                if key.startswith("separator::"):
                    self.combo.addSeparator(value)
                else:
                    self.combo.addItem(value, key)

    def set_value(self, value):
        """
        Set value

        :param value: value
        """
        if not value:
            return
        index = self.combo.findData(value)
        if index != -1:
            self.combo.setCurrentIndex(index)

    def get_value(self):
        """
        Get value

        :return: value
        """
        return self.current_id

    def set_keys(self, keys, lock: bool = False):
        """
        Set keys

        :param keys: keys
        :param lock: lock current value if True
        """
        if lock:
            self.locked = True  # lock on_change
        self.keys = keys
        self.option["keys"] = keys
        self.combo.clear()
        self.update()
        if lock:
            self.locked = False

    def on_combo_change(self, index):
        """
        On combo change

        :param index: combo index
        :return:
        """
        if self.locked:
            return
        self.current_id = self.combo.itemData(index)
        self.window.controller.config.combo.on_update(self.parent_id, self.id, self.option, self.current_id)

    def fit_to_content(self):
        """Fit to content"""
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)

