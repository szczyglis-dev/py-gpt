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

from PySide6.QtWidgets import QHBoxLayout, QWidget, QComboBox

from pygpt_net.ui.widget.option.combo import NoScrollCombo
from pygpt_net.utils import trans

class BaseCombo(QWidget):
    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Llama index mode select combobox

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(BaseCombo, self).__init__(window)
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
        self.initialized = False

        # add items
        self.update()

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.combo)
        self.setLayout(self.layout)
        self.fit_to_content()
        self.initialized = True

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

    def has_key(self, name: str) -> bool:
        """
        Check if combo has key

        :param name: key name
        :return:
        """
        if isinstance(self.keys, list):
            for key in self.keys:
                if isinstance(key, dict):
                    if name in key:
                        return True
                elif name == key:
                    return True
        return False

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
        """
        if not self.initialized:
            return
        self.current_id = self.combo.itemData(index)
        # print("Selected item: ", self.current_id)

    def fit_to_content(self):
        """Fit to content"""
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
