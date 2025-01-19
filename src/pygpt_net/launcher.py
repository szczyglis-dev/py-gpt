#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.01.19 02:00:00                  #
# ================================================== #

import os
import sys
import argparse
from logging import ERROR, WARNING, INFO, DEBUG

from PySide6 import QtCore
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QApplication

from pygpt_net.core.events import AppEvent
from pygpt_net.core.access.shortcuts import GlobalShortcutFilter
from pygpt_net.core.debug import Debug
from pygpt_net.core.platforms import Platforms
from pygpt_net.provider.agents.base import BaseAgent
from pygpt_net.tools import BaseTool
from pygpt_net.ui.main import MainWindow
from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.provider.llms.base import BaseLLM
from pygpt_net.provider.loaders.base import BaseLoader
from pygpt_net.provider.vector_stores.base import BaseStore
from pygpt_net.provider.audio_input.base import BaseProvider as BaseAudioInput
from pygpt_net.provider.audio_output.base import BaseProvider as BaseAudioOutput
from pygpt_net.provider.web.base import BaseProvider as BaseWeb


class Launcher:
    def __init__(self):
        """Launcher"""
        self.app = None
        self.window = None
        self.debug = False
        self.force_legacy = False
        self.force_disable_gpu = False
        self.shortcut_filter = None
        self.workdir = None

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
        parser.add_argument(
            "-l",
            "--legacy",
            required=False,
            help="force enable legacy mode (0=disabled, 1=enable)",
        )
        parser.add_argument(
            "-n",
            "--disable-gpu",
            required=False,
            help="force disable OpenGL (1=disabled, 0=enabled)",
        )
        parser.add_argument(
            "-w",
            "--workdir",
            required=False,
            help="force set workdir",
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

        # force legacy mode
        if "legacy" in args and args["legacy"] == "1":
            print("** Force legacy mode enabled")
            self.force_legacy = True

        # force disable GPU
        if "disable-gpu" in args and args["disable-gpu"] == "1":
            print("** Force disable GPU enabled")
            self.force_disable_gpu = True

        # force set workdir
        if "workdir" in args and args["workdir"] is not None:
            # set as environment variable
            os.environ["PYGPT_WORKDIR"] = args["workdir"]

        return args

    def init(self):
        """Initialize app"""
        args = self.setup()
        Platforms.prepare()  # setup platform specific options
        QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        self.app = QApplication(sys.argv)
        self.app.setAttribute(QtCore.Qt.AA_DontUseNativeMenuBar)
        self.window = MainWindow(self.app, args=args)
        self.shortcut_filter = GlobalShortcutFilter(self.window)

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

    def add_audio_input(self, audio: BaseAudioInput):
        """
        Register audio input provider

        :param audio: Audio input provider instance
        """
        if not isinstance(audio, BaseAudioInput):
            raise TypeError(
                "Audio input provider must be instance of: "
                "pygpt_net.provider.audio_input.base.BaseProvider"
            )
        self.window.add_audio_input(audio)
        if self.debug:
            print("Loaded audio input: {} ({})".format(audio.id, audio.__class__.__name__))

    def add_audio_output(self, audio: BaseAudioOutput):
        """
        Register audio output provider

        :param audio: Audio output provider instance
        """
        if not isinstance(audio, BaseAudioOutput):
            raise TypeError(
                "Audio output provider must be instance of: "
                "pygpt_net.provider.audio_output.base.BaseProvider"
            )
        self.window.add_audio_output(audio)
        if self.debug:
            print("Loaded audio output: {} ({})".format(audio.id, audio.__class__.__name__))

    def add_web(self, provider: BaseWeb):
        """
        Register web provider

        :param provider: Web provider instance
        """
        if not isinstance(provider, BaseWeb):
            raise TypeError(
                "Web provider must be instance of: "
                "pygpt_net.provider.web.base.BaseProvider"
            )
        self.window.add_web(provider)
        if self.debug:
            print("Loaded web provider: {} ({})".format(provider.id, provider.__class__.__name__))

    def add_tool(self, tool: BaseTool):
        """
        Register tool

        :param tool: tool instance
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(
                "Tool must be instance of: "
                "pygpt_net.tools.base.BaseTool"
            )
        self.window.add_tool(tool)
        if self.debug:
            print("Loaded tool: {} ({})".format(tool.id, tool.__class__.__name__))

    def add_agent(self, agent: BaseAgent):
        """
        Register agent (LlamaIndex agent)

        :param agent: Agent instance
        """
        if not isinstance(agent, BaseAgent):
            raise TypeError(
                "Agent must be instance of: "
                "pygpt_net.provider.agents.base.BaseAgent"
            )
        self.window.add_agent(agent)
        if self.debug:
            print("Loaded agent: {} ({})".format(agent.id, agent.__class__.__name__))

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
        self.window.dispatch(AppEvent(AppEvent.APP_STARTED))  # app event
        self.window.setup_global_shortcuts()
        sys.exit(self.app.exec())
