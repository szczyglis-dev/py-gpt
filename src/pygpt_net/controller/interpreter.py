#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.16 15:00:00                  #
# ================================================== #

import os

from PySide6.QtGui import QTextCursor

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem


class Interpreter:
    def __init__(self, window=None):
        """
        Python real-time interpreter controller

        :param window: Window instance
        """
        self.window = window
        self.opened = False
        self.is_edit = False
        self.filename = "_interpreter.py"
        self.file_current = "_interpreter.current.py"
        self.file_input = "_interpreter.input.py"

    def toggle_edit(self):
        """Toggle edit mode"""
        self.is_edit = self.window.ui.nodes['interpreter.edit'].isChecked()
        self.window.interpreter.setReadOnly(not self.is_edit)

        if self.is_edit:
            self.window.ui.nodes['interpreter.edit_label'].setText("Edit Python code:")
            self.load_input()
        else:
            self.window.ui.nodes['interpreter.edit_label'].setText("Output:")
            self.load()

        self.cursor_to_end()

    def cursor_to_end(self):
        """Cursor to end"""
        cur = self.window.interpreter.textCursor()
        cur.movePosition(QTextCursor.End)
        self.window.interpreter.setTextCursor(cur)

    def disable_edit(self):
        """Disable edit mode"""
        self.window.ui.nodes['interpreter.edit'].setChecked(False)
        self.toggle_edit()

    def save_edit(self):
        """Save edit"""
        if not self.is_edit:
            return
        data = self.window.interpreter.toPlainText()
        self.save_input(data)

    def append_output(self, output: str, type="stdout", **kwargs):
        """
        Append output to the interpreter window

        :param output: Output data
        :param type: Output type
        :param kwargs: Additional parameters
        """
        if self.is_edit:
            self.disable_edit()
        if type == "stdin":
            data = ">> "  + str(output)
        else:
            data = str(output)
        cur = self.window.interpreter.textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)
        s = data + "\n"
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertText("\n")
        self.window.interpreter.setTextCursor(cur)  # Update visible cursor
        self.save()

    def load(self):
        """Load output"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.filename)
        content = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        self.window.interpreter.setPlainText(content)
        self.window.ui.nodes['interpreter.input'].setFocus()

    def load_input(self):
        """Load input"""
        data = self.load_prev_input()
        self.window.interpreter.setPlainText(data)
        self.window.interpreter.setFocus()

    def save(self):
        """Save"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.window.interpreter.toPlainText())

    def is_all(self) -> bool:
        """Is all"""
        return self.window.ui.nodes['interpreter.all'].isChecked()

    def load_prev_input(self) -> str:
        """
        Load previous input

        :return: Input data
        """
        input = ""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_input)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                input = f.read()
        return input

    def save_input(self, input: str):
        """
        Save input

        :param input: Input data
        """
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_input)
        with open(path , "w", encoding="utf-8") as f:
            f.write(input)

    def get_output(self) -> str:
        """Get output"""
        return self.window.interpreter.toPlainText()

    def setup(self):
        """Setup"""
        self.load()
        self.update()

    def clear_output(self):
        """Clear output"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.filename)
        if os.path.exists(path):
            os.remove(path)
        self.window.interpreter.clear()

    def clear_input(self):
        """Clear input"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_input)
        if os.path.exists(path):
            os.remove(path)
        self.window.interpreter.clear()

    def clear(self):
        """Clear"""
        if self.is_edit:
            self.clear_input()
        else:
            self.clear_output()

    def clear_all(self):
        """Clear all"""
        self.clear_output()
        self.clear_input()

    def open(self):
        """Open"""
        self.opened = True
        self.window.ui.dialogs.open('interpreter', width=800, height=600)
        self.window.ui.nodes['interpreter.input'].setFocus()
        self.cursor_to_end()

    def close(self):
        """Close"""
        self.opened = False
        self.window.ui.dialogs.close('interpreter')


    def send_input(self):
        """Send input"""
        if self.is_edit:
            self.save_edit()
            self.disable_edit()

        input = str(self.window.ui.nodes['interpreter.input'].toPlainText())
        if self.is_all():
            cmd = "code_execute_all"
        else:
            if input == "":
                return
            cmd = "code_execute"

        commands = [
            {
                "cmd": cmd,
                "params": {
                    "code": input,
                    "path": "_interpreter.tmp.py"
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