#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.19 17:00:00                  #
# ================================================== #
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QSplitter, QWidget

from .attachments import Attachments
from .attachments_uploaded import AttachmentsUploaded
from .contexts import Contexts
from .dialogs import Dialogs
from .menu import Menu
from .output import Output
from .toolbox import Toolbox


class UI:
    def __init__(self, window=None):
        """
        UI (main)

        :param window: Window instance
        """
        self.window = window

        # setup containers
        self.config_option = {}
        self.debug = {}
        self.dialog = {}
        self.editor = {}
        self.groups = {}
        self.menu = {}
        self.models = {}
        self.nodes = {}
        self.paths = {}
        self.plugin_addon = {}
        self.plugin_data = {}
        self.plugin_option = {}
        self.splitters = {}
        self.tabs = {}

        # setup builders
        self.attachments = Attachments(window)
        self.attachments_uploaded = AttachmentsUploaded(window)
        self.chat = Output(window)
        self.contexts = Contexts(window)
        self.dialogs = Dialogs(window)
        self.menus = Menu(window)
        self.toolbox = Toolbox(window)

    def setup(self):
        """Setup UI"""
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
        self.window.ui.splitters['main'] = QSplitter(Qt.Horizontal)
        self.window.ui.splitters['main'].addWidget(self.window.ctx)  # contexts
        self.window.ui.splitters['main'].addWidget(self.window.chat)  # chat box
        self.window.ui.splitters['main'].addWidget(self.window.toolbox)  # toolbox
        self.window.ui.splitters['main'].setSizes([1, 8, 1])

        # menu
        self.menus.setup()

        # dialogs
        self.dialogs.setup()

        # set central widget
        self.window.setCentralWidget(self.window.ui.splitters['main'])

    def setup_font(self):
        """Setup UI font"""
        path = os.path.join(self.window.config.get_root_path(), 'data', 'fonts', 'Lato', 'Lato-Regular.ttf')
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id == -1:
            print("Error loading font file {}".format(path))
