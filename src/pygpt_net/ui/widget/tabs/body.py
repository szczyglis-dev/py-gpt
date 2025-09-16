#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.16 22:00:00                  #
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
        if self.on_delete and callable(self.on_delete):
            self.on_delete(self)
        self.delete_refs()

    def unwrap(self, widget: QWidget) -> None:
        """
        Remove widget from tab body

        :param widget: widget to remove
        """
        layout = self.layout()
        if layout is not None:
            layout.removeWidget(widget)
        self.delete_ref(widget)

    def unwrap_all(self) -> None:
        """
        Remove all widgets from tab body
        """
        layout = self.layout()
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                try:
                    layout.removeWidget(widget)
                except Exception:
                    pass
                try:
                    self.delete_ref(widget)
                except Exception:
                    pass

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
            if ref is None:
                continue
            if ref and hasattr(ref, 'on_delete'):
                try:
                    ref.on_delete()
                except Exception:
                    pass
            if ref and hasattr(ref, 'deleteLater'):
                try:
                    ref.deleteLater()
                except Exception:
                    pass
        del self.refs[:]

    def delete_ref(self, widget: Any) -> None:
        """
        Unpin reference to widget in this tab

        :param widget: widget reference
        """
        for ref in self.refs:
            if ref and ref is widget:
                self.refs.remove(ref)
                break

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
        t = event.type()
        if (t == QEvent.ChildAdded and
                source is self and
                event.child().isWidgetType()):
            self._glwidget = event.child()
            self._glwidget.installEventFilter(self)
        elif t == event.Type.MouseButtonPress:
            # handle column focus
            if self.owner is not None:
                col_idx = self.owner.column_idx
                self.window.controller.ui.tabs.on_column_focus(col_idx)
        return super().eventFilter(source, event)

    def to_dict(self) -> dict:
        """
        Convert to dict

        :return: dict
        """
        return {
            "refs": [str(ref) for ref in self.refs],  # references to widgets
            "body": [str(b) for b in self.body],  # body widgets
            "len(layout)": self.layout().count() if self.layout() else 0,
        }