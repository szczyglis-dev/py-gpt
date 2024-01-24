#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.24 18:00:00                  #
# ================================================== #

import sys

from PySide6.QtCore import QTimer, Signal, Slot, QThreadPool
from PySide6.QtGui import QScreen
from PySide6.QtWidgets import QApplication, QMainWindow
from qt_material import QtStyleTools
from logging import ERROR, WARNING, INFO, DEBUG

from pygpt_net.container import Container
from pygpt_net.controller import Controller
from pygpt_net.core.debug import Debug
from pygpt_net.core.platforms import Platforms
from pygpt_net.ui import UI
from pygpt_net.utils import get_app_meta

# plugins
from pygpt_net.plugin.audio_azure import Plugin as AudioAzurePlugin
from pygpt_net.plugin.audio_openai_tts import Plugin as AudioOpenAITTSPlugin
from pygpt_net.plugin.audio_openai_whisper import Plugin as AudioOpenAIWhisperPlugin
from pygpt_net.plugin.cmd_code_interpreter import Plugin as CmdCodeInterpreterPlugin
from pygpt_net.plugin.cmd_custom import Plugin as CmdCustomCommandPlugin
from pygpt_net.plugin.cmd_files import Plugin as CmdFilesPlugin
from pygpt_net.plugin.cmd_web_google import Plugin as CmdWebGooglePlugin
from pygpt_net.plugin.openai_dalle import Plugin as OpenAIDallePlugin
from pygpt_net.plugin.openai_vision import Plugin as OpenAIVisionPlugin
from pygpt_net.plugin.real_time import Plugin as RealTimePlugin
from pygpt_net.plugin.self_loop import Plugin as SelfLoopPlugin
from pygpt_net.plugin.idx_llama_index import Plugin as IdxLlamaIndexPlugin
from pygpt_net.plugin.crontab import Plugin as CrontabPlugin
from pygpt_net.plugin.cmd_serial import Plugin as CmdSerialPlugin

# LLMs
from pygpt_net.provider.llm.anthropic import AnthropicLLM
from pygpt_net.provider.llm.azure_openai import AzureOpenAILLM
from pygpt_net.provider.llm.hugging_face import HuggingFaceLLM
from pygpt_net.provider.llm.llama import Llama2LLM
from pygpt_net.provider.llm.ollama import OllamaLLM
from pygpt_net.provider.llm.openai import OpenAILLM

# vector stores
from pygpt_net.provider.vector_stores.chroma import ChromaProvider
from pygpt_net.provider.vector_stores.elasticsearch import ElasticsearchProvider
from pygpt_net.provider.vector_stores.pinecode import PinecodeProvider
from pygpt_net.provider.vector_stores.redis import RedisProvider
from pygpt_net.provider.vector_stores.simple import SimpleProvider

Debug.init(ERROR)  # <-- set logging level [ERROR|WARNING|INFO|DEBUG]


