#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.19 01:00:00                  #
# ================================================== #

from PySide6.QtCore import QEvent, QSize, QPoint
from PySide6.QtWidgets import QDialog


class BaseDialog(QDialog):
    def __init__(self, window=None, id=None):
        """
        Base dialog

        :param window: main window
        :param id: dialog id
        """
        super(BaseDialog, self).__init__(window)
        self.window = window
        self.id = id
        self.disable_geometry_store = False

    def showEvent(self, event):
        """
        Event called when the dialog is shown

        :param event: show event
        """
        super(BaseDialog, self).showEvent(event)
        if event.type() == QEvent.Show:
            self.restore_geometry()

    def closeEvent(self, event):
        """
        Event called when the dialog is closed

        :param event: close event
        """
        self.save_geometry()
        super(BaseDialog, self).closeEvent(event)

    def store_geometry_enabled(self) -> bool:
        """
        Check if the geometry store is enabled

        :return: True if enabled
        """
        if self.disable_geometry_store:
            return False

        if self.window is None or self.id is None:
            return False

        if not self.window.core.config.has("layout.dialog.geometry.store") \
                or not self.window.core.config.get("layout.dialog.geometry.store"):
            return False

        return True

    def save_geometry(self):
        """Save dialog geometry"""
        item = {
            "size": [self.size().width(), self.size().height()],
            "pos": [self.pos().x(), self.pos().y()]
        }
        if self.store_geometry_enabled():
            data = self.window.core.config.get("layout.dialog.geometry", {})
        else:
            data = self.window.core.config.get_session("layout.dialog.geometry", {})

        if not isinstance(data, dict):
            data = {}
        data[self.id] = item

        if self.store_geometry_enabled():
            self.window.core.config.set("layout.dialog.geometry", data)
        else:
            self.window.core.config.set_session("layout.dialog.geometry", data)

    def restore_geometry(self):
        """Restore dialog geometry"""
        if self.store_geometry_enabled():
            data = self.window.core.config.get("layout.dialog.geometry", {})
        else:
            data = self.window.core.config.get_session("layout.dialog.geometry", {})
        if not isinstance(data, dict):
            data = {}
        item = data.get(self.id, {})
        if isinstance(item, dict):
            if "size" in item and "pos" in item:
                size = QSize(item["size"][0], item["size"][1])
                pos = QPoint(item["pos"][0], item["pos"][1])
                self.resize(size)
                self.move(pos)
