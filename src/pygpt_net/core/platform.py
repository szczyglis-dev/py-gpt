#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.20 21:00:00                  #
# ================================================== #

import platform
import os

from PySide6 import QtCore, QtWidgets

from pygpt_net.core.config import Config


class Platform:

    def __init__(self, window=None):
        """
        Platform handler

        :param window: Window instance
        """
        self.window = window
        self.snap_name = 'pygpt'

    @staticmethod
    def prepare():
        """Pre-initialize application"""
        dpi_scaling = True
        dpi_factor = '1'

        try:
            config = Config()
            config.load_config(False)
            if config.has('layout.dpi.scaling'):
                dpi_scaling = config.get('layout.dpi.scaling')
            if config.has('layout.dpi.factor'):
                dpi_factor = str(config.get('layout.dpi.factor'))
        except Exception as e:
            pass

        os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = dpi_factor
        os.environ['QT_SCALE_FACTOR'] = dpi_factor

        if not dpi_scaling:
            if hasattr(QtCore.Qt, 'AA_DisableHighDpiScaling'):
                QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_DisableHighDpiScaling, True)
            if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
                QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, False)
        else:
            if hasattr(QtCore.Qt, 'AA_DisableHighDpiScaling'):
                QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_DisableHighDpiScaling, False)
            if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
                QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

        if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    def init(self):
        """Initialize platform"""
        pass

    def get_os(self):
        """
        Return OS name

        :return: OS name
        :rtype: str
        """
        return platform.system()

    def get_architecture(self):
        """
        Return platform architecture

        :return: platform architecture
        :rtype: str
        """
        return platform.machine()

    def is_linux(self):
        """
        Return True if OS is Linux

        :return: true if OS is Linux
        :rtype: bool
        """
        return self.get_os() == 'Linux'

    def is_mac(self):
        """
        Return True if OS is MacOS

        :return: True if OS is MacOS
        :rtype: bool
        """
        return self.get_os() == 'Darwin'

    def is_windows(self):
        """
        Return True if OS is Windows

        :return: true if OS is Windows
        :rtype: bool
        """
        return self.get_os() == 'Windows'

    def is_snap(self):
        """
        Return True if app is running as snap

        :return: true if app is running as snap
        :rtype: bool
        """
        return "SNAP" in os.environ \
               and "SNAP_NAME" in os.environ \
               and os.environ["SNAP_NAME"] == self.snap_name
