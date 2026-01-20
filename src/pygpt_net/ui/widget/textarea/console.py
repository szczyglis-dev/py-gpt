#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.20 21:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtWidgets import QLineEdit, QApplication


class ConsoleInput(QLineEdit):
    def __init__(self, window=None):
        """
        Console input

        :param window: main window
        """
        super(ConsoleInput, self).__init__(window)
        self.window = window
        self.setPlaceholderText("Console... Type your command here")
        self.setProperty('class', 'text-editor')
        self.setFocus()

        # command history storage
        self._history = []
        self._history_index = 0  # points to position after the last item
        self._buffer_before_history = ""  # stores current line when entering history navigation
        self._in_history_mode = False

        # supported commands for TAB auto-completion
        self._commands = []

    def set_commands(self, commands):
        """
        Set supported commands for auto-completion.

        :param commands: list of command strings
        """
        if isinstance(commands, (list, tuple)):
            self._commands = list(commands)

    def add_to_history(self, cmd: str):
        """
        Add command to history.

        :param cmd: command string
        """
        if not cmd:
            return
        # avoid adding the same command twice in a row
        if len(self._history) == 0 or self._history[-1] != cmd:
            self._history.append(cmd)
        # reset navigation state
        self._history_index = len(self._history)
        self._in_history_mode = False
        self._buffer_before_history = ""

    def _history_prev(self):
        """Navigate to previous history item (Up)."""
        if not self._history:
            QApplication.beep()
            return
        if not self._in_history_mode:
            self._buffer_before_history = self.text()
            self._in_history_mode = True
        if self._history_index > 0:
            self._history_index -= 1
            self.setText(self._history[self._history_index])
            self.end(False)
        else:
            QApplication.beep()

    def _history_next(self):
        """Navigate to next history item (Down)."""
        if not self._history:
            QApplication.beep()
            return
        if not self._in_history_mode:
            QApplication.beep()
            return
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            self.setText(self._history[self._history_index])
            self.end(False)
        else:
            # move past the last item: restore buffer and exit history mode
            self._history_index = len(self._history)
            self.setText(self._buffer_before_history)
            self.end(False)
            self._in_history_mode = False
            self._buffer_before_history = ""

    def _longest_common_prefix(self, strings):
        """Compute longest common prefix for a list of strings."""
        if not strings:
            return ""
        s1 = min(strings)
        s2 = max(strings)
        for i, c in enumerate(s1):
            if c != s2[i]:
                return s1[:i]
        return s1

    def _try_autocomplete(self) -> bool:
        """
        Try to auto-complete the current text based on supported commands.

        :return: True if something was completed, False otherwise
        """
        if not self._commands:
            return False

        text = self.text()
        # only complete first token; do not attempt when there is a space
        if not text or " " in text.strip():
            return False

        prefix = text.strip()
        # case-insensitive matching, but insert canonical command form
        matches = [cmd for cmd in self._commands if cmd.lower().startswith(prefix.lower())]

        if len(matches) == 1:
            self.setText(matches[0])
            self.end(False)
            return True

        if len(matches) > 1:
            # complete to the longest common prefix if it extends current prefix
            lcp = self._longest_common_prefix(matches)
            if len(lcp) > len(prefix):
                self.setText(lcp)
                self.end(False)
                return True

        return False

    def keyPressEvent(self, event):
        """
        Key press event

        :param event: key event
        """
        key = event.key()

        # Enter/Return sends the command
        if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.window.core.debug.console.on_send()
            self.setFocus()
            event.accept()
            return

        # Up/Down for history navigation
        if key == QtCore.Qt.Key_Up:
            self._history_prev()
            event.accept()
            return

        if key == QtCore.Qt.Key_Down:
            self._history_next()
            event.accept()
            return

        # TAB or SHIFT+TAB for command auto-completion
        if key in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab):
            completed = self._try_autocomplete()
            if not completed:
                QApplication.beep()
            event.accept()  # prevent focus traversal
            return

        # Any other key exits history navigation mode
        if self._in_history_mode:
            self._in_history_mode = False
            self._history_index = len(self._history)
            self._buffer_before_history = ""

        super(ConsoleInput, self).keyPressEvent(event)

    def focusNextPrevChild(self, next):
        """
        Disable focus traversal with TAB for this widget.
        This prevents Qt from moving focus to other widgets when TAB/SHIFT+TAB is pressed.
        """
        return False