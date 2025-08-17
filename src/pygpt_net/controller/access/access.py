#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.18 01:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow

from pygpt_net.core.events import BaseEvent, ControlEvent, AppEvent

from .control import Control
from .voice import Voice


class Access:
    def __init__(self, window=None):
        """
        Accessibility controller

        :param window: Window instance
        """
        self.window = window
        self.control = Control(window)
        self.voice = Voice(window)

    def setup(self):
        """Setup accessibility"""
        self.voice.setup()

    def reload(self):
        """Reload accessibility"""
        self.voice.setup()

    def update(self):
        """Update accessibility"""
        self.voice.update()

    def handle(self, event: BaseEvent):
        """
        Handle accessibility event (ControlEvent or AppEvent)

        :param event: event object
        """
        if isinstance(event, ControlEvent):
            self.control.handle(event)
            event.stop = True
        elif isinstance(event, AppEvent):
            self.handle_app(event)
            event.stop = True

    def handle_app(self, event: AppEvent):
        """
        Handle accessibility event (AppEvent only)

        :param event: event object
        """
        self.window.core.debug.info("[app] Event: " + event.name)
        if event.name == AppEvent.VOICE_CONTROL_TOGGLE:
            self.voice.toggle_recording()
        if self.window.core.access.voice.is_muted(event.name):
            return  # ignore muted events
        self.voice.play(event)  # handle audio synthesis

    def on_escape(self):
        """Handle escape key"""
        # stop voice recording if active
        if self.voice.is_recording:
            self.voice.stop_recording(timeout=True)
        if self.window.core.plugins.get("audio_input").handler_simple.is_recording:
            self.window.core.plugins.get("audio_input").handler_simple.stop_recording(timeout=True)

        # stop audio output if playing
        self.window.controller.audio.stop_output()

        # stop generating if active
        self.window.controller.kernel.stop()

        # close top dialog if any
        self.close_top_dialog_if_any()

    def close_top_dialog_if_any(self) -> bool:
        """Close top dialog if any"""
        app = QApplication.instance()

        try:
            w = app.activeModalWidget()
            if w:
                top = w.window()
                if top and (top.windowFlags() & (Qt.Dialog | Qt.Sheet | Qt.Tool | Qt.Popup)):
                    top.close()
                    return True
        except Exception:
            pass

        try:
            w = app.activeWindow()
            if w:
                top = w.window()
                if isinstance(top, QMainWindow):
                    pass
                else:
                    if top and (top.windowFlags() & (Qt.Dialog | Qt.Sheet | Qt.Tool | Qt.Popup)):
                        top.close()
                        return True
        except Exception:
            pass

        try:
            for top in reversed(QApplication.topLevelWidgets()):
                if not top.isVisible():
                    continue
                if isinstance(top, QMainWindow):
                    continue
                if top.windowFlags() & (Qt.Dialog | Qt.Sheet | Qt.Tool | Qt.Popup):
                    top.close()
                    return True
        except Exception:
            pass

        return False