#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 02:00:00                  #
# ================================================== #
from typing import Dict

from PySide6.QtWidgets import QCheckBox, QWidget

from pygpt_net.ui.base.flow_layout import FlowLayout
from pygpt_net.utils import trans

import pygpt_net.icons_rc

class OptionCheckboxList(QWidget):
    def __init__(
            self,
            window=None,
            parent_id: str = None,
            id: str = None,
            option: dict = None,
            icon = None
    ):
        """
        Settings checkbox list

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        :param icon: icon
        """
        super(OptionCheckboxList, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option
        self.value = False
        self.title = ""
        self.real_time = False
        self.keys = {}
        self.boxes = {}

        # init from option data
        if self.option is not None:
            if "label" in self.option and self.option["label"] is not None \
                    and self.option["label"] != "":
                self.title = trans(self.option["label"])
            if "value" in self.option:
                self.value = self.option["value"]
            if "real_time" in self.option:
                self.real_time = self.option["real_time"]
            if "keys" in self.option:
                self.keys = self.option["keys"]

        values = self.value.split(",") if isinstance(self.value, str) else []
        widgets = []

        # create a checkbox for each key
        for item in self.keys:
            # item is a dict with key:name
            if type(item) is dict:
                for key, name in item.items():
                    self.boxes[key] = QCheckBox(name, self.window)
                    self.boxes[key].setStyleSheet("margin-left: 5px; margin-right: 5px;")
                    if key in values:
                        self.boxes[key].setChecked(True)
                    else:
                        self.boxes[key].setChecked(False)
                    self.boxes[key].stateChanged.connect(
                        lambda state, k=key: self.window.controller.config.checkbox_list.on_update(
                            self.parent_id,
                            self.id,
                            self.option,
                            state,
                            k
                        )
                    )
                    widgets.append(self.boxes[key])

        self.layout = FlowLayout()
        for widget in widgets:
            self.layout.addWidget(widget)

        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def update_boxes_list(self, keys: dict) -> None:
        """
        Update checkbox list with new keys

        :param keys: dictionary with keys and names
        """
        self.keys = keys

        # remove all existing checkboxes from the layout
        while self.layout.count() > 0:
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        # clear the boxes dictionary
        self.boxes.clear()

        # get current values from the option
        values = self.value.split(",") if isinstance(self.value, str) else []

        # create a checkbox for each key
        for item in self.keys:
            # item is a dict with key:name
            if type(item) is dict:
                for key, name in item.items():
                    checkbox = QCheckBox(name, self.window)
                    checkbox.setStyleSheet("margin-left: 5px; margin-right: 5px;")
                    checkbox.setChecked(key in values)
                    checkbox.stateChanged.connect(
                        lambda state, k=key: self.window.controller.config.checkbox_list.on_update(
                            self.parent_id,
                            self.id,
                            self.option,
                            state,
                            k
                        )
                    )
                    self.boxes[key] = checkbox
                    self.layout.addWidget(checkbox)

    def setIcon(self, icon: str):
        """
        Set icon

        :param icon: icon
        """
        pass

    def setText(self, key: str, text: str):
        """
        Set label text

        :param key: checkbox key
        :param text: text
        """
        if key in self.boxes:
            self.boxes[key].setText(text)

    def setChecked(self, key: str, state: bool):
        """
        Set checkbox state

        :param key: checkbox key
        :param state: state
        """
        if key in self.boxes:
            self.boxes[key].setChecked(state)
            # on update hooks
            self.window.controller.config.checkbox_list.on_update(
                self.parent_id,
                self.id,
                self.option,
                state,
                key
            )

    def isChecked(self, key: str) -> bool:
        """
        Get checkbox state

        :return: state
        """
        if key in self.boxes:
            return self.boxes[key].isChecked()
        return False
