#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenuBar, QVBoxLayout, QHBoxLayout, QSizePolicy

from pygpt_net.ui.widget.dialog.base import BaseDialog
from pygpt_net.ui.widget.image.display import ImageLabel
from pygpt_net.utils import trans

class DialogSpawner:
    def __init__(self, window=None):
        """
        Image viewer dialog spawner

        :param window: Window instance
        """
        self.window = window
        self.path = None
        self.id = 'image_preview'

    def setup(self, id: str = None) -> BaseDialog:
        """
        Setup image viewer dialog

        :param id: dialog id
        :return: BaseDialog instance
        """
        dialog = ImageViewerDialog(self.window, self.id)
        dialog.disable_geometry_store = True  # disable geometry store
        dialog.id = id

        source = ImageLabel(dialog, self.path)
        source.setVisible(False)
        pixmap = ImageLabel(dialog, self.path)
        pixmap.setSizePolicy(QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored))

        row = QHBoxLayout()
        row.addWidget(pixmap)

        layout = QVBoxLayout()
        layout.addLayout(row)

        dialog.append_layout(layout)
        dialog.source = source
        dialog.pixmap = pixmap

        return dialog


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
        self.menu_bar = None
        self.file_menu = None
        self.actions = {}
        self.source = None
        self.pixmap = None
        self._last_src_key = 0
        self._last_target_size = None
        self._icon_add = QIcon(":/icons/add.svg")
        self._icon_folder = QIcon(":/icons/folder.svg")
        self._icon_save = QIcon(":/icons/save.svg")
        self._icon_logout = QIcon(":/icons/logout.svg")

    def append_layout(self, layout):
        """
        Update layout

        :param layout: layout
        """
        layout.setMenuBar(self.setup_menu())
        self.setLayout(layout)

    def resizeEvent(self, event):
        """
        Resize event to adjust the pixmap on window resizing

        :param event: resize event
        """
        src = self.source.pixmap() if self.source is not None else None
        if src and not src.isNull() and self.pixmap is not None:
            target_size = self.pixmap.size()
            key = src.cacheKey()
            if key != self._last_src_key or target_size != self._last_target_size:
                self.pixmap.setPixmap(
                    src.scaled(
                        target_size,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                )
                self._last_src_key = key
                self._last_target_size = target_size
        super(ImageViewerDialog, self).resizeEvent(event)

    def setup_menu(self) -> QMenuBar:
        """
        Setup dialog menu

        :return: QMenuBar
        """
        self.menu_bar = QMenuBar(self)
        self.file_menu = self.menu_bar.addMenu(trans("menu.file"))

        self.actions["new"] = QAction(self._icon_add, trans("action.new"), self)
        self.actions["new"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").new()
        )

        self.actions["open"] = QAction(self._icon_folder, trans("action.open"), self)
        self.actions["open"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").open_file(self.id, auto_close=True)
        )

        self.actions["open_new"] = QAction(self._icon_folder, trans("action.open_new_window"), self)
        self.actions["open_new"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").open_file(self.id, auto_close=False)
        )

        self.actions["save_as"] = QAction(self._icon_save, trans("action.save_as"), self)
        self.actions["save_as"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").save_by_id(self.id)
        )

        self.actions["exit"] = QAction(self._icon_logout, trans("menu.file.exit"), self)
        self.actions["exit"].triggered.connect(
            lambda checked=False: self.window.tools.get("viewer").close_preview(self.id)
        )

        self.file_menu.addAction(self.actions["new"])
        self.file_menu.addAction(self.actions["open"])
        self.file_menu.addAction(self.actions["open_new"])
        self.file_menu.addAction(self.actions["save_as"])
        self.file_menu.addAction(self.actions["exit"])

        return self.menu_bar