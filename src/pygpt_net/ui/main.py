#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.31 14:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import QTimer, Signal, Slot, QThreadPool, QEvent, Qt, QLoggingCategory, QEventLoop
from PySide6.QtGui import QShortcut, QKeySequence, QKeyEvent
from PySide6.QtWidgets import QMainWindow, QApplication
from qt_material import QtStyleTools

from pygpt_net.core.events import BaseEvent, KernelEvent, ControlEvent
from pygpt_net.app_core import Core
from pygpt_net.controller import Controller
from pygpt_net.tools import Tools
from pygpt_net.ui import UI
from pygpt_net.ui.widget.textarea.web import ChatWebOutput
from pygpt_net.utils import get_app_meta, freeze_updates, set_env, has_env, get_env, trans


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
    appReady = Signal()  # emitted after the first paint to indicate the window is ready on screen

    def __init__(self, app: QApplication, args: dict = None):
        """
        Main window

        :param app: QApplication instance
        :param args: launcher arguments
        """
        super().__init__()
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint | Qt.WindowMaximizeButtonHint)
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
        self.is_post_update = False

        # app ready emission control
        self._app_ready_emitted = False  # ensures single-shot emission

        # load version info
        self.meta = get_app_meta()

        # setup service container
        self.core = Core(self)
        self.core.init()
        self.core.patch()  # patch version if needed
        self.core.post_setup()

        # before render, handle engine args
        self.handle_engine_args()

        # setup thread pool
        self.threadpool = QThreadPool.globalInstance()

        # setup controller
        self.controller = Controller(self)

        # setup tools
        self.tools = Tools(self)

        # init, load settings options, etc.
        self.controller.init()

        # setup UI
        self.ui = UI(self)
        with freeze_updates(self):
            self.ui.init()

        # global shortcuts
        self.shortcuts = []
        self._esc_shortcut = None  # keep a direct handle to temporarily disable during rerouting

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
        CHROMIUM_FLAGS = "QTWEBENGINE_CHROMIUM_FLAGS"

        if not render_debug:
            QLoggingCategory.setFilterRules("*.info=false")
        else:
            set_env(CHROMIUM_FLAGS, "--enable-logging", True)
            set_env(CHROMIUM_FLAGS, "--log-level=0", True)

        # OpenGL disable
        if self.core.config.get("render.open_gl") is False:
            set_env(CHROMIUM_FLAGS, "--disable-gpu", True)

        # log chromium flags
        if (has_env(CHROMIUM_FLAGS) and get_env("PYGPT_APP_ENV") == "dev") or render_debug:
            print("Running with Chromium flags:", get_env(CHROMIUM_FLAGS))

    def add_plugin(self, plugin):
        """
        Add a plugin to the app

        :param plugin: plugin instance
        """
        self.core.plugins.register(plugin)

    def add_llm(self, llm):
        """
        Add a Langchain LLM wrapper to the app

        :param llm: LLM wrapper instance
        """
        self.core.llm.register(llm.id, llm)

    def add_vector_store(self, store):
        """
        Add a vector store provider to the app

        :param store: Vector store provider instance
        """
        self.core.idx.storage.register(store.id, store)

    def add_loader(self, loader):
        """
        Add a data loader to the app

        :param loader: data loader instance
        """
        self.core.idx.indexing.register_loader(loader)

    def add_agent(self, agent):
        """
        Add an agent to the app

        :param agent: agent instance
        """
        self.core.agents.provider.register(agent.id, agent)

    def add_audio_input(self, provider):
        """
        Add an audio input provider to the app

        :param provider: audio input provider instance
        """
        self.core.audio.register(provider, "input")

    def add_audio_output(self, provider):
        """
        Add an audio output provider to the app

        :param provider: audio output provider instance
        """
        self.core.audio.register(provider, "output")

    def add_web(self, provider):
        """
        Add a web provider to the app

        :param provider: web provider instance
        """
        self.core.web.register(provider)

    def add_tool(self, tool):
        """
        Add a tool to the app

        :param tool: tool instance
        """
        self.tools.register(tool)

    def setup(self):
        """Setup app"""
        self.tools.setup()
        self.controller.setup()
        self.controller.plugins.setup()
        self.controller.post_setup()

    def post_setup(self):
        """Called after setup"""
        self.controller.layout.post_setup()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.update)
        self.timer.start(self.timer_interval)
        self.post_timer = QTimer(self)
        self.post_timer.setTimerType(Qt.VeryCoarseTimer)
        self.post_timer.timeout.connect(self.post_update)
        self.post_timer.start(self.post_timer_interval)
        self.update_timer = QTimer(self)
        self.update_timer.setTimerType(Qt.VeryCoarseTimer)
        self.update_timer.timeout.connect(self.core.updater.run_check)
        self.update_timer.start(self.update_timer_interval)
        self.logger_message.connect(self.controller.debug.handle_log)
        self.ui.post_setup()
        self.tools.post_setup()

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self.ui.on_show)

    def paintEvent(self, e):
        """
        On the first paint, announce that the window is actually visible and ready.
        This is used to synchronize closing the external splash screen.
        """
        super().paintEvent(e)
        if not self._app_ready_emitted:
            self._app_ready_emitted = True
            QTimer.singleShot(0, self.appReady.emit)
            # set focus to main window after shown
            QTimer.singleShot(0, self.activateWindow)

    def update(self):
        """Called on every update (real-time)"""
        # self.controller.on_update()
        self.controller.plugins.on_update()
        self.tools.on_update()

    def post_update(self):
        """Called on post-update (lazy)"""
        if self.is_post_update:
            return
        self.is_post_update = True
        try:
            self.controller.debug.on_post_update()
            self.controller.plugins.on_post_update()
            self.tools.on_post_update()
        finally:
            self.is_post_update = False

    @Slot(str)
    def update_status(self, message: str = ""):
        """
        Update global status

        :param message: status message
        """
        self.dispatch(
            KernelEvent(
                KernelEvent.STATUS, {
                    "status": message if isinstance(message, str) else str(message)
                }
            )
        )

    @Slot(str)
    def update_state(self, state: str):
        """
        Update state

        :param state: state
        """
        if state == self.state:
            return
        self.state = state
        self.ui.tray.set_icon(state)

    @Slot(object, bool)
    def dispatch(self, event: BaseEvent, all: bool = False):
        """
        Dispatch App event

        :param event
        :param all: True to dispatch to all plugins
        """
        self.core.dispatcher.dispatch(event, all=all)

    def closeEvent(self, event):
        """
        Handle close event

        :param event: close event
        """
        if self.core.config.get('layout.tray.minimize') and self.ui.tray.is_tray:
            event.ignore()
            self.hide()
            return

        for view in self.findChildren(ChatWebOutput):
            try:
                view.on_delete()
            except Exception:
                pass

        for _ in range(6):
            QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            QApplication.processEvents(QEventLoop.AllEvents, 50)

        self.shutdown()
        event.accept()

    def shutdown(self):
        """
        Shutdown the application gracefully
        This method is called when the application is closing.
        """
        if self.is_closing:
            print("Application is already closing...")
            return
        self.is_closing = True
        print("Closing...")
        print("Sending terminate signal to all...")
        self.controller.kernel.terminate()
        print("Saving ctx groups...")
        self.controller.ctx.save_all()
        print("Saving tabs...")
        self.core.tabs.save()
        print("Saving notepad...")
        self.controller.notepad.save_all()
        print("Saving calendar...")
        self.controller.calendar.save_all()
        print("Saving drawing...")
        self.controller.painter.save_all()
        print("Saving plugins config...")
        self.controller.plugins.save_all()
        print("Saving tools...")
        self.tools.on_exit()
        print("Closing clients...")
        self.controller.kernel.close_clients()
        print("Saving layout state...")
        self.controller.layout.save()
        print("Stopping timers...")
        if self.timer is not None:
            self.timer.stop()
            self.timer.deleteLater()
            self.timer = None
        if self.post_timer is not None:
            self.post_timer.stop()
            self.post_timer.deleteLater()
            self.post_timer = None
        if self.update_timer is not None:
            self.update_timer.stop()
            self.update_timer.deleteLater()
            self.update_timer = None
        print("Saving config...")
        self.core.config.save()
        print("Saving presets...")
        self.core.presets.save_all()
        print("Exiting...")
        print("")
        print(f"{trans('exit.msg')} https://pygpt.net/#donate")

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
        if self.prevState == Qt.WindowMaximized or self.isMaximized():
            self.showMaximized()
        else:
            self.showNormal()
        self.activateWindow()
        self.ui.tray_menu['restore'].setVisible(False)

    # ----- Global ESC routing that preserves widget-level ESC handling -----

    def _deliver_escape_to(self, target) -> bool:
        """
        Synthesize ESC keypress to the focused/popup widget so it can run its own close logic.
        Temporarily disables the global ESC shortcut to avoid re-triggering itself.
        """
        if target is None or not target.isVisible():
            return False
        try:
            if self._esc_shortcut is not None:
                self._esc_shortcut.setEnabled(False)
            press = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
            release = QKeyEvent(QEvent.KeyRelease, Qt.Key_Escape, Qt.NoModifier)
            QApplication.sendEvent(target, press)
            QApplication.sendEvent(target, release)
        except Exception:
            pass
        finally:
            if self._esc_shortcut is not None:
                QTimer.singleShot(0, lambda: self._esc_shortcut.setEnabled(True))
        return True

    def _route_escape_to_focus_or_popup(self) -> bool:
        """
        Route ESC to the widget that currently owns focus (prefer) or active popup widget.
        Returns True when ESC was delivered to a target.
        """
        popup = QApplication.activePopupWidget()
        if popup is not None and popup.isVisible():
            try:
                fw = QApplication.focusWidget()
                if self._deliver_escape_to(fw):
                    return True
            except Exception:
                pass
            return True

        modal = QApplication.activeModalWidget()
        if modal is not None and modal.isVisible():
            try:
                modal.close()
            except Exception:
                pass
            return True

        # No popup or modal to close
        return False

    def _on_escape_shortcut(self):
        """
        Global ESC: deliver ESC to the focused/popup widget first so it can handle and cleanup correctly.
        If nothing handles it, run the app-level escape handler.
        """
        if self._route_escape_to_focus_or_popup():
            return
        try:
            self.controller.access.on_escape()
        except Exception:
            pass

    def setup_global_shortcuts(self):
        """Setup global shortcuts"""
        if not hasattr(self, 'core') or not hasattr(self.core, 'config'):
            return

        # unregister existing shortcuts
        if hasattr(self, 'shortcuts'):
            for shortcut in self.shortcuts:
                shortcut.setEnabled(False)
                shortcut.deleteLater()
            self.shortcuts.clear()
        else:
            self.shortcuts = []
        self._esc_shortcut = None

        # Handle the Escape key
        escape_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        escape_shortcut.setContext(Qt.ApplicationShortcut)
        # escape_shortcut.setAutoRepeat(False)  # avoid spamming when holding the key
        escape_shortcut.activated.connect(self._on_escape_shortcut)
        self.shortcuts.append(escape_shortcut)
        self._esc_shortcut = escape_shortcut

        config = self.core.config.get("access.shortcuts")
        if config is None:
            return

        for shortcut_conf in config:
            key = shortcut_conf.get('key', '')
            key_modifier = shortcut_conf.get('key_modifier', '')
            action_name = shortcut_conf.get('action')

            if not key or not action_name:
                continue

            key_sequence_parts = []
            if key_modifier and key_modifier != '---':
                if key_modifier == "Control":
                    key_modifier = "Ctrl"
                key_sequence_parts.append(key_modifier)
            key_sequence_parts.append(key)
            key_sequence_str = '+'.join(key_sequence_parts)
            key_sequence = QKeySequence(key_sequence_str)

            shortcut = QShortcut(key_sequence, self)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(
                lambda checked=False, action=action_name: self.dispatch(ControlEvent(action))
            )
            self.shortcuts.append(shortcut)