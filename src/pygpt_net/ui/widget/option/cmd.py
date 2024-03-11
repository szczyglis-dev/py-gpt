#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.11 01:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex, QSize
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTreeView, QMenu, QStyledItemDelegate, QComboBox, \
    QCheckBox, QSizePolicy

from pygpt_net.ui.widget.option.checkbox import OptionCheckbox
from pygpt_net.ui.widget.option.dictionary import OptionDict
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class OptionCmd(QWidget):
    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Settings dictionary items

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(OptionCmd, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option  # option data

        # TODO: implement cmd type option

        # prepare options
        option_enabled = {}
        option_enabled["type"] = "bool"
        option_enabled["label"] = ""

        if self.option["value"] is not None and "cmd" in self.option["value"]:
            option_enabled["label"] = "Command: " + self.option["value"]["cmd"]
        option_enabled["description"] = "Test description"
        option_enabled["value"] = True

        option_params = {}
        option_params["name"] = "params"
        option_params["type"] = "dict"
        option_params["keys"] = {
            "name": "text",
            "type": "text",
            "description": "text",
            "required": "bool",
        }
        option_params["value"] = []

        if self.option["value"] is not None and "params" in self.option["value"]:
            option_params["value"] = self.option["value"]["params"]

        key_enabled = self.id + ".enabled"
        key_params = self.id + ".params"

        self.enabled = OptionCheckbox(self.window, parent_id, key_enabled, option_enabled)  # enable checkbox
        self.params = OptionDict(self.window, parent_id, key_params, option_params)  # command params

        # layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.enabled)
        self.layout.addWidget(self.params)
        self.setLayout(self.layout)

        # update
        self.update()

    def update_item(self, idx, data):
        """
        Update item in params list

        :param idx: Item index
        :param data: Item data
        """
        self.params.update_item(idx, data)

    def update(self):
        """Update widget"""
        pass