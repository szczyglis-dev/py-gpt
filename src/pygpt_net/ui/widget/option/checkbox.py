#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.19 18:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QWidget

from pygpt_net.utils import trans


class OptionCheckbox(QWidget):
    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Settings checkbox

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(OptionCheckbox, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option
        self.value = False
        self.title = ""
        self.real_time = False

        # init from option data
        if self.option is not None:
            if "label" in self.option and self.option["label"] is not None \
                    and self.option["label"] != "":
                self.title = trans(self.option["label"])
            if "value" in self.option:
                self.value = self.option["value"]
            if "real_time" in self.option:
                self.real_time = self.option["real_time"]

        self.box = QCheckBox(self.title, self.window)
        self.box.setChecked(self.value)
        self.box.stateChanged.connect(
            lambda: self.window.controller.config.checkbox.on_update(
                self.parent_id,
                self.id,
                self.option,
                self.box.isChecked()
            )
        )

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.box)

        self.setLayout(self.layout)
