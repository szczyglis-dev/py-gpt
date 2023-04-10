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

import sys

from PySide6.QtGui import QScreen
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (QApplication, QMainWindow, QStyleFactory)
from qt_material import apply_stylesheet

from core.config import Config
from core.ui.main import UI
from core.controller.main import Controller
from core.debugger import Debug
from core.settings import Settings
from core.info import Info
from core.gpt import Gpt
from core.image import Image
from core.utils import get_init_value


class MainWindow(QMainWindow):
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
        self.config.init()

        # app controller
        self.controller = Controller(self)
        self.debugger = Debug(self)
        self.info = Info(self)
        self.settings = Settings(self)

        # setup GPT and DALL-E
        self.gpt = Gpt(self.config)
        self.images = Image(self.config)

        # setup UI
        self.ui = UI(self)
        self.ui.setup()

        self.setup()
        self.setWindowTitle('PYGPT.net v{} | build {}'.format(self.version, self.build))

    def setup(self):
        """Setup app"""
        self.controller.setup()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(30)

    def update(self):
        """On update"""
        self.debugger.update()

    def set_status(self, text):
        """Set status"""
        self.data['status'].setText(str(text))

    def closeEvent(self, event):
        """
        Handle close event

        :param event: close event
        """
        print("Closing...")
        print("Saving config...")
        self.config.save_config()
        print("Saving presets...")
        self.config.save_presets()
        print("Exiting...")
        event.accept()  # let the window close


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    # sys.excepthook = except_hook

    app = QApplication(sys.argv)
   
    window = MainWindow()
    window.setStyle(QStyleFactory.create('Plastique'))
    window.setStyleSheet("QLineEdit { color: #fff; }")
    extra = {
        'density_scale': '-2',
        #'linux': True,
        #'windows': True,
        'pyside6': True,
        # 'font_family': 'Roboto',
        'QLineEdit': {
            'color': '#ffffff',
        },
    }
    apply_stylesheet(app, theme='dark_teal.xml', invert_secondary=False, extra=extra)

    available_geometry = window.screen().availableGeometry()
    center = QScreen.availableGeometry(QApplication.primaryScreen()).center() / 2
    topLeftPoint = QScreen.availableGeometry(QApplication.primaryScreen()).topLeft()
    window.resize(available_geometry.width(), available_geometry.height())
    window.showMaximized()
    window.move(topLeftPoint)

    try:
        sys.exit(app.exec())
    except SystemExit:
        print("Closing...")
