#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.02 14:00:00                  #
# ================================================== #

import sys

from PySide6.QtGui import QScreen
from PySide6.QtCore import QTimer, Signal, Slot
from PySide6.QtWidgets import (QApplication, QMainWindow)
from qt_material import QtStyleTools

from .config import Config
from .ui.main import UI
from .controller.main import Controller
from .debugger import Debug
from .settings import Settings
from .info import Info
from .gpt import Gpt
from .image import Image
from .utils import get_init_value

from .plugin.self_loop.plugin import Plugin as SelfLoopPlugin
from .plugin.real_time.plugin import Plugin as RealTimePlugin
from .plugin.web_search.plugin import Plugin as WebSearchPlugin
from .plugin.audio_azure.plugin import Plugin as AudioAzurePlugin
from .plugin.audio_openai_tts.plugin import Plugin as AudioOpenAITTSPlugin


class MainWindow(QMainWindow, QtStyleTools):
    statusChanged = Signal(str)

    def __init__(self):
        """App main window"""
        super().__init__()
        self.timer = None
        self.github = get_init_value("__github__")
        self.website = get_init_value("__website__")
        self.version = get_init_value("__version__")
        self.build = get_init_value("__build__")
        self.author = get_init_value("__author__")
        self.email = get_init_value("__email__")
        self.data = {}

        # setup config
        self.config = Config()
        self.config.init(True, True)

        # app controller
        self.controller = Controller(self)
        self.debugger = Debug(self)
        self.info = Info(self)
        self.settings = Settings(self)

        # handle config migration if needed
        self.controller.launcher.migrate_version()

        # setup GPT and DALL-E
        self.gpt = Gpt(self.config)
        self.images = Image(self.config)

        # setup UI
        self.ui = UI(self)
        self.ui.setup()

        self.setWindowTitle('PYGPT.net v{} | build {}'.format(self.version, self.build))

        # setup signals
        self.statusChanged.connect(self.update_status)

    def log(self, data):
        """
        Logs data to console

        :param text: text to log
        """
        self.controller.debug.log(data)

    def set_theme(self, theme='dark_teal.xml'):
        """
        Updates theme

        :param theme: theme name
        """
        label = "#ffffff"
        inverse = False
        if theme.startswith('light_'):
            label = "#000000"
            inverse = True
        extra = {
            'density_scale': '-2',
            'pyside6': True,
            'QLineEdit': {
                'color': label,
            },
        }
        self.setStyleSheet(self.controller.theme.get_style('line_edit'))  # fix for line edit
        self.apply_stylesheet(self, theme, invert_secondary=inverse, extra=extra)

    def add_plugin(self, plugin):
        """
        Adds plugin

        :param plugin: plugin instance
        """
        plugin.attach(self)
        self.controller.plugins.register(plugin)

    def setup_plugins(self):
        self.controller.plugins.setup()

    def setup(self):
        """Setups app"""
        self.controller.setup()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(30)

    def update(self):
        """Called on update"""
        self.debugger.update()

    def set_status(self, text):
        """
        Updates status text

        :param text: status text
        """
        self.data['status'].setText(str(text))

    @Slot(str)
    def update_status(self, text):
        self.set_status(text)

    def closeEvent(self, event):
        """
        Handles close event

        :param event: close event
        """
        print("Closing...")
        print("Saving config...")
        self.timer.stop()
        self.config.save()
        print("Saving presets...")
        self.config.save_presets()
        print("Exiting...")
        event.accept()  # let the window close


class Launcher:
    def __init__(self):
        """Launcher"""
        self.app = None
        self.window = None

    def init(self):
        """Initializes app"""
        self.app = QApplication(sys.argv)
        self.window = MainWindow()
        self.app.aboutToQuit.connect(self.app.quit)

    def add_plugin(self, plugin=None):
        """
        Registers plugin

        :param plugin: plugin instance
        """
        self.window.add_plugin(plugin)
        self.window.setup_plugins()

    def run(self):
        """Runs app"""
        self.window.setup()
        available_geometry = self.window.screen().availableGeometry()
        pos = QScreen.availableGeometry(QApplication.primaryScreen()).topLeft()
        self.window.resize(available_geometry.width() - 50, available_geometry.height() - 50)
        # self.window.showMaximized()
        self.window.show()
        self.window.move(pos)

        try:
            sys.exit(self.app.exec())
        except SystemExit:
            print("Closing...")


def run():
    """Runs app"""
    # initialize app
    launcher = Launcher()
    launcher.init()

    # add plugins
    launcher.add_plugin(SelfLoopPlugin())
    launcher.add_plugin(RealTimePlugin())
    launcher.add_plugin(WebSearchPlugin())
    launcher.add_plugin(AudioAzurePlugin())
    launcher.add_plugin(AudioOpenAITTSPlugin())

    # run app
    launcher.run()
