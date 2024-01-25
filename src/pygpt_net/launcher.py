#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.25 11:00:00                  #
# ================================================== #

import sys

from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QApplication

from pygpt_net.core.platforms import Platforms
from pygpt_net.ui.main import MainWindow


class Launcher:
    def __init__(self):
        """Launcher"""
        self.app = None
        self.window = None

    def init(self):
        """Initialize app"""
        Platforms.prepare()  # setup platform specific options
        self.app = QApplication(sys.argv)
        self.window = MainWindow(self.app)
        self.app.setWindowIcon(self.window.ui.get_app_icon())
        self.app.aboutToQuit.connect(self.app.quit)
        self.window.ui.tray.setup(self.app)

    def add_plugin(self, plugin=None):
        """
        Register plugin

        :param plugin: plugin instance
        """
        self.window.add_plugin(plugin)

    def add_llm(self, llm=None):
        """
        Register LLM wrapper

        :param llm: LLM wrapper instance
        """
        self.window.add_llm(llm)

    def add_vector_store(self, store=None):
        """
        Register vector index store provider

        :param store: Vector index store provider instance
        """
        self.window.add_vector_store(store)

    def run(self):
        """Run app"""
        margin = 50
        self.window.setup()
        geometry = self.window.screen().availableGeometry()
        pos = QScreen.availableGeometry(QApplication.primaryScreen()).topLeft()
        self.window.resize(geometry.width() - margin, geometry.height() - margin)
        self.window.show()
        self.window.move(pos)
        self.window.post_setup()
        sys.exit(self.app.exec())
