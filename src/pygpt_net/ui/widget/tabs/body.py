#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.05 21:00:00                  #
# ================================================== #
from typing import Any

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QTabWidget, QWidget

from pygpt_net.core.tabs.tab import Tab


class TabBody(QTabWidget):
    def __init__(self, window=None):
        super(TabBody, self).__init__()
        self.window = window
        self.owner = None
        self.body = []
        self.refs = []
        self.on_delete = None  # callback on delete
        self.installEventFilter(self)

    def cleanup(self):
        """
        Clean up on delete
        """
        if self.on_delete:
            self.on_delete(self)
        self.delete_refs()

    def add_ref(self, ref: Any) -> None:
        """
        Add reference to widget in this tab

        :param ref: widget reference
        """
        if ref not in self.refs:
            self.refs.append(ref)

    def delete_refs(self) -> None:
        """
        Delete all references to widgets in this tab
        """
        for ref in self.refs:
            if ref and hasattr(ref, 'on_delete'):
                ref.on_delete()
            if ref and hasattr(ref, 'deleteLater'):
                ref.deleteLater()
        del self.refs[:]

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