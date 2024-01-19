#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.19 18:00:00                  #
# ================================================== #

import platform
import os

from PySide6 import QtCore, QtWidgets

from pygpt_net.config import Config


class Platforms:

    def __init__(self, window=None):
        """
        Platform core

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

    def get_os(self) -> str:
        """
        Return OS name

        :return: OS name
        """
        return platform.system()

    def get_architecture(self) -> str:
        """
        Return platform architecture

        :return: platform architecture
        """
        return platform.machine()

    def is_linux(self) -> bool:
        """
        Return True if OS is Linux

        :return: True if OS is Linux
        """
        return self.get_os() == 'Linux'

    def is_mac(self) -> bool:
        """
        Return True if OS is MacOS

        :return: True if OS is MacOS
        """
        return self.get_os() == 'Darwin'

    def is_windows(self) -> bool:
        """
        Return True if OS is Windows

        :return: True if OS is Windows
        """
        return self.get_os() == 'Windows'

    def is_snap(self) -> bool:
        """
        Return True if app is running as snap

        :return: True if app is running as snap
        """
        return "SNAP" in os.environ \
               and "SNAP_NAME" in os.environ \
               and os.environ["SNAP_NAME"] == self.snap_name

    def get_as_string(self) -> str:
        """
        Return platform as string

        :return: platform as string
        """
        extra = ''
        if self.is_snap():
            extra = ' (snap)'
        elif self.window.core.config.is_compiled():
            extra = ' (compiled)'
        return self.get_os() + ', ' + self.get_architecture() + '  ' + extra
