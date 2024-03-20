#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.20 06:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenuBar

from pygpt_net.utils import trans
from .base import BaseDialog


class ImageDialog(BaseDialog):
    def __init__(self, window=None, id=None):
        """
        Image dialog

        :param window: main window
        :param id: info window id
        """
        super(ImageDialog, self).__init__(window, id)
        self.window = window
        self.id = id


class ImageViewerDialog(BaseDialog):
    def __init__(self, window=None, id=None):
        """
        Image viewer dialog

        :param window: main window
        :param id: info window id
        """
        super(ImageViewerDialog, self).__init__(window, id)
        self.window = window
        self.id = id
        self.disable_geometry_store = False
        self.resizeEvent = self.onResizeEvent  # resize event to adjust the pixmap
        self.source = None
        self.pixmap = None

    def append_layout(self, layout):
        """
        Update layout

        :param layout: layout
        """
        layout.setMenuBar(self.setup_menu())  # attach menu
        self.setLayout(layout)

    def onResizeEvent(self, event):
        """
        Resize event to adjust the pixmap on window resizing

        :param event: resize event
        """
        if self.source.pixmap() and not self.source.pixmap().isNull():
            self.pixmap.setPixmap(
                self.source.pixmap().scaled(
                    self.pixmap.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )
        super(ImageViewerDialog, self).resizeEvent(event)

    def setup_menu(self) -> QMenuBar:
        """
        Setup dialog menu

        :return: QMenuBar
        """
        self.menu_bar = QMenuBar()
        self.file_menu = self.menu_bar.addMenu(trans("menu.file"))
        self.actions = {}

        # new
        self.actions["new"] = QAction(QIcon(":/icons/add.svg"), trans("action.new"))
        self.actions["new"].triggered.connect(
            lambda: self.window.tools.viewer.new()
        )

        # open
        self.actions["open"] = QAction(QIcon(":/icons/folder.svg"), trans("action.open"))
        self.actions["open"].triggered.connect(
            lambda: self.window.tools.viewer.open_file(self.id, auto_close=True)
        )

        # open (new window)
        self.actions["open_new"] = QAction(QIcon(":/icons/folder.svg"), trans("action.open_new_window"))
        self.actions["open_new"].triggered.connect(
            lambda: self.window.tools.viewer.open_file(self.id, auto_close=False)
        )

        # save as
        self.actions["save_as"] = QAction(QIcon(":/icons/save.svg"), trans("action.save_as"))
        self.actions["save_as"].triggered.connect(
            lambda: self.window.tools.viewer.save_by_id(self.id)
        )

        # exit
        self.actions["exit"] = QAction(QIcon(":/icons/logout.svg"), trans("menu.file.exit"))
        self.actions["exit"].triggered.connect(
            lambda: self.window.tools.viewer.close_preview(self.id)
        )

        # add actions
        self.file_menu.addAction(self.actions["new"])
        self.file_menu.addAction(self.actions["open"])
        self.file_menu.addAction(self.actions["open_new"])
        self.file_menu.addAction(self.actions["save_as"])
        self.file_menu.addAction(self.actions["exit"])

        return self.menu_bar
