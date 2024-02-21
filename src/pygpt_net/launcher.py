#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.21 18:00:00                  #
# ================================================== #

import sys
import argparse
from logging import ERROR, WARNING, INFO, DEBUG

from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QApplication

from pygpt_net.core.debug import Debug
from pygpt_net.core.platforms import Platforms
from pygpt_net.ui.main import MainWindow
from pygpt_net.plugin.base import BasePlugin
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.provider.loaders.base import BaseLoader
from pygpt_net.provider.vector_stores.base import BaseStore


class Launcher:
    def __init__(self):
        """Launcher"""
        self.app = None
        self.window = None
        self.debug = False

    def setup(self) -> dict:
        """
        Setup launcher

        :return: dict with launcher arguments
        """
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-d",
            "--debug",
            required=False,
            help="debug mode (0=disabled, 1=info, 2=debug)",
        )
        args = vars(parser.parse_args())

        # set log level [ERROR|WARNING|INFO|DEBUG]
        if "debug" in args and args["debug"] == "1":
            print("** Debug mode enabled (1=INFO)")
            Debug.init(INFO)
            self.debug = True
        elif "debug" in args and args["debug"] == "2":
            print("** Debug mode enabled (2=DEBUG)")
            Debug.init(DEBUG)
            self.debug = True
        else:
            Debug.init(ERROR)  # default log level

        return args

    def init(self):
        """Initialize app"""
        args = self.setup()
        Platforms.prepare()  # setup platform specific options
        self.app = QApplication(sys.argv)
        self.window = MainWindow(self.app, args=args)

    def add_plugin(self, plugin: BasePlugin):
        """
        Register plugin

        :param plugin: plugin instance
        """
        if not isinstance(plugin, BasePlugin):
            raise TypeError(
                "Plugin must be instance of: "
                "pygpt_net.plugin.base.BasePlugin"
            )
        self.window.add_plugin(plugin)
        if self.debug:
            print("Loaded plugin: {} ({})".format(plugin.id, plugin.__class__.__name__))

    def add_llm(self, llm: BaseLLM):
        """
        Register LLM provider

        :param llm: LLM provider instance
        """
        if not isinstance(llm, BaseLLM):
            raise TypeError(
                "LLM provider must be instance of: "
                "pygpt_net.provider.llms.base.BaseLLM"
            )
        self.window.add_llm(llm)
        if self.debug:
            print("Loaded LLM: {} ({})".format(llm.id, llm.__class__.__name__))

    def add_vector_store(self, store: BaseStore):
        """
        Register vector store provider

        :param store: Vector store provider instance
        """
        if not isinstance(store, BaseStore):
            raise TypeError(
                "Vector store provider must be instance of: "
                "pygpt_net.provider.vector_stores.base.BaseStore"
            )
        self.window.add_vector_store(store)
        if self.debug:
            print("Loaded vector store: {} ({})".format(store.id, store.__class__.__name__))

    def add_loader(self, loader: BaseLoader):
        """
        Register data loader

        :param loader: Data loader instance
        """
        if not isinstance(loader, BaseLoader):
            raise TypeError(
                "Data loader must be instance of: "
                "pygpt_net.provider.loaders.base.BaseLoader"
            )
        self.window.add_loader(loader)
        if self.debug:
            print("Loaded data loader: {} ({})".format(loader.id, loader.__class__.__name__))

    def run(self):
        """Run app"""
        self.window.setup()
        geometry = self.window.screen().availableGeometry()
        pos = QScreen.availableGeometry(QApplication.primaryScreen()).topLeft()
        margin = 100
        self.window.resize(geometry.width() - margin, geometry.height() - margin)
        self.window.show()
        self.window.move(pos)
        self.window.post_setup()
        self.app.setWindowIcon(self.window.ui.get_app_icon())
        self.window.ui.tray.setup(self.app)
        self.window.controller.after_setup()
        sys.exit(self.app.exec())
