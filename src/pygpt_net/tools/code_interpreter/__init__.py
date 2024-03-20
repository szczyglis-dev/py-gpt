#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.20 06:00:00                  #
# ================================================== #

import os

from PySide6.QtGui import QTextCursor

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class CodeInterpreter:
    def __init__(self, window=None):
        """
        Python code interpreter

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
        self.load_input()
        self.load_output()
        self.update()

        # restore
        if self.window.core.config.has("interpreter.input"):
            self.window.ui.nodes['interpreter.input'].setPlainText(self.window.core.config.get("interpreter.input"))
        if self.window.core.config.has("interpreter.execute_all"):
            self.window.ui.nodes['interpreter.all'].setChecked(self.window.core.config.get("interpreter.execute_all"))
        if self.window.core.config.has("interpreter.auto_clear"):
            self.window.ui.nodes['interpreter.auto_clear'].setChecked(self.window.core.config.get("interpreter.auto_clear"))

    def update(self):
        """Update menu"""
        self.update_menu()

    def update_menu(self):
        """Update menu"""
        if self.opened:
            self.window.ui.menu['tools.interpreter'].setChecked(True)
        else:
            self.window.ui.menu['tools.interpreter'].setChecked(False)

    def append_output(self, output: str, type="stdout", **kwargs):
        """
        Append output to the interpreter window

        :param output: Output data
        :param type: Output type
        :param kwargs: Additional parameters
        """
        area = self.window.interpreter
        if type == "stdin":
            data = ">> "  + str(output)
        else:
            data = str(output)
        cur = area.textCursor()
        cur.movePosition(QTextCursor.End)
        s = data + "\n"
        while s:
            head, sep, s = s.partition("\n")
            cur.insertText(head)
            if sep:  # New line if LF
                cur.insertText("\n")
        area.setTextCursor(cur)
        self.save_output()
        self.load_input()

    def load_input(self):
        """Load input data from file"""
        data = self.load_prev_input()
        self.window.ui.nodes['interpreter.code'].setPlainText(data)

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
        data = self.window.interpreter.toPlainText()
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)

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
        self.window.ui.nodes['interpreter.code'].clear()

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
        self.clear_output()

    def clear_all(self):
        """Clear input and output"""
        self.clear_output()
        self.clear_input()

    def send_input(self):
        """Send input to interpreter"""
        # switch to output mode if edit mode is enabled
        self.save_edit()

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

    def update_input(self):
        """Update input data"""
        data = self.window.ui.nodes['interpreter.input'].toPlainText()
        self.window.core.config.set("interpreter.input", data)

    def append_to_input(self, data: str):
        """
        Append data to input

        :param data: Data
        """
        current = self.window.ui.nodes['interpreter.input'].toPlainText()
        if current:
            current += "\n"
        current += data
        self.window.ui.nodes['interpreter.input'].setPlainText(current)

    def append_to_edit(self, data: str):
        """
        Append data to editor

        :param data: Data
        """
        # load input from input file
        input = self.load_prev_input()
        if input:
            input += "\n"
        input += data
        self.save_input(input)
        self.load_input()

    def save_edit(self):
        """Save edit data to file"""
        data = self.window.ui.nodes['interpreter.code'].toPlainText()
        self.save_input(data)

    def open(self):
        """Open interpreter dialog"""
        self.opened = True
        self.load_input()
        self.load_output()
        self.window.ui.dialogs.open('interpreter', width=800, height=600)
        self.window.ui.nodes['interpreter.input'].setFocus()
        self.cursor_to_end()
        self.update()

    def close(self):
        """Close interpreter dialog"""
        self.opened = False
        self.window.ui.dialogs.close('interpreter')
        self.update()

    def toggle(self):
        """Toggle interpreter dialog open/close"""
        if self.opened:
            self.close()
        else:
            self.open()

    def show_hide(self, show: bool = True):
        """
        Show/hide interpreter window

        :param show: show/hide
        """
        if show:
            self.open()
        else:
            self.close()

    def toggle_icon(self, state: bool):
        """
        Toggle interpreter icon

        :param state: State
        """
        self.window.ui.nodes['icon.interpreter'].setVisible(state)

    def toggle_auto_clear(self):
        """Toggle auto clear"""
        self.auto_clear = self.window.ui.nodes['interpreter.auto_clear'].isChecked()
        self.window.core.config.set("interpreter.auto_clear", self.auto_clear)

    def toggle_all(self):
        """Toggle execute all"""
        self.window.core.config.set("interpreter.execute_all", self.window.ui.nodes['interpreter.all'].isChecked())

    def get_output(self) -> str:
        """
        Get current output from interpreter

        :return: Output data
        """
        return self.window.interpreter.toPlainText()

    def get_input(self) -> str:
        """
        Get current input edit code

        :return: Edit code
        """
        return self.window.ui.nodes['interpreter.code'].toPlainText()

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

    def on_exit(self):
        """On exit"""
        pass