#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.12 00:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import Qt

class ModelComboBox(QComboBox):
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