#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.27 10:15:00                  #
# ================================================== #
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QWidget, QLabel, QSizePolicy

from pygpt_net.ui.widget.anims.toggles import AnimToggle
from pygpt_net.ui.widget.element.labels import ElideLabel


class ToggleLabel(QWidget):
    def __init__(
            self,
            title: str = None,
            label_position: str = 'right',
            icon=None,
            icon_size=24,
            parent=None,
            elide_label: bool = False,
    ):
        """
        Toggle checkbox with label

        :param title: label title
        :param label_position: label position relative to the toggle
        :param icon: optional icon path
        :param icon_size: icon size
        :param parent: parent widget
        :param elide_label: whether to shorten the label when horizontal space is limited
        """
        super(ToggleLabel, self).__init__()
        self.title = title or ""
        if elide_label:
            self.label = ElideLabel(self.title)
        else:
            self.label = QLabel(self.title)
            self.label.setWordWrap(False)
            self.label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
            self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.box = AnimToggle('', parent)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        ico = None
        if icon is not None:
            ico = QLabel()
            pixmap = QIcon(icon).pixmap(icon_size, icon_size)
            ico.setPixmap(pixmap)

        self.layout = QHBoxLayout()
        if label_position == 'left':
            if icon is not None:
                self.layout.addWidget(ico)
            self.layout.addWidget(self.label, 1)
            self.layout.addWidget(self.box, 0)
        else:
            self.layout.addWidget(self.box, 0)
            if icon is not None:
                self.layout.addWidget(ico, 0)
            self.layout.addWidget(self.label, 1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def setText(self, text: str):
        """
        Set label text

        :param text: text
        """
        self.title = "" if text is None else str(text)
        self.label.setText(self.title)

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
