#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.21 16:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QTimer, Signal, Slot, QThreadPool, QEvent, Qt, QLoggingCategory
from PySide6.QtWidgets import QApplication, QMainWindow
from qt_material import QtStyleTools

from pygpt_net.container import Container
from pygpt_net.controller import Controller
from pygpt_net.tools import Tools
from pygpt_net.ui import UI
from pygpt_net.utils import get_app_meta


class MainWindow(QMainWindow, QtStyleTools):

    # states
    STATE_IDLE = 'idle'
    STATE_BUSY = 'busy'
    STATE_ERROR = 'error'

    # signals
    statusChanged = Signal(str)
    stateChanged = Signal(str)
    logger_message = Signal(object)
    idx_logger_message = Signal(object)

    def __init__(self, app: QApplication, args: dict = None):
        """
        Main window

        :param app: QApplication instance
        :param args: launcher arguments
        """
        super().__init__()
        self.app = app
        self.args = args
        self.timer = None
        self.post_timer = None
        self.update_timer = None
        self.threadpool = None
        self.is_closing = False
        self.timer_interval = 30
        self.post_timer_interval = 1000
        self.update_timer_interval = 300000  # check every 5 minutes
        self.state = self.STATE_IDLE
        self.prevState = None

        # load version info
        self.meta = get_app_meta()

        # setup service container
        self.core = Container(self)
        self.core.init()
        self.core.patch()  # patch version if needed
        self.core.post_setup()

        # before render, handle engine args
        self.handle_engine_args()

        # setup thread pool
        self.threadpool = QThreadPool()

        # setup controller
        self.controller = Controller(self)

        # setup tools
        self.tools = Tools(self)

        # init, load settings options, etc.
        self.controller.init()

        # setup UI
        self.ui = UI(self)
        self.ui.init()

        # setup signals
        self.statusChanged.connect(self.update_status)
        self.stateChanged.connect(self.update_state)

    def handle_engine_args(self):
        """Handle launcher arguments"""
        render_debug = False
        if self.args is not None:
            if "debug" in self.args and (self.args["debug"] == "1" or self.args["debug"] == "2"):
                render_debug = True
            if "legacy" in self.args and self.args["legacy"] == "1":
                self.core.config.set("render.engine", "legacy")
            if "disable-gpu" in self.args and self.args["disable-gpu"] == "1":
                self.core.config.set("render.open_gl", False)

        # from log level
        if self.core.config.get("log.level") in ["debug", "info"]:
            render_debug = True

        # disable/enable logging web engine context
        if not render_debug:
            log = QLoggingCategory("qt.webenginecontext")
            log.setFilterRules("*.info=false")
        else:
            os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-logging --log-level=0"

        # OpenGL disable
        if self.core.config.get("render.open_gl") is False:
            if "QTWEBENGINE_CHROMIUM_FLAGS" in os.environ:
                os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] += " --disable-gpu"
            else:
                os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"

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

    def add_loader(self, loader):
        """
        Add data loader to app

        :param loader: data loader instance
        """
        self.core.idx.indexing.register_loader(loader)

    def add_audio_input(self, provider):
        """
        Add audio input provider to app

        :param provider: audio input provider instance
        """
        self.core.audio.register(provider, "input")

    def add_audio_output(self, provider):
        """
        Add audio output provider to app

        :param provider: audio output provider instance
        """
        self.core.audio.register(provider, "output")

    def add_web(self, provider):
        """
        Add web provider to app

        :param provider: web provider instance
        """
        self.core.web.register(provider)

    def add_tool(self, tool):
        """
        Add tool to app

        :param tool: tool instance
        """
        self.tools.register(tool)

    def setup(self):
        """Setup app"""
        self.controller.setup()
        self.tools.setup()
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
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.core.updater.run_check)
        self.update_timer.start(self.update_timer_interval)
        self.logger_message.connect(self.controller.debug.handle_log)
        self.ui.post_setup()
        self.tools.post_setup()

    def update(self):
        """Called on every update (real-time)"""
        self.controller.on_update()
        self.controller.plugins.on_update()
        self.tools.on_update()

    def post_update(self):
        """Called on post-update (lazy)"""
        self.controller.debug.on_post_update()
        self.controller.plugins.on_post_update()
        self.tools.on_post_update()

    @Slot(str)
    def update_status(self, text: str):
        """
        Update status text

        :param text: status text
        """
        self.ui.status(text)

    @Slot(str)
    def update_state(self, state: str):
        """
        Update state

        :param state: state
        """
        self.state = state
        self.ui.tray.set_icon(state)

    def closeEvent(self, event):
        """
        Handle close event

        :param event: close event
        """
        if self.core.config.get('layout.tray.minimize') and self.ui.tray.is_tray:
            event.ignore()
            self.hide()
            return

        self.is_closing = True
        print("Closing...")
        print("Sending terminate signal to all plugins...")
        self.controller.chat.common.stop(exit=True)
        self.controller.plugins.destroy()
        print("Saving ctx groups...")
        self.controller.ctx.save_all()
        print("Saving notepad...")
        self.controller.notepad.save_all()
        print("Saving calendar...")
        self.controller.calendar.save_all()
        print("Saving drawing...")
        self.controller.painter.save_all()
        print("Saving tools...")
        self.tools.on_exit()
        print("Saving layout state...")
        self.controller.layout.save()
        print("Stopping timers...")
        self.timer.stop()
        self.post_timer.stop()
        self.update_timer.stop()
        print("Saving config...")
        self.core.config.save()
        print("Saving presets...")
        self.core.presets.save_all()
        print("Exiting...")
        event.accept()

    def changeEvent(self, event):
        """
        Handle window state change event

        :param event: Event
        """
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized() and self.core.config.get('layout.tray.minimize'):
                self.ui.tray_menu['restore'].setVisible(True)
                self.hide()
                event.ignore()
            else:
                self.prevState = event.oldState()

    def tray_toggle(self):
        """Toggle tray icon"""
        if self.core.config.get('layout.tray.minimize'):
            if self.isVisible():
                if not self.isActiveWindow():
                    self.activateWindow()
                else:
                    self.ui.tray_menu['restore'].setVisible(True)
                    self.hide()
            else:
                self.restore()
        else:
            if self.isMinimized():
                self.restore()
            else:
                if not self.isActiveWindow():
                    self.activateWindow()
                else:
                    self.showMinimized()

    def restore(self):
        """Restore window"""
        if self.prevState == Qt.WindowMaximized or self.windowState() == Qt.WindowMaximized:
            self.showMaximized()
        else:
            self.showNormal()
        self.activateWindow()
        self.ui.tray_menu['restore'].setVisible(False)
