#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.29 16:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QSplitter, QMessageBox

from pygpt_net.ui.dialogs import Dialogs
from pygpt_net.ui.layout.chat import ChatMain
from pygpt_net.ui.layout.ctx import CtxMain
from pygpt_net.ui.layout.toolbox import ToolboxMain
from pygpt_net.ui.menu import Menu
from pygpt_net.ui.tray import Tray


class UI:

    STATUS_MAX_CHARS = 80

    def __init__(self, window=None):
        """
        UI (main)

        :param window: Window instance
        """
        self.window = window

        # bags
        self.calendar = {}
        self.config = {
            "assistant": {},
            "config": {},
            "global": {},
            "preset": {},
        }
        self.hooks = {}
        self.debug = {}
        self.dialog = {}
        self.editor = {}
        self.groups = {}
        self.menu = {}
        self.models = {}
        self.nodes = {}
        self.notepad = {}
        self.parts = {}
        self.paths = {}
        self.plugin_addon = {}
        self.splitters = {}
        self.tabs = {}
        self.tray_menu = {}

        # builders
        self.chat = ChatMain(window)
        self.contexts = CtxMain(window)
        self.dialogs = Dialogs(window)
        self.menus = Menu(window)
        self.toolbox = ToolboxMain(window)
        self.tray = Tray(window)

    def init(self):
        """Setup UI"""
        # load font
        self.setup_font()

        # ctx, chat and toolbox
        self.parts['ctx'] = self.contexts.setup()
        self.parts['chat'] = self.chat.setup()
        self.parts['toolbox'] = self.toolbox.setup()

        # set width
        self.parts['ctx'].setMinimumWidth(200)

        # horizontal splitter
        self.splitters['main'] = QSplitter(Qt.Horizontal)
        self.splitters['main'].addWidget(self.parts['ctx'])  # contexts
        self.splitters['main'].addWidget(self.parts['chat'])  # chat box
        self.splitters['main'].addWidget(self.parts['toolbox'])  # toolbox

        self.splitters['main'].setStretchFactor(0, 3)
        self.splitters['main'].setStretchFactor(1, 5)
        self.splitters['main'].setStretchFactor(2, 1)

        # menus
        self.menus.setup()

        # dialogs
        self.dialogs.setup()

        # set central widget
        self.window.setCentralWidget(self.window.ui.splitters['main'])

        # set window title
        self.window.setWindowTitle(
            'PyGPT - Desktop AI Assistant v{} | build {}'.format(self.window.meta['version'],
                                                                 self.window.meta['build'])
        )

    def post_setup(self):
        """Post setup UI (just before show)"""
        self.dialogs.post_setup()

    def status(self, text):
        """
        Update status text

        :param text: status text
        """
        msg = str(text)
        status = msg[:self.STATUS_MAX_CHARS] + '...' if len(msg) > self.STATUS_MAX_CHARS else msg  # truncate
        self.nodes['status'].setText(status)

    def setup_font(self):
        """Setup UI font"""
        path = os.path.join(
            self.window.core.config.get_app_path(),
            'data',
            'fonts',
            'Lato',
            'Lato-Regular.ttf'
        )
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id == -1:
            print("Error loading font file {}".format(path))

    def msg(self, msg: str):
        """
        Show message box

        :param msg: Message
        """
        msg_box = QMessageBox()
        msg_box.setText(msg)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setDefaultButton(QMessageBox.Ok)
        msg_box.exec_()

    def add_hook(self, name: str, callback: callable):
        """
        Add hook

        :param name: Hook name
        :param callback: Callback function
        """
        self.hooks[name] = callback

    def has_hook(self, name: str) -> bool:
        """
        Check if hook exists

        :param name: Hook name
        :return: True if hook exists
        """
        return name in self.hooks

    def get_hook(self, name: str) -> callable:
        """
        Get hook

        :param name: Hook name
        :return: Hook callback
        """
        return self.hooks[name]

    def get_app_icon(self) -> QIcon:
        """
        Get app icon

        :return: App icon
        """
        return QIcon(os.path.join(
            self.window.core.config.get_app_path(),
            'data',
            'icon.ico'
        ))

    def get_tray_icon(self, state: str = "idle") -> QIcon:
        """
        Get tray icon

        :param state: Tray state
        :return: Tray icon
        """
        if state == self.window.STATE_IDLE:
            icon = "icon_tray_idle.ico"
        elif state == self.window.STATE_BUSY:
            icon = "icon_tray_busy.ico"
        elif state == self.window.STATE_ERROR:
            icon = "icon_tray_error.ico"
        else:
            icon = "icon_tray_idle.ico"
        return QIcon(os.path.join(
            self.window.core.config.get_app_path(),
            'data',
            icon
        ))
