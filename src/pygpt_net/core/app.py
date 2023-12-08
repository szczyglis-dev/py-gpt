#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.08 14:00:00                  #
# ================================================== #
import os
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
from .chain import Chain
from .context import Context
from .command import Command
from .image import Image
from .utils import get_init_value

from .plugin.self_loop.plugin import Plugin as SelfLoopPlugin
from .plugin.real_time.plugin import Plugin as RealTimePlugin
from .plugin.audio_azure.plugin import Plugin as AudioAzurePlugin
from .plugin.audio_openai_tts.plugin import Plugin as AudioOpenAITTSPlugin
from .plugin.audio_openai_whisper.plugin import Plugin as AudioOpenAIWhisperPlugin
from .plugin.cmd_web_google.plugin import Plugin as CmdWebGooglePlugin
from .plugin.cmd_files.plugin import Plugin as CmdFilesPlugin
from .plugin.cmd_code_interpreter.plugin import Plugin as CmdCodeInterpreterPlugin

from .llm.OpenAI import OpenAILLM
from .llm.AzureOpenAI import AzureOpenAILLM
from .llm.Anthropic import AnthropicLLM
from .llm.HuggingFace import HuggingFaceLLM
from .llm.Llama2 import Llama2LLM
from .llm.Ollama import OllamaLLM


class MainWindow(QMainWindow, QtStyleTools):
    statusChanged = Signal(str)

    def __init__(self):
        """App main window"""
        super().__init__()
        self.timer = None
        self.is_closing = False
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
        self.context = Context(self.config)

        # app controller
        self.controller = Controller(self)
        self.debugger = Debug(self)
        self.info = Info(self)
        self.settings = Settings(self)
        self.command = Command(self)

        # handle config migration if needed
        self.controller.launcher.migrate_version()

        # load settings options from json
        self.controller.settings.load()

        # setup GPT, Langchain and DALL-E
        self.gpt = Gpt(self.config, self.context)
        self.chain = Chain(self.config, self.context)
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

    def set_theme(self, theme='dark_teal.xml', custom_css=None):
        """
        Updates material theme and applies custom CSS

        :param theme: Material theme name
        :param custom_css: custom CSS file
        """
        inverse = False
        extra = {
            'density_scale': '-2',
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
        Adds plugin

        :param plugin: plugin instance
        """
        plugin.attach(self)
        self.controller.plugins.register(plugin)

    def add_llm(self, llm):
        """
        Adds Langchain LLM wrapper

        :param llm: llm instance
        """
        id = llm.id
        self.chain.register(id, llm)

    def setup(self):
        """Setups app"""
        self.controller.setup()
        self.controller.plugins.setup()
        self.controller.setup_plugins()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(30)

    def post_setup(self):
        """Called after setup"""
        self.controller.layout.post_setup()

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

    def add_llm(self, llm=None):
        """
        Registers LLMs

        :param llm: llm instance
        """
        self.window.add_llm(llm)

    def run(self):
        """Runs app"""
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


def run():
    """Runs app"""
    # initialize app
    launcher = Launcher()
    launcher.init()

    # register plugins
    launcher.add_plugin(SelfLoopPlugin())
    launcher.add_plugin(RealTimePlugin())
    launcher.add_plugin(AudioAzurePlugin())
    launcher.add_plugin(AudioOpenAITTSPlugin())
    launcher.add_plugin(AudioOpenAIWhisperPlugin())
    launcher.add_plugin(CmdWebGooglePlugin())
    launcher.add_plugin(CmdFilesPlugin())
    launcher.add_plugin(CmdCodeInterpreterPlugin())

    # register langchain LLMs
    launcher.add_llm(OpenAILLM())
    launcher.add_llm(AzureOpenAILLM())
    launcher.add_llm(AnthropicLLM())
    launcher.add_llm(HuggingFaceLLM())
    launcher.add_llm(Llama2LLM())
    launcher.add_llm(OllamaLLM())

    # run app
    launcher.run()
