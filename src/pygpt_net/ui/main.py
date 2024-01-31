#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.01 00:00:00                  #
# ================================================== #

from PySide6.QtCore import QTimer, Signal, Slot, QThreadPool, QEvent
from PySide6.QtWidgets import QApplication, QMainWindow
from qt_material import QtStyleTools

from pygpt_net.container import Container
from pygpt_net.controller import Controller
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
        self.threadpool = None
        self.is_closing = False
        self.timer_interval = 30
        self.post_timer_interval = 1000
        self.state = self.STATE_IDLE

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

        # setup signals
        self.statusChanged.connect(self.update_status)
        self.stateChanged.connect(self.update_state)

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
        self.logger_message.connect(self.controller.debug.handle_log)
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
        self.is_closing = True
        print("Closing...")
        print("Sending terminate signal to plugins...")
        self.controller.chat.common.stop()
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

    def changeEvent(self, event):
        """
        Handle window state change event

        :param event: Event
        """
        if not self.core.config.get('layout.tray.minimize'):
            return

        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                self.hide()
                self.ui.tray_menu['restore'].setVisible(True)
                event.ignore()

    def restore(self):
        """Restore window"""
        self.showNormal()
        self.activateWindow()
        self.ui.tray_menu['restore'].setVisible(False)
