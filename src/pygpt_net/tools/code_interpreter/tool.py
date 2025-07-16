#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.17 01:00:00                  #
# ================================================== #

import json
import os
from time import strftime
from typing import Dict

from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor, QAction, QIcon
from PySide6.QtWidgets import QWidget

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.tools.base import BaseTool
from pygpt_net.tools.code_interpreter.ui.dialogs import Tool
from pygpt_net.core.events import Event, KernelEvent, BaseEvent, RenderEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans
from .ui.html import HtmlOutput, CodeBlock

from .ui.widgets import PythonInput, PythonOutput, ToolWidget, ToolSignals


class CodeInterpreter(BaseTool):
    def __init__(self, *args, **kwargs):
        """
        Python code interpreter

        :param window: Window instance
        """
        super(CodeInterpreter, self).__init__(*args, **kwargs)
        self.id = "interpreter"
        self.has_tab = True
        self.tab_title = "menu.tools.interpreter"
        self.tab_icon = ":/icons/code.svg"
        self.opened = False
        self.is_edit = False
        self.auto_clear = False
        self.dialog = None
        self.ipython = True
        self.auto_opened = False
        self.signals = ToolSignals()

        # interpreter data files in /data directory
        self.file_current = ".interpreter.current.py"
        self.file_input = ".interpreter.input.py"
        self.file_output = ".interpreter.output.py"
        self.file_output_json = ".interpreter.output.json"

        # buffers
        self.input_buffer = ""
        self.output_buffer = ""

    def setup(self):
        """Setup"""
        self.load_history()
        self.load_output()
        self.update()

        # restore
        if self.window.core.config.has("interpreter.input"):
            self.signals.update_input.emit(self.window.core.config.get("interpreter.input"))
        if self.window.core.config.has("interpreter.execute_all"):
            self.signals.set_checkbox_all.emit(self.window.core.config.get("interpreter.execute_all"))
        if self.window.core.config.has("interpreter.auto_clear"):
            self.signals.set_checkbox_auto_clear.emit(self.window.core.config.get("interpreter.auto_clear"))
        if self.window.core.config.has("interpreter.ipython"):
            self.signals.set_checkbox_ipython.emit(self.window.core.config.get("interpreter.ipython"))
        if self.ipython:
            self.signals.toggle_all_visible.emit(False)

        # set initial size
        if not self.window.core.config.has("interpreter.dialog.initialized"):
            self.set_initial_size()
            self.window.core.config.set("interpreter.dialog.initialized", True)

    def handle(self, event: BaseEvent):
        """
        Handle event

        :param event: Event instance
        """
        name = event.name
        if name == RenderEvent.ON_THEME_CHANGE:
            self.reload_view()  # reload web view on theme change

    def set_initial_size(self):
        """Set default sizes"""
        def set_initial_splitter_height():
            total_height = self.window.ui.splitters['interpreter'].size().height()
            if total_height > 0:
                size_output = int(total_height * 0.85)
                size_input = total_height - size_output
                self.window.ui.splitters['interpreter'].setSizes([size_output, size_input])
            else:
                QTimer.singleShot(0, set_initial_splitter_height)
        QTimer.singleShot(0, set_initial_splitter_height)

        def set_initial_splitter_dialog_height():
            total_height = self.window.ui.splitters['interpreter_dialog'].size().height()
            if total_height > 0:
                size_output = int(total_height * 0.85)
                size_input = total_height - size_output
                self.window.ui.splitters['interpreter_dialog'].setSizes([size_output, size_input])
            else:
                QTimer.singleShot(0, set_initial_splitter_dialog_height)
        QTimer.singleShot(0, set_initial_splitter_dialog_height)

        def set_initial_splitter_width():
            total_width = self.window.ui.splitters['interpreter.columns'].size().width()
            if total_width > 0:
                size_output = int(total_width * 0.85)
                size_history = total_width - size_output
                self.window.ui.splitters['interpreter.columns'].setSizes([size_output, size_history])
            else:
                QTimer.singleShot(0, set_initial_splitter_width)
        QTimer.singleShot(0, set_initial_splitter_width)

    def handle_ipython_output(self, line: str):
        """
        Handle ipython output

        :param line: Output line
        """
        self.append_output(line)

    def on_reload(self):
        """On app profile reload"""
        self.setup()
        self.reload_view()

    def reload_view(self):
        """Reload view"""
        self.signals.reload_view.emit()

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

    def output_begin(self, type: str = "stdout"):
        """
        Begin output

        :param type: Output type (stdout, stderr, etc.)
        """
        if type == "stdout":
            self.output_buffer = ""
        elif type == "stdin":
            self.input_buffer = ""
        self.signals.begin_output.emit(type)

    def output_end(self, type: str = "stdout"):
        """
        End output

        :param type: Output type (stdout, stderr, etc.)
        """
        # extract data files from output buffer
        ctx = CtxItem()
        images = []
        files = []
        if type == "stdout":
            if self.output_buffer:
                self.window.core.filesystem.parser.extract_data_files(ctx, self.output_buffer)
                if ctx.images:
                    images = ctx.images
                if ctx.files:
                    files = ctx.files
            self.output_buffer = ""  # clear buffer
        elif type == "stdin":
            self.input_buffer = ""
        self.signals.end_output.emit(type, ctx)

        if images or files:
            self.save_output_nodes()  # update nodes

    def append_output(self, data: str, type="stdout", **kwargs):
        """
        Append output to the interpreter window

        :param data: Data to append
        :param type: Output type
        :param kwargs: Additional parameters
        """
        if type in ["stdout", "stderr"]:
            self.output_buffer += str(data)
        elif type == "stdin":
            self.input_buffer += str(data)
        self.signals.update.emit(data, type, True)
        self.save_output()
        self.load_history()

    def get_path_input(self) -> str:
        """
        Get input path

        :return: Input path
        """
        return os.path.join(self.window.core.config.get_user_dir("data"), self.file_input)

    def get_path_output(self) -> str:
        """
        Get output path

        :return: Output path
        """
        return os.path.join(self.window.core.config.get_user_dir("data"), self.file_output)

    def get_path_output_json(self) -> str:
        """
        Get output path for JSON files

        :return: Output path
        """
        return os.path.join(self.window.core.config.get_user_dir("data"), self.file_output_json)

    def get_widget(self) -> ToolWidget:
        """
        Get tool widget

        :return: ToolWidget instance
        """
        return self.dialog.widget

    def get_widget_history(self) -> HtmlOutput:
        """
        Get history widget

        :return: PythonOutput widget
        """
        return self.dialog.widget.history

    def get_widget_output(self) -> HtmlOutput:
        """
        Get output widget

        :return: PythonOutput widget
        """
        return self.dialog.widget.output

    def get_widget_input(self) -> PythonInput:
        """
        Get input widget

        :return: PythonInput widget
        """
        return self.dialog.widget.input

    def load_history(self):
        """Load history data from file"""
        data = self.get_history()
        self.signals.update_history.emit(data)

    def get_output(self) -> str:
        """
        Load and get output from file

        :return: Output data
        """
        data = ""
        path = self.get_path_output()
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
        # self.signals.update.emit(data, "stdout", False)
        self.signals.focus_input.emit()

        # from nodes
        items = []
        path_json = self.get_path_output_json()
        if os.path.exists(path_json):
            with open(path_json, "r", encoding="utf-8") as f:
                try:
                    items = json.load(f)
                except:
                    pass
        nodes = []
        for item in items:
            node = CodeBlock(
                content=item.get("content", ""),
                type=item.get("type", "text"),
                images=item.get("images", []),
                files=item.get("files", []),
            )
            nodes.append(node)
        self.signals.restore_nodes.emit(nodes)

    def save_output(self):
        """Save output data to file"""
        path = self.get_path_output()
        data = self.get_widget_output().get_plaintext()
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)

        # save nodes
        self.save_output_nodes()

    def save_output_nodes(self):
        """Save output nodes to file"""
        nodes = self.get_widget_output().get_nodes()
        items = []
        for node in nodes:
            item = {
                "content": node.content,
                "type": node.type,
                "images": node.images,
                "files": node.files,
            }
            items.append(item)
        data = json.dumps(items, indent=4, ensure_ascii=False)
        path_json = self.get_path_output_json()
        with open(path_json, "w", encoding="utf-8") as f:
            f.write(data)

    def get_history(self) -> str:
        """
        Load and get history from file

        :return: History data
        """
        data = ""
        path = self.get_path_input()
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
        path = self.get_path_input()
        with open(path , "w", encoding="utf-8") as f:
            f.write(input)

    def clear_history(self):
        """Clear input"""
        path = self.get_path_input()
        if os.path.exists(path):
            os.remove(path)
        self.signals.clear_history.emit()

    def clear_output(self):
        """Clear output"""
        path = self.get_path_output()
        if os.path.exists(path):
            os.remove(path)
        self.signals.clear_output.emit()

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

    def restart_kernel(self):
        """Restart kernel"""
        print("Sending restart event...")
        commands = [
            {
                "cmd": "ipython_kernel_restart",
                "params": {},
                "silent": True,
                "force": True,
            }
        ]
        event = Event(Event.CMD_EXECUTE, {
            'commands': commands,
            'silent': True,
        })
        event.ctx = CtxItem()  # tmp
        self.window.controller.command.dispatch_only(event)
        self.signals.focus_input.emit()
        event = KernelEvent(KernelEvent.STATUS, {
            'status': "[OK] Kernel restarted at " + strftime("%H:%M:%S") + ".",
        })
        self.window.dispatch(event)

    def is_ipython(self) -> bool:
        """
        Check if ipython is enabled

        :return: True if ipython is enabled, False otherwise
        """
        return self.ipython

    def is_opened(self) -> bool:
        """
        Check if interpreter dialog is opened

        :return: True if dialog is opened, False otherwise
        """
        return self.opened

    def send_input(self, widget: ToolWidget):
        """
        Send input to interpreter

        :param widget: PythonInput widget
        """
        self.store_history(widget)
        if self.auto_clear:
            self.clear_output()

        input_textarea = widget.input
        input = str(input_textarea.toPlainText()).strip()

        # replace tab with 4 spaces
        input = input.replace("\t", "    ")

        if input == "/restart":
            self.restart_kernel()
            input_textarea.clear()
            input_textarea.setFocus()
            return
        elif input == "/clear":
            self.clear(force=True)
            input_textarea.clear()
            input_textarea.setFocus()
            return

        if self.is_all():
            cmd = "code_execute_all"
        else:
            if input == "":
                return
            cmd = "code_execute"

        if self.ipython:
            cmd = "ipython_execute"

        commands = [
            {
                "cmd": cmd,
                "params": {
                    "code": input,
                    "path": self.file_current,
                },
                "silent": True,
                "force": True,
            }
        ]
        event = Event(Event.CMD_EXECUTE, {
            'commands': commands,
            'silent': True,
        })
        event.ctx = CtxItem()  # tmp
        self.window.controller.command.dispatch_only(event)
        input_textarea.clear()
        input_textarea.setFocus()

    def run_input(self, input: str):
        """
        Run input code directly

        :param input: Code to execute
        """
        if input == "/restart":
            self.restart_kernel()
            return
        elif input == "/clear":
            self.clear(force=True)
            return

        if self.is_all():
            cmd = "code_execute_all"
        else:
            if input == "":
                return
            cmd = "code_execute"

        if self.ipython:
            cmd = "ipython_execute"

        commands = [
            {
                "cmd": cmd,
                "params": {
                    "code": input,
                    "path": self.file_current,
                },
                "silent": True,
                "force": True,
            }
        ]
        event = Event(Event.CMD_EXECUTE, {
            'commands': commands,
            'silent': True,
        })
        event.ctx = CtxItem()  # tmp
        self.window.controller.command.dispatch_only(event)

    def update_input(self):
        """Update input data"""
        data = self.get_widget_input().toPlainText()
        self.window.core.config.set("interpreter.input", data)

    def append_to_input(self, data: str):
        """
        Append data to input

        :param data: Data
        """
        self.signals.append_input.emit(data)

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

    def store_history(self, widget: ToolWidget):
        """
        Save history data to file

        :param widget: ToolWidget
        """
        if not widget.history:
            return
        data = widget.history.get_plaintext()
        self.save_history(data)

    def open(self):
        """Open interpreter dialog"""
        self.opened = True
        self.auto_opened = False
        self.load_history()
        self.load_output()
        self.window.ui.dialogs.open('interpreter', width=800, height=600)
        self.get_widget_input().setFocus()
        self.dialog.widget.on_open()
        self.cursor_to_end()
        self.scroll_to_bottom()
        self.update()

    def close(self):
        """Close interpreter dialog"""
        self.opened = False
        self.window.ui.dialogs.close('interpreter')
        self.update()

    def auto_open(self):
        """Auto open dialog or tab"""
        if self.window.controller.ui.tabs.is_current_tool(self.id):
            tool_col = self.window.controller.ui.tabs.get_tool_column(self.id)
            current_col = self.window.controller.ui.tabs.column_idx
            if tool_col == 1 and tool_col != current_col:
                self.window.controller.ui.tabs.enable_split_screen(True)  # enable split screen
                return
            return # do not open if already opened in tab
        if not self.auto_opened:
            self.auto_opened = True
            self.open()

    def scroll_to_bottom(self):
        """Scroll down"""
        self.get_widget_history().scroll_to_bottom()
        self.get_widget_output().scroll_to_bottom()

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

    def get_toolbar_icon(self) -> QWidget:
        """
        Get toolbar icon

        :return: QWidget
        """
        return self.window.ui.nodes['icon.interpreter']

    def toggle_icon(self, state: bool):
        """
        Toggle interpreter icon

        :param state: State
        """
        self.get_toolbar_icon().setVisible(state)

    def toggle_auto_clear(self, widget: ToolWidget):
        """
        Toggle auto clear

        :param widget: ToolWidget instance
        """
        self.auto_clear = widget.checkbox_auto_clear.isChecked()
        self.window.core.config.set("interpreter.auto_clear", self.auto_clear)
        self.signals.set_checkbox_auto_clear.emit(self.auto_clear)

    def toggle_ipython(self, widget: ToolWidget):
        """
        Toggle ipython

        :param widget: ToolWidget instance
        """
        self.ipython = widget.checkbox_ipython.isChecked()
        self.window.core.config.set("interpreter.ipython", self.ipython)
        self.signals.set_checkbox_ipython.emit(self.ipython)
        if self.ipython:
            self.signals.toggle_all_visible.emit(False)
        else:
            self.signals.toggle_all_visible.emit(True)

    def toggle_all(self, widget: ToolWidget):
        """
        Toggle execute all

        :param widget: ToolWidget instance
        """
        state = widget.checkbox_all.isChecked()
        self.window.core.config.set("interpreter.execute_all", state)
        self.signals.set_checkbox_all.emit(state)

    def get_current_output(self) -> str:
        """
        Get current output from interpreter

        :return: Output data
        """
        return self.get_output()

    def get_current_history(self) -> str:
        """
        Get code from history

        :return: Edit code
        """
        return self.get_history()

    def is_all(self) -> bool:
        """
        Check if execute all is enabled

        :return: True if execute all is enabled
        """
        return self.get_widget().checkbox_all.isChecked()

    def cursor_to_end(self):
        """Move cursor to end"""
        self.get_widget_history().scroll_to_bottom()

    def setup_menu(self) -> Dict[str, QAction]:
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

    def as_tab(self, tab: Tab) -> QWidget:
        """
        Spawn and return tab instance

        :param tab: Parent Tab instance
        :return: Tab widget instance
        """
        tool = Tool(window=self.window, tool=self)  # dialog
        tool.widget.set_is_dialog(False)
        layout = tool.widget.setup(all=False)
        widget = QWidget()
        widget.setLayout(layout)
        self.load_history()
        self.load_output()
        tool.set_tab(tab)
        return widget

    def setup_dialogs(self):
        """Setup dialogs (static)"""
        self.dialog = Tool(self.window, self)
        self.dialog.setup()
        self.dialog.set_is_dialog(True)

    def setup_theme(self):
        """Setup theme"""
        self.get_widget_output().value = self.window.core.config.get('font_size')

    def get_lang_mappings(self) -> Dict[str, Dict]:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {
            'menu.text': {
                'tools.interpreter': 'menu.tools.interpreter',
            }
        }