#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.01 15:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QCheckBox, QWidget, QPushButton
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize, Qt

from pygpt_net.ui.base.flow_layout import FlowLayout
from pygpt_net.utils import trans

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

        # overlay button config
        self._overlay_margin = 4  # px
        self.btn_select = None

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

        # do not add the select/unselect all button to the flow layout
        # it will be overlaid in the top-right corner to avoid affecting layout flow
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        # overlay select/unselect all button pinned to top-right corner
        self.btn_select = QPushButton(self)
        self.btn_select.setObjectName("btn_select_all_overlay")
        self.btn_select.setToolTip(trans("action.select_unselect_all"))
        self.btn_select.setIcon(QIcon(":/icons/asterisk.svg"))
        self.btn_select.setIconSize(QSize(16, 16))
        self.btn_select.setFixedSize(22, 22)
        self.btn_select.setFocusPolicy(Qt.NoFocus)
        self.btn_select.setCursor(Qt.PointingHandCursor)
        self.btn_select.setStyleSheet("QPushButton { border: none; padding: 0; background: transparent; }")
        self.btn_select.clicked.connect(
            lambda: self.window.controller.config.checkbox_list.on_select_all(
                self.parent_id,
                self.id,
                self.option
            )
        )
        self.btn_select.raise_()
        self._place_select_button()

    def _place_select_button(self) -> None:
        """
        Place the overlay select/unselect button in the top-right corner.
        """
        if not self.btn_select:
            return
        m = self._overlay_margin
        w = self.btn_select.width()
        x = max(0, self.width() - w - m)
        y = m
        self.btn_select.move(x, y)

    def resizeEvent(self, event):
        """
        Keep the overlay button pinned to the top-right on resize.
        """
        super().resizeEvent(event)
        self._place_select_button()

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

        # keep the overlay button in place after list update
        self._place_select_button()

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