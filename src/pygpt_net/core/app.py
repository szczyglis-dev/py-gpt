#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.18 14:00:00                  #
# ================================================== #
import os
import sys

from PySide6.QtGui import QScreen
from PySide6.QtCore import QTimer, Signal, Slot
from PySide6.QtWidgets import (QApplication, QMainWindow)
from qt_material import QtStyleTools

from .config import Config
from .ui.main import UI
from .container import Container
from .controller.main import Controller
from .utils import get_app_meta

from .plugin.self_loop.plugin import Plugin as SelfLoopPlugin
from .plugin.real_time.plugin import Plugin as RealTimePlugin
from .plugin.audio_azure.plugin import Plugin as AudioAzurePlugin
from .plugin.audio_openai_tts.plugin import Plugin as AudioOpenAITTSPlugin
from .plugin.audio_openai_whisper.plugin import Plugin as AudioOpenAIWhisperPlugin
from .plugin.cmd_web_google.plugin import Plugin as CmdWebGooglePlugin
from .plugin.cmd_files.plugin import Plugin as CmdFilesPlugin
from .plugin.cmd_code_interpreter.plugin import Plugin as CmdCodeInterpreterPlugin
from .plugin.cmd_custom.plugin import Plugin as CmdCustomCommandPlugin

from .llm.OpenAI import OpenAILLM
from .llm.AzureOpenAI import AzureOpenAILLM
from .llm.Anthropic import AnthropicLLM
from .llm.HuggingFace import HuggingFaceLLM
from .llm.Llama2 import Llama2LLM
from .llm.Ollama import OllamaLLM


class MainWindow(QMainWindow, QtStyleTools):
    statusChanged = Signal(str)

    def __init__(self):
        """Application main window"""
        super().__init__()
        self.timer = None
        self.is_closing = False

        # load version info
        self.meta = get_app_meta()
        self.data = {}

        # setup config
        self.config = Config()
        self.config.init(True, True)

        # setup service container
        self.app = Container(self)

        # setup main controller
        self.controller = Controller(self)

        # handle version migration
        self.controller.migrate()

        # init, load settings options, etc.
        self.controller.init()

        # setup UI
        self.ui = UI(self)
        self.ui.setup()

        # set window title
        self.setWindowTitle('PyGPT - Desktop AI Assistant v{} | build {}'.format(self.meta['version'], self.meta['build']))

        # setup signals
        self.statusChanged.connect(self.update_status)

    def log(self, data):
        """
        Log data to logger and console

        :param data: content to log
        """
        self.controller.debug.log(data)

    def dispatch(self, event):
        """
        Dispatch event to plugins and other listeners

        :param event: event object
        """
        self.controller.plugins.dispatch(event)

    def set_theme(self, theme='dark_teal.xml', custom_css=None):
        """
        Update material theme and apply custom CSS

        :param theme: material theme name
        :param custom_css: custom CSS file
        """
        inverse = False
        extra = {
            'density_scale': self.config.get('layout.density'),
            'pyside6': True,
        }
        self.apply_stylesheet(self, theme, invert_secondary=inverse, extra=extra)

        # append custom CSS
        if custom_css is not None:
            path = os.path.join(self.config.get_root_path(), 'data', 'css', custom_css)
            stylesheet = self.styleSheet()
            if os.path.exists(path):
                with open(path) as file:
                    self.setStyleSheet(stylesheet + file.read().format(**os.environ))

    def add_plugin(self, plugin):
        """
        Add plugin to app

        :param plugin: plugin instance
        """
        plugin.attach(self)
        self.controller.plugins.register(plugin)

    def add_llm(self, llm):
        """
        Add Langchain LLM wrapper to app

        :param llm: LLM wrapper instance
        """
        id = llm.id
        self.app.chain.register(id, llm)

    def setup(self):
        """Setup app"""
        self.controller.setup()
        self.controller.plugins.setup()
        self.controller.post_setup()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(30)

    def post_setup(self):
        """Called after setup"""
        self.controller.layout.post_setup()

    def update(self):
        """Called on every update"""
        self.app.debug.update()
        self.controller.update()

    def set_status(self, text):
        """
        Update status text

        :param text: status text
        """
        self.data['status'].setText(str(text))

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
        self.controller.notepad.save()
        print("Saving layout state...")
        self.controller.layout.save()
        print("Stopping event loop...")
        self.timer.stop()
        print("Saving config...")
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
        """Initialize app"""
        self.app = QApplication(sys.argv)
        self.window = MainWindow()
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
        self.window.setup()
        available_geometry = self.window.screen().availableGeometry()
        pos = QScreen.availableGeometry(QApplication.primaryScreen()).topLeft()
        self.window.resize(available_geometry.width() - margin, available_geometry.height() - margin)
        self.window.show()
        self.window.move(pos)
        self.window.post_setup()
        try:
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

        from pygpt_net.core.app import run
        from my_plugins import MyCustomPlugin, MyOtherCustomPlugin
        from my_llms import MyCustomLLM

        plugins = [
            MyCustomPlugin(),
            MyOtherCustomPlugin(),
        ]
        llms = [
            MyCustomLLM(),
        ]

        run(plugins, llms)

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
