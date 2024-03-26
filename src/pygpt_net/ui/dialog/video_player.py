#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.25 10:00:00                  #
# ================================================== #

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QVBoxLayout, QMenuBar

from pygpt_net.ui.widget.dialog.video_player import VideoPlayerDialog
from pygpt_net.ui.widget.video.player import VideoPlayerWidget

from pygpt_net.utils import trans
import pygpt_net.icons_rc


class VideoPlayer:
    def __init__(self, window=None):
        """
        Video Player dialog

        :param window: Window instance
        """
        self.window = window
        self.path = None

    def setup_menu(self) -> QMenuBar:
        """Setup video dialog menu"""
        self.menu_bar = QMenuBar()
        self.file_menu = self.menu_bar.addMenu(trans("menu.file"))
        self.actions = {}

        # open
        self.actions["open"] = QAction(QIcon(":/icons/folder.svg"), trans("action.open"))
        self.actions["open"].triggered.connect(
            lambda: self.window.tools.get("player").open_file()
        )

        # save as
        self.actions["save_as"] = QAction(QIcon(":/icons/save"), trans("action.save_as"))
        self.actions["save_as"].triggered.connect(
            lambda: self.window.tools.get("player").save_as_file()
        )

        # exit
        self.actions["exit"] = QAction(QIcon(":/icons/logout.svg"), trans("menu.file.exit"))
        self.actions["exit"].triggered.connect(
            lambda: self.window.tools.get("player").close()
        )

        # add actions
        self.file_menu.addAction(self.actions["open"])
        self.file_menu.addAction(self.actions["save_as"])
        self.file_menu.addAction(self.actions["exit"])
        return self.menu_bar

    def setup(self):
        """Setup video dialog"""
        id = 'video_player'
        self.window.video_player = VideoPlayerWidget(self.window)

        layout = QVBoxLayout()
        layout.setMenuBar(self.setup_menu())
        layout.addWidget(self.window.video_player)

        self.window.ui.dialog[id] = VideoPlayerDialog(self.window, id)
        self.window.ui.dialog[id].setLayout(layout)
        self.window.ui.dialog[id].setWindowTitle("Media Player")
