#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.16 12:00:00                  #
# ================================================== #

import os

from PySide6.QtGui import QTextCursor

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem


class Interpreter:
    def __init__(self, window=None):
        """
        Interpreter controller

        :param window: Window instance
        """
        self.window = window
        self.opened = False
        self.filename = "_interpreter.py"

    def append_output(self, output, type="stdout", **kwargs):
        """
        Append output to the interpreter window

        :param output: Output data
        :param type: Output type
        :param kwargs: Additional parameters
        """
        if type == "stdin":
            data = ">> "  + str(output)
        else:
            data = str(output)
        cur = self.window.interpreter.textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)
        s = str(data) + "\n"
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertText("\n")
        self.window.interpreter.setTextCursor(cur)  # Update visible cursor
        self.save()

    def load(self):
        """Load"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.window.interpreter.setPlainText(f.read())

    def save(self):
        """Save"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.window.interpreter.toPlainText())

    def get_output(self) -> str:
        """Get output"""
        return self.window.interpreter.toPlainText()

    def setup(self):
        """Setup"""
        self.load()
        self.update()

    def clear(self):
        """Clear"""
        self.window.interpreter.clear()
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.filename)
        if os.path.exists(path):
            os.remove(path)
        pass

    def open(self):
        """Open"""
        self.opened = True
        self.window.ui.dialogs.open('interpreter', width=800, height=600)
        self.window.ui.nodes['interpreter.input'].setFocus()

    def close(self):
        """Close"""
        self.opened = False
        self.window.ui.dialogs.close('interpreter')


    def send_input(self):
        """Send input"""
        input = str(self.window.ui.nodes['interpreter.input'].toPlainText())
        if not input:
            return
        commands = [
            {
                "cmd": "code_execute",
                "params": {
                    "code": input,
                    "path": "_interpreter.current.py"
                },
                "silent": True,
            }
        ]
        event = Event(Event.CMD_EXECUTE, {
            'commands': commands,
        })
        event.ctx = CtxItem()  # tmp
        self.window.controller.command.dispatch(event)
        self.window.ui.nodes['interpreter.input'].clear()
        self.window.ui.nodes['interpreter.input'].setFocus()

    def toggle(self):
        """Toggle"""
        if self.opened:
            self.close()
        else:
            self.open()

    def toggle_icon(self, state: bool):
        """
        Toggle icon

        :param state: State
        """
        self.window.ui.nodes['icon.interpreter'].setVisible(state)

    def update(self):
        """Update"""
        self.toggle_icon(self.window.controller.plugins.is_type_enabled('interpreter'))