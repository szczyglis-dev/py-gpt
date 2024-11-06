#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QTabWidget
from pygpt_net.core.tabs.tab import Tab


class TabBody(QTabWidget):
    def __init__(self):
        super(TabBody, self).__init__()
        self.owner = None

    def setOwner(self, owner: Tab):
        """
        Set tab parent (owner)

        :param owner: parent tab instance
        """
        self.owner = owner

    def getOwner(self) -> Tab:
        """
        Get tab parent (owner)

        :return: parent tab instance
        """
        return self.owner