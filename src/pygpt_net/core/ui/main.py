#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.04.14 20:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QWidget

from .chatbox import ChatBox
from .toolbox import Toolbox
from .menu import Menu
from .dialogs import Dialogs
from .contexts import Contexts
from .attachments import Attachments


class UI:
    def __init__(self, window=None):
        """
        UI (main)

        :param window: main UI window object
        """
        self.window = window
        self.window.data = {}
        self.window.plugin_data = {}
        self.window.menus = {}
        self.window.models = {}
        self.window.path_label = {}
        self.window.config_option = {}
        self.window.plugin_option = {}

        self.chat = ChatBox(window)
        self.toolbox = Toolbox(window)
        self.contexts = Contexts(window)
        self.attachments = Attachments(window)
        self.menu = Menu(window)
        self.dialogs = Dialogs(window)

    def setup(self):
        """Setups UI"""
        # chat and toolbox
        self.window.chat = self.chat.setup()
        self.window.toolbox = self.toolbox.setup()

        # ctx
        self.window.ctx = QWidget()
        self.window.ctx.setLayout(self.contexts.setup())

        # set width
        self.window.ctx.setMinimumWidth(200)

        # horizontal splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.window.ctx)  # contexts
        splitter.addWidget(self.window.chat)  # chat box
        splitter.addWidget(self.window.toolbox)  # toolbox
        #splitter.setStretchFactor(0, 3)
        #splitter.setStretchFactor(2, 9)
        #splitter.setStretchFactor(1, 3)
        splitter.setSizes([1, 8, 1])

        # menu
        self.menu.setup()

        # dialogs
        self.dialogs.setup()

        # set central widget
        self.window.setCentralWidget(splitter)
