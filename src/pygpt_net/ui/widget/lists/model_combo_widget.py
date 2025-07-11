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
        """
        index = self.count()
        self.addItem(text)
        item = self.model().item(index)
        if item is not None:
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)