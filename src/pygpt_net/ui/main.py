#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QSplitter

from pygpt_net.ui.dialogs import Dialogs
from pygpt_net.ui.layout.chat.main import ChatMain
from pygpt_net.ui.layout.ctx.main import CtxMain
from pygpt_net.ui.layout.toolbox.main import ToolboxMain
from pygpt_net.ui.menu import Menu


class UI:
    def __init__(self, window=None):
        """
        UI (main)

        :param window: Window instance
        """
        self.window = window

        # prepare
        self.config_option = {}
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
        self.plugin_data = {}
        self.plugin_option = {}
        self.splitters = {}
        self.tabs = {}

        # builders
        self.chat = ChatMain(window)
        self.contexts = CtxMain(window)
        self.dialogs = Dialogs(window)
        self.menus = Menu(window)
        self.toolbox = ToolboxMain(window)

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
        self.splitters['main'].setSizes([1, 8, 1])

        # menus
        self.menus.setup()

        # dialogs
        self.dialogs.setup()

        # set central widget
        self.window.setCentralWidget(self.window.ui.splitters['main'])

    def setup_font(self):
        """Setup UI font"""
        path = os.path.join(self.window.app.config.get_root_path(), 'data', 'fonts', 'Lato', 'Lato-Regular.ttf')
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id == -1:
            print("Error loading font file {}".format(path))
