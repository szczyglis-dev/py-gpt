#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.02 19:00:00                  #
# ================================================== #

import copy

from PySide6 import QtCore
from PySide6.QtCore import QObject, QEvent

from pygpt_net.core.access.events import ControlEvent


class Shortcuts:
    def __init__(self, window=None):
        """
        Shortcuts core

        :param window: Window instance
        """
        self.window = window

    def get_keys_choices(self) -> list:
        """
        Get keys choices with identical key and value.
        """
        keys = [{chr(i): chr(i)} for i in range(65, 91)]  # A-Z
        keys.extend([{str(i): str(i)} for i in range(0, 10)])  # 0-9
        keys.extend([{str(i): str(i)} for i in range(1, 13)])  # F1-F12
        symbols = [
            'Space', 'Comma', 'Period', 'Slash', 'Backslash', 'Minus', 'Equal',
            'Semicolon', 'Apostrophe'
        ]
        keys.extend([{name: name} for name in symbols])
        return keys

    def get_modifiers_choices(self) -> list:
        """
        Get modifiers choices with identical key and value.
        """
        modifiers_names = [
            'Shift', 'Control', 'Meta', 'Alt', 'Escape', 'Tab', 'Backtab',
            'Backspace', 'Return', 'Enter', 'Insert', 'Delete', 'Pause',
            'Print', 'SysReq', 'Clear', 'Home', 'End', 'Left', 'Up',
            'Right', 'Down', 'PageUp', 'PageDown', 'Super_L', 'Super_R', 'Menu'
        ]
        modifiers = [{name: name} for name in modifiers_names]
        return modifiers


class GlobalShortcutFilter(QObject):
    def __init__(self, window=None):
        super().__init__()
        self.window = window

    def eventFilter(self, obj, event):
        """
        Event filter for global shortcuts handling

        :param obj: object
        :param event: event
        :return: True if event was handled
        """
        try:
            # esc key
            if event.type() == QEvent.KeyPress and event.key() == QtCore.Qt.Key_Escape:
                self.window.controller.access.on_escape()

            # shortcuts
            config = copy.deepcopy(self.window.core.config.get("access.shortcuts"))
            for shortcut in config:
                if shortcut['key'] == "" or shortcut['key'] is None:
                    continue
                shortcut['key'] = getattr(QtCore.Qt, 'Key_' + str(shortcut['key']))
                shortcut['key_modifier'] = getattr(QtCore.Qt, str(shortcut['key_modifier']) + 'Modifier', QtCore.Qt.NoModifier)
            if event.type() == QEvent.KeyPress:
                for shortcut in config:
                    if (event.key() == shortcut['key'] and
                        (shortcut['key_modifier'] == QtCore.Qt.NoModifier or event.modifiers() == shortcut['key_modifier'])
                    ):
                        self.window.core.dispatcher.dispatch(ControlEvent(shortcut['action']))
                        return True
        except Exception as e:
            print(e)
            pass
        return False