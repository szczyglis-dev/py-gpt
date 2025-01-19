#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.19 02:00:00                  #
# ================================================== #

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QTabWidget, QWidget

from pygpt_net.core.tabs.tab import Tab


class TabBody(QTabWidget):
    def __init__(self, window=None):
        super(TabBody, self).__init__()
        self.window = window
        self.owner = None
        self.body = []
        self.installEventFilter(self)

    def append(self, body: QWidget):
        """
        Append tab body (parent widget)

        :param body: tab body widget
        """
        self.body.append(body)

    def get_body(self):
        """
        Get tab body (parent widget)

        :return: tab body widget
        """
        return self.body

    def attach_tab(self, tab: Tab):
        """
        Attach tab to body

        :param tab: tab instance
        """
        for body in self.body:
            if hasattr(body, 'set_tab'):
                body.set_tab(tab)

    def setOwner(self, owner: Tab):
        """
        Set tab parent (owner)

        :param owner: parent tab instance
        """
        self.owner = owner
        self.attach_tab(owner)

    def getOwner(self) -> Tab:
        """
        Get tab parent (owner)

        :return: parent tab instance
        """
        return self.owner

    def eventFilter(self, source, event):
        """
        Focus event filter

        :param source: source
        :param event: event
        """
        if (event.type() == QEvent.ChildAdded and
                source is self and
                event.child().isWidgetType()):
            self._glwidget = event.child()
            self._glwidget.installEventFilter(self)
        elif (event.type() == event.Type.MouseButtonPress):
            # handle column focus
            if self.owner is not None:
                col_idx = self.owner.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
        return super().eventFilter(source, event)