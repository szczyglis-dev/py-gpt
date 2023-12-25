#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

import os
import sys
import time

from PySide6.QtCore import QTimer, Signal, Slot
from PySide6.QtGui import QScreen, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow)
from qt_material import QtStyleTools
from logging import ERROR, WARNING, INFO, DEBUG

from pygpt_net.container import Container
from pygpt_net.controller.main import Controller
from pygpt_net.core.debugger import Debug
from pygpt_net.core.platforms import Platforms
from pygpt_net.ui.main import UI
from pygpt_net.utils import get_app_meta

from pygpt_net.plugin.audio_azure.plugin import Plugin as AudioAzurePlugin
from pygpt_net.plugin.audio_openai_tts.plugin import Plugin as AudioOpenAITTSPlugin
from pygpt_net.plugin.audio_openai_whisper.plugin import Plugin as AudioOpenAIWhisperPlugin
from pygpt_net.plugin.cmd_code_interpreter.plugin import Plugin as CmdCodeInterpreterPlugin
from pygpt_net.plugin.cmd_custom.plugin import Plugin as CmdCustomCommandPlugin
from pygpt_net.plugin.cmd_files.plugin import Plugin as CmdFilesPlugin
from pygpt_net.plugin.cmd_web_google.plugin import Plugin as CmdWebGooglePlugin
from pygpt_net.plugin.real_time.plugin import Plugin as RealTimePlugin
from pygpt_net.plugin.self_loop.plugin import Plugin as SelfLoopPlugin

from pygpt_net.llm.Anthropic import AnthropicLLM
from pygpt_net.llm.AzureOpenAI import AzureOpenAILLM
from pygpt_net.llm.HuggingFace import HuggingFaceLLM
from pygpt_net.llm.Llama2 import Llama2LLM
from pygpt_net.llm.Ollama import OllamaLLM
from pygpt_net.llm.OpenAI import OpenAILLM


Debug.init(ERROR)  # <-- set logging level [ERROR|WARNING|INFO|DEBUG]


class MainWindow(QMainWindow, QtStyleTools):
    statusChanged = Signal(str)

    def __init__(self):
        """Main window"""
        super().__init__()
        self.timer = None
        self.timer_interval = 30
        self.is_closing = False

        # load version info
        self.meta = get_app_meta()

        # setup service container
        self.app = Container(self)
        self.app.init()
        self.app.patch()  # patch version if needed

        # setup controllers
        self.controller = Controller(self)

        # init, load settings options, etc.
        self.controller.init()

        # setup UI
        self.ui = UI(self)
        self.ui.init()

        # set window title
        self.setWindowTitle('PyGPT - Desktop AI Assistant v{} | build {}'.
                            format(self.meta['version'], self.meta['build']))

        # setup global signals
        self.statusChanged.connect(self.update_status)

    def log(self, data, window=True):
        """
        Log data to logger and console

        :param data: content to log
        :param window: log to window
        """
        self.controller.debug.log(data, window)

    def dispatch(self, event, all=False):
        """
        Dispatch event to plugins and other listeners

        :param event: event object
        :param all: dispatch to all listeners (plugins, etc.)
        """
        self.app.dispatcher.dispatch(event, all)

    def add_plugin(self, plugin):
        """
        Add plugin to app

        :param plugin: plugin instance
        """
        self.app.plugins.register(plugin)

    def add_llm(self, llm):
        """
        Add Langchain LLM wrapper to app

        :param llm: LLM wrapper instance
        """
        self.app.chain.register(llm.id, llm)

    def setup(self):
        """Setup app"""
        self.controller.setup()
        self.controller.plugins.setup()
        self.controller.post_setup()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self.timer_interval)
        self.post_timer = QTimer()
        self.post_timer.timeout.connect(self.post_update)
        self.post_timer.start(1000)

    def post_setup(self):
        """Called after setup"""
        self.controller.layout.post_setup()

    def post_update(self):
        """Called on post-update (slow)"""
        self.app.debug.update()

    def update(self):
        """Called on every update"""
        self.controller.update()

    def set_status(self, text):
        """
        Update status text

        :param text: status text
        """
        self.ui.nodes['status'].setText(str(text))

    @Slot(str)
    def update_status(self, text):
        """
        Update status text

        :param text: status text
        """
        self.set_status(text)

    def closeEvent(self, event):
        """
        Handle close event

        :param event: close event
        """
        self.is_closing = True
        print("Closing...")
        print("Sending terminate signal to plugins...")
        self.controller.plugins.destroy()
        print("Saving notepad...")
        self.controller.notepad.save_all()
        print("Saving layout state...")
        self.controller.layout.save()
        print("Stopping timers...")
        self.timer.stop()
        self.post_timer.stop()
        print("Saving config...")
        self.app.config.save()
        print("Saving presets...")
        self.app.presets.save_all()
        print("Exiting...")


