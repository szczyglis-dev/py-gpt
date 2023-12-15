#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.08 22:00:00                  #
# ================================================== #
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QSplitter, QWidget

from .chatbox import ChatBox
from .toolbox import Toolbox
from .menu import Menu
from .dialogs import Dialogs
from .contexts import Contexts
from .attachments import Attachments
from .attachments_uploaded import AttachmentsUploaded


class UI:
    def __init__(self, window=None):
        """
        UI (main)

        :param window: main UI window object
        """
        self.window = window
        self.window.data = {}
        self.window.menus = {}
        self.window.splitters = {}
        self.window.tabs = {}
        self.window.models = {}
        self.window.groups = {}
        self.window.path_label = {}
        self.window.config_option = {}
        self.window.plugin_data = {}
        self.window.plugin_option = {}
        self.window.plugin_addon = {}

        self.chat = ChatBox(window)
        self.toolbox = Toolbox(window)
        self.contexts = Contexts(window)
        self.attachments = Attachments(window)
        self.attachments_uploaded = AttachmentsUploaded(window)
        self.menu = Menu(window)
        self.dialogs = Dialogs(window)

    def setup(self):
        """Setups UI"""
        # load font
        self.setup_font()

        # chat and toolbox
        self.window.chat = self.chat.setup()
        self.window.toolbox = self.toolbox.setup()

        # ctx
        self.window.ctx = QWidget()
        self.window.ctx.setLayout(self.contexts.setup())

        # set width
        self.window.ctx.setMinimumWidth(200)

        # horizontal splitter
        self.window.splitters['main'] = QSplitter(Qt.Horizontal)
        self.window.splitters['main'].addWidget(self.window.ctx)  # contexts
        self.window.splitters['main'].addWidget(self.window.chat)  # chat box
        self.window.splitters['main'].addWidget(self.window.toolbox)  # toolbox
        self.window.splitters['main'].setSizes([1, 8, 1])

        # menu
        self.menu.setup()

        # dialogs
        self.dialogs.setup()

        # set central widget
        self.window.setCentralWidget(self.window.splitters['main'])

    def setup_font(self):
        """Setups UI font"""
        path = os.path.join(self.window.config.get_root_path(), 'data', 'fonts', 'Lato', 'Lato-Regular.ttf')
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id == -1:
            print("Error loading font file {}".format(path))
        else:
            family = QFontDatabase.applicationFontFamilies(font_id)[0]
