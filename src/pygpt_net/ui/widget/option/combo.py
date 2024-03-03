#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QHBoxLayout, QWidget, QComboBox

from pygpt_net.utils import trans


class NoScrollCombo(QComboBox):
    def __init__(self, parent=None):
        super(NoScrollCombo, self).__init__(parent)

    def wheelEvent(self, event):
        event.ignore()  # disable mouse wheel


class OptionCombo(QWidget):
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

        # add items
        self.update()

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.combo)
        self.setLayout(self.layout)

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
            if "real_time" in self.option:
                self.real_time = self.option["real_time"]

        # add items
        if type(self.keys) is list:
            for item in self.keys:
                if type(item) is dict:
                    for key, value in item.items():
                        self.combo.addItem(value, key)
                else:
                    self.combo.addItem(item)

    def on_combo_change(self, index):
        """
        On combo change

        :param index: combo index
        :return:
        """
        current_id = self.combo.itemData(index)
        self.window.controller.config.combo.on_update(self.parent_id, self.id, self.option, current_id)

