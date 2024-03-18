#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.18 03:00:00                  #
# ================================================== #

import os

from PySide6.QtGui import QTextCursor

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Interpreter:
    def __init__(self, window=None):
        """
        Python real-time interpreter controller

        :param window: Window instance
        """
        self.window = window
        self.opened = False
        self.is_edit = False
        self.auto_clear = True

        # interpreter data files in /data directory
        self.file_current = ".interpreter.current.py"
        self.file_input = ".interpreter.input.py"
        self.file_output = ".interpreter.output.py"

    def setup(self):
        """Setup"""
        self.load_output()
        self.update()

    def update(self):
        """Update icon"""
        pass
        """
        self.toggle_icon(self.window.controller.plugins.is_type_enabled('interpreter'))
        """

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
        cur = self.window.interpreter.textCursor()
        cur.movePosition(QTextCursor.End)
        s = data + "\n"
        while s:
            head, sep, s = s.partition("\n")
            cur.insertText(head)
            if sep:  # New line if LF
                cur.insertText("\n")
        self.window.interpreter.setTextCursor(cur)
        self.save_output()

    def load_input(self):
        """Load input data from file"""
        data = self.load_prev_input()
        self.window.interpreter.setPlainText(data)
        self.window.interpreter.setFocus()

    def load_output(self):
        """Load output data from file"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_output)
        content = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        self.window.interpreter.setPlainText(content)
        self.window.ui.nodes['interpreter.input'].setFocus()

    def save_output(self):
        """Save output data to file"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_output)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.window.interpreter.toPlainText())

    def load_prev_input(self) -> str:
        """
        Load previous input data from file

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
        Save input data

        :param input: Input data
        """
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_input)
        with open(path , "w", encoding="utf-8") as f:
            f.write(input)

    def clear_input(self):
        """Clear input"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_input)
        if os.path.exists(path):
            os.remove(path)
        self.window.interpreter.clear()

    def clear_output(self):
        """Clear output"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_output)
        if os.path.exists(path):
            os.remove(path)
        self.window.interpreter.clear()

    def clear(self, force: bool = False):
        """
        Clear current window

        :param force: Force clear
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='interpreter.clear',
                id=0,
                msg=trans("interpreter.clear.confirm"),
            )
            return
        if self.is_edit:
            self.clear_input()
        else:
            self.clear_output()

    def clear_all(self):
        """Clear input and output"""
        self.clear_output()
        self.clear_input()

    def send_input(self):
        """Send input to interpreter"""
        # switch to output mode if edit mode is enabled
        if self.is_edit:
            self.save_edit()
            self.disable_edit()

        if self.auto_clear:
            self.clear_output()

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
                    "path": self.file_current,
                },
                "silent": True,
            }
        ]
        event = Event(Event.CMD_EXECUTE, {
            'commands': commands,
        })
        event.ctx = CtxItem()  # tmp
        self.window.controller.command.dispatch_only(event)
        self.window.ui.nodes['interpreter.input'].clear()
        self.window.ui.nodes['interpreter.input'].setFocus()

    def toggle_edit(self):
        """Toggle edit mode"""
        self.is_edit = self.window.ui.nodes['interpreter.edit'].isChecked()
        self.window.interpreter.setReadOnly(not self.is_edit)

        if self.is_edit:
            self.window.ui.nodes['interpreter.edit_label'].setText(trans("interpreter.edit_label.edit"))
            self.load_input()
        else:
            self.window.ui.nodes['interpreter.edit_label'].setText(trans("interpreter.edit_label.output"))
            self.load_output()

        self.cursor_to_end()

    def save_edit(self):
        """Save edit data to file"""
        if not self.is_edit:
            return
        data = self.window.interpreter.toPlainText()
        self.save_input(data)

    def open(self):
        """Open interpreter dialog"""
        self.opened = True
        self.window.ui.dialogs.open('interpreter', width=800, height=600)
        self.window.ui.nodes['interpreter.input'].setFocus()
        self.cursor_to_end()

    def close(self):
        """Close interpreter dialog"""
        self.opened = False
        self.window.ui.dialogs.close('interpreter')

    def toggle(self):
        """Toggle interpreter dialog open/close"""
        if self.opened:
            self.close()
        else:
            self.open()

    def toggle_icon(self, state: bool):
        """
        Toggle interpreter icon

        :param state: State
        """
        self.window.ui.nodes['icon.interpreter'].setVisible(state)

    def toggle_auto_clear(self):
        """Toggle auto clear"""
        self.auto_clear = self.window.ui.nodes['interpreter.auto_clear'].isChecked()

    def get_data(self) -> str:
        """
        Get current data from interpreter

        :return: Output data
        """
        return self.window.interpreter.toPlainText()

    def is_all(self) -> bool:
        """
        Check if execute all is enabled

        :return: True if execute all is enabled
        """
        return self.window.ui.nodes['interpreter.all'].isChecked()

    def cursor_to_end(self):
        """Move cursor to end"""
        cur = self.window.interpreter.textCursor()
        cur.movePosition(QTextCursor.End)
        self.window.interpreter.setTextCursor(cur)

    def disable_edit(self):
        """Disable edit mode"""
        self.window.ui.nodes['interpreter.edit'].setChecked(False)
        self.toggle_edit()