class MainWindow(QMainWindow, QtStyleTools):
    statusChanged = Signal(str)

    def __init__(self, app: QApplication):
        """Main window"""
        super().__init__()
        self.app = app
        self.timer = None
        self.post_timer = None
        self.threadpool = None
        self.is_closing = False
        self.timer_interval = 30
        self.post_timer_interval = 1000

        # load version info
        self.meta = get_app_meta()

        # setup service container
        self.core = Container(self)
        self.core.init()
        self.core.patch()  # patch version if needed

        # setup thread pool
        self.threadpool = QThreadPool()

        # setup controllers
        self.controller = Controller(self)

        # init, load settings options, etc.
        self.controller.init()

        # setup UI
        self.ui = UI(self)
        self.ui.init()

        # setup global signals
        self.statusChanged.connect(self.update_status)

    def add_plugin(self, plugin):
        """
        Add plugin to app

        :param plugin: plugin instance
        """
        self.core.plugins.register(plugin)

    def add_llm(self, llm):
        """
        Add Langchain LLM wrapper to app

        :param llm: LLM wrapper instance
        """
        self.core.llm.register(llm.id, llm)

    def add_vector_store(self, store):
        """
        Add vector store provider to app

        :param store: Vector store provider instance
        """
        self.core.idx.storage.register(store.id, store)

    def setup(self):
        """Setup app"""
        self.controller.setup()
        self.controller.plugins.setup()
        self.controller.post_setup()

    def post_setup(self):
        """Called after setup"""
        self.controller.layout.post_setup()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self.timer_interval)
        self.post_timer = QTimer()
        self.post_timer.timeout.connect(self.post_update)
        self.post_timer.start(self.post_timer_interval)
        self.ui.post_setup()

    def update(self):
        """Called on every update"""
        self.controller.on_update()
        self.controller.plugins.on_update()

    def post_update(self):
        """Called on post-update (slow)"""
        self.controller.debug.on_update()
        self.controller.plugins.on_post_update()

    @Slot(str)
    def update_status(self, text: str):
        """
        Update status text

        :param text: status text
        """
        self.ui.status(text)

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
        print("Saving calendar...")
        self.controller.calendar.save_all()
        print("Saving drawing...")
        self.controller.painter.save_all()
        print("Saving layout state...")
        self.controller.layout.save()
        print("Stopping timers...")
        self.timer.stop()
        self.post_timer.stop()
        print("Saving config...")
        self.core.config.save()
        print("Saving presets...")
        self.core.presets.save_all()
        print("Exiting...")
        event.accept()


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
        available_geometry = self.window.screen().availableGeometry()
        pos = QScreen.availableGeometry(QApplication.primaryScreen()).topLeft()
        self.window.resize(available_geometry.width() - margin, available_geometry.height() - margin)
        self.window.show()
        self.window.move(pos)
        self.window.post_setup()
        sys.exit(self.app.exec())


def run(
        plugins: list = None,
        llms: list = None,
        vector_stores: list = None
):
    """
    PyGPT launcher.

    :param plugins: List containing custom plugin instances.
    :param llms: List containing custom LLMs wrapper instances.
    :param vector_stores: List containing custom vector index store provider instances.

    Extending PyGPT with custom plugins and LLMs wrappers:

    - You can pass custom plugin instances and LLMs wrappers to the launcher.
    - This is useful if you want to extend PyGPT with your own plugins and LLMs.

    To register custom plugins:

    - Pass a list with the plugin instances as the first argument.

    To register custom LLMs wrappers:

    - Pass a list with the LLMs wrappers instances as the second argument.

    To register custom vector store providers:

    - Pass a list with the vector store provider instances as the third argument.

    Example:
    --------
    ::

        from pygpt_net.app import run
        from my_plugins import MyCustomPlugin, MyOtherCustomPlugin
        from my_llms import MyCustomLLM
        from my_vector_stores import MyCustomVectorStore

        plugins = [
            MyCustomPlugin(),
            MyOtherCustomPlugin(),
        ]
        llms = [
            MyCustomLLM(),
        ]
        vector_stores = [
            MyCustomVectorStore(),
        ]

        run(
            plugins=plugins,
            llms=llms,
            vector_stores=vector_stores
        )

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
    launcher.add_plugin(CmdSerialPlugin())
    launcher.add_plugin(OpenAIDallePlugin())
    launcher.add_plugin(OpenAIVisionPlugin())
    launcher.add_plugin(IdxLlamaIndexPlugin())
    launcher.add_plugin(CrontabPlugin())

    # register custom plugins
    if plugins is not None:
        for plugin in plugins:
            launcher.add_plugin(plugin)

    # register base langchain and llama-index LLMs
    launcher.add_llm(OpenAILLM())
    launcher.add_llm(AzureOpenAILLM())
    launcher.add_llm(AnthropicLLM())
    launcher.add_llm(HuggingFaceLLM())
    launcher.add_llm(Llama2LLM())
    launcher.add_llm(OllamaLLM())

    # register custom langchain and llama-index LLMs
    if llms is not None:
        for llm in llms:
            launcher.add_llm(llm)

    # register base vector store providers (llama-index)
    launcher.add_vector_store(ChromaProvider())
    launcher.add_vector_store(ElasticsearchProvider())
    launcher.add_vector_store(PinecodeProvider())
    launcher.add_vector_store(RedisProvider())
    launcher.add_vector_store(SimpleProvider())

    # register custom vector store providers (llama-index)
    if vector_stores is not None:
        for store in vector_stores:
            launcher.add_vector_store(store)

    # run app
    launcher.run()
    

if __name__ == '__main__':
    run()
