#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.11 05:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect, QSize, QPoint, QEvent
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
        # get available screen geometry
        screen = QApplication.primaryScreen()
        available_geometry = screen.availableGeometry()

        if self.store_geometry_enabled():
            data = self.window.core.config.get("layout.dialog.geometry", {})
        else:
            data = self.window.core.config.get_session("layout.dialog.geometry", {})

        if not isinstance(data, dict):
            data = {}

        item = data.get(self.id, {})
        if isinstance(item, dict) and "size" in item and "pos" in item:
            width, height = item["size"]
            x, y = item["pos"]
            width = min(width, available_geometry.width())
            height = min(height, available_geometry.height())
            size = QSize(width, height)
            # adjust position
            x = max(min(x, available_geometry.right() - width), available_geometry.left())
            y = max(min(y, available_geometry.bottom() - height), available_geometry.top())

            pos = QPoint(x, y)
            self.resize(size)
            self.move(pos)
