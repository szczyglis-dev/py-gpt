#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.19 01:00:00                  #
# ================================================== #

import os

from PySide6.QtGui import QTextCursor, QAction, QIcon

from pygpt_net.tools.base import BaseTool
from pygpt_net.tools.code_interpreter.ui.dialogs import Interpreter
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class CodeInterpreter(BaseTool):
    def __init__(self, *args, **kwargs):
        """
        Python code interpreter

        :param window: Window instance
        """
        super(CodeInterpreter, self).__init__(*args, **kwargs)
        self.id = "interpreter"
        self.opened = False
        self.is_edit = False
        self.auto_clear = True
        self.dialog = None

        # interpreter data files in /data directory
        self.file_current = ".interpreter.current.py"
        self.file_input = ".interpreter.input.py"
        self.file_output = ".interpreter.output.py"

    def setup(self):
        """Setup"""
        self.load_history()
        self.load_output()
        self.update()

        # restore
        if self.window.core.config.has("interpreter.input"):
            self.window.ui.nodes['interpreter.input'].setPlainText(self.window.core.config.get("interpreter.input"))
        if self.window.core.config.has("interpreter.execute_all"):
            self.window.ui.nodes['interpreter.all'].setChecked(self.window.core.config.get("interpreter.execute_all"))
        if self.window.core.config.has("interpreter.auto_clear"):
            self.window.ui.nodes['interpreter.auto_clear'].setChecked(self.window.core.config.get("interpreter.auto_clear"))

    def on_reload(self):
        """On app profile reload"""
        self.setup()

    def update(self):
        """Update menu"""
        self.update_menu()

    def update_menu(self):
        """Update menu"""
        """
        if self.opened:
            self.window.ui.menu['tools.interpreter'].setChecked(True)
        else:
            self.window.ui.menu['tools.interpreter'].setChecked(False)
        """

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
        self.load_history()

    def load_history(self):
        """Load history data from file"""
        data = self.get_history()
        self.window.ui.nodes['interpreter.code'].setPlainText(data)
        self.cursor_to_end()

    def get_output(self) -> str:
        """
        Load and get output from file

        :return: Output data
        """
        data = ""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_output)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = f.read()
                except:
                    pass
        return data

    def load_output(self):
        """Load output data from file"""
        data = self.get_output()
        self.window.interpreter.setPlainText(data)
        self.window.ui.nodes['interpreter.input'].setFocus()

    def save_output(self):
        """Save output data to file"""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_output)
        data = self.window.interpreter.toPlainText()
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)

    def get_history(self) -> str:
        """
        Load and get history from file

        :return: History data
        """
        data = ""
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_input)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    data = f.read()
                except:
                    pass
        return data

    def save_history(self, input: str):
        """
        Save input data

        :param input: Input data
        """
        path = os.path.join(self.window.core.config.get_user_dir("data"), self.file_input)
        with open(path , "w", encoding="utf-8") as f:
            f.write(input)

    def clear_history(self):
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
        self.clear_history()

    def send_input(self):
        """Send input to interpreter"""
        self.store_history()
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
        prev = self.get_history()
        if prev:
            prev += "\n"
        prev += data
        self.save_history(prev)
        self.load_history()

    def store_history(self):
        """Save history data to file"""
        data = self.window.ui.nodes['interpreter.code'].toPlainText()
        self.save_history(data)

    def open(self):
        """Open interpreter dialog"""
        self.opened = True
        self.load_history()
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

    def get_current_output(self) -> str:
        """
        Get current output from interpreter

        :return: Output data
        """
        return self.window.interpreter.toPlainText()

    def get_current_history(self) -> str:
        """
        Get code from history

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
        cur = self.window.ui.nodes['interpreter.code'].textCursor()
        cur.movePosition(QTextCursor.End)
        self.window.ui.nodes['interpreter.code'].setTextCursor(cur)

    def setup_menu(self) -> dict:
        """
        Setup main menu

        :return dict with menu actions
        """
        actions = {}
        actions["interpreter"] = QAction(
            QIcon(":/icons/code.svg"),
            trans("menu.tools.interpreter"),
            self.window,
            checkable=False,
        )
        actions["interpreter"].triggered.connect(
            lambda: self.toggle()
        )
        return actions

    def setup_dialogs(self):
        """Setup dialogs (static)"""
        self.dialog = Interpreter(self.window)
        self.dialog.setup()

    def setup_theme(self):
        """Setup theme"""
        size = self.window.core.config.get('font_size')
        self.window.interpreter.value = size

    def get_lang_mappings(self) -> dict:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {
            'menu.text': {
                'tools.interpreter': 'menu.tools.interpreter',
            }
        }