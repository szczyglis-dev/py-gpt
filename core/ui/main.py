#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QWidget
from core.ui.chatbox import ChatBox
from core.ui.toolbox import Toolbox
from core.ui.menu import Menu
from core.ui.dialogs import Dialogs
from core.ui.contexts import Contexts


class UI:
    def __init__(self, window=None):
        """
        UI (main)

        :param window: main UI window object
        """
        self.window = window
        self.window.data = {}
        self.window.menus = {}
        self.window.models = {}
        self.window.path_label = {}
        self.window.config_option = {}

        self.chat = ChatBox(window)
        self.toolbox = Toolbox(window)
        self.contexts = Contexts(window)
        self.menu = Menu(window)
        self.dialogs = Dialogs(window)

    def setup(self):
        """Setup UI"""
        # chat and toolbox
        self.window.chat = self.chat.setup()
        self.window.toolbox = self.toolbox.setup()

        # ctx
        self.window.ctx = QWidget()
        self.window.ctx.setLayout(self.contexts.setup())

        # set width
        self.window.ctx.setMinimumWidth(self.window.config.data['ui.ctx.min_width'])
        # self.window.ctx.setMaximumWidth(self.window.config.data['ui.ctx.max_width'])
        # self.window.toolbox.setMinimumWidth(self.window.config.data['ui.toolbox.min_width'])
        # self.window.toolbox.setMaximumWidth(self.window.config.data['ui.toolbox.max_width'])

        # horizontal splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.window.ctx)  # contexts
        splitter.addWidget(self.window.toolbox)  # toolbox
        splitter.addWidget(self.window.chat)  # chat box
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 9)
        # splitter.setSizes([1, 1, 7])

        # menu
        self.menu.setup()

        # dialogs
        self.dialogs.setup()

        # set central widget
        self.window.setCentralWidget(splitter)
