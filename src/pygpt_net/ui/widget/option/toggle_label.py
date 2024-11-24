#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.24 22:00:00                  #
# ================================================== #
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QWidget, QLabel

from pygpt_net.ui.widget.anims.toggles import AnimToggle
from pygpt_net.utils import trans


class ToggleLabel(QWidget):
    def __init__(
            self,
            title: str = None,
            label_position: str = 'right',
            icon=None,
            icon_size=24,
            parent=None,
    ):
        """
        Toggle checkbox with label

        :param title: label title
        """
        super(ToggleLabel, self).__init__()
        self.title = title
        self.label = QLabel(self.title)
        self.box = AnimToggle()

        ico = None
        if icon is not None:
            ico = QLabel()
            pixmap = QIcon(icon).pixmap(icon_size, icon_size)
            ico.setPixmap(pixmap)

        self.layout = QHBoxLayout()
        if label_position == 'left':
            if icon is not None:
                self.layout.addWidget(ico)
            self.layout.addWidget(self.label)
            self.layout.addWidget(self.box)
        else:
            self.layout.addWidget(self.box)
            if icon is not None:
                self.layout.addWidget(ico)
            self.layout.addWidget(self.label)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def setText(self, text: str):
        """
        Set label text

        :param text: text
        """
        self.label.setText(text)

    def setChecked(self, state: bool):
        """
        Set checkbox state

        :param state: state
        """
        self.box.setChecked(state)

    def isChecked(self) -> bool:
        """
        Get checkbox state

        :return: state
        """
        return self.box.isChecked()