class Launcher:
    def __init__(self):
        """Launcher"""
        self.app = None
        self.window = None

    def init(self):
        """Initialize app"""
        Platforms.prepare()  # setup platform specific options

        self.app = QApplication(sys.argv)
        self.window = MainWindow()
        self.app.setWindowIcon(QIcon(os.path.join(self.window.app.config.get_root_path(), 'data', 'icon.ico')))
        self.app.aboutToQuit.connect(self.app.quit)

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

    def run(self):
        """Run app"""
        margin = 50
        try:
            self.window.setup()
            available_geometry = self.window.screen().availableGeometry()
            pos = QScreen.availableGeometry(QApplication.primaryScreen()).topLeft()
            self.window.resize(available_geometry.width() - margin, available_geometry.height() - margin)
            self.window.show()
            self.window.move(pos)
            self.window.post_setup()
            sys.exit(self.app.exec())
        except SystemExit:
            print("Closing...")


def run(plugins=None, llms=None):
    """
    PyGPT launcher.

    :param plugins: List containing custom plugin instances.
    :param llms: List containing custom LLMs (Large Language Models) wrapper instances.

    Extending PyGPT with custom plugins and LLMs wrappers:

    - You can pass custom plugin instances and LLMs wrappers to the launcher.
    - This is useful if you want to extend PyGPT with your own plugins and LLMs.

    To register custom plugins:

    - Pass a list with the plugin instances as the first argument.

    To register custom LLMs wrappers:

    - Pass a list with the LLMs wrappers instances as the second argument.

    Example:
    --------
    ::

        from pygpt_net.app import run
        from my_plugins import MyCustomPlugin, MyOtherCustomPlugin
        from my_llms import MyCustomLLM

        plugins = [
            MyCustomPlugin(),
            MyOtherCustomPlugin(),
        ]
        llms = [
            MyCustomLLM(),
        ]

        run(plugins=plugins, llms=llms)

    """

    # initialize app launcher
    launcher = Launcher()
    launcher.init()

    # register base plugins
    launcher.add_plugin(SelfLoopPlugin())
    launcher.add_plugin(RealTimePlugin())
    launcher.add_plugin(AudioAzurePlugin())
    launcher.add_plugin(AudioOpenAITTSPlugin())
    launcher.add_plugin(AudioOpenAIWhisperPlugin())
    launcher.add_plugin(CmdWebGooglePlugin())
    launcher.add_plugin(CmdFilesPlugin())
    launcher.add_plugin(CmdCodeInterpreterPlugin())
    launcher.add_plugin(CmdCustomCommandPlugin())

    # register custom plugins
    if plugins is not None:
        for plugin in plugins:
            launcher.add_plugin(plugin)

    # register base langchain LLMs
    launcher.add_llm(OpenAILLM())
    launcher.add_llm(AzureOpenAILLM())
    launcher.add_llm(AnthropicLLM())
    launcher.add_llm(HuggingFaceLLM())
    launcher.add_llm(Llama2LLM())
    launcher.add_llm(OllamaLLM())

    # register custom langchain LLMs
    if llms is not None:
        for llm in llms:
            launcher.add_llm(llm)

    # run app
    launcher.run()
    

if __name__ == '__main__':
    run()
