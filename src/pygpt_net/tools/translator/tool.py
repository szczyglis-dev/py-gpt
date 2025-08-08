#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.08 05:00:00                  #
# ================================================== #
import json
import os
from typing import Dict

from PySide6.QtCore import QTimer, Slot, QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QFileDialog, QWidget, QApplication

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.text.utils import output_clean_html, output_html2text
from pygpt_net.tools.base import BaseTool, TabWidget
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.events import KernelEvent
from pygpt_net.core.worker import Worker
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans
from pygpt_net.item.model import ModelItem


class WorkerSignals(QObject):
    updated = Signal(str, str)  # ID, text

from .ui.dialogs import Tool
from .ui.widgets import ToolSignals


class Translator(BaseTool):
    def __init__(self, *args, **kwargs):
        """
        Translator

        :param window: Window instance
        """
        super(Translator, self).__init__(*args, **kwargs)
        self.id = "translator"
        self.dialog_id = "translator"
        self.has_tab = False
        self.tab_title = "menu.tools.translator"
        self.tab_icon = ":/icons/text.svg"
        self.opened = False
        self.is_edit = False
        self.auto_clear = True
        self.dialog = None
        self.is_edit = False
        self.auto_opened = False
        self.config_file = ".translator.json"
        self.signals = ToolSignals()

    def setup(self):
        """Setup"""
        self.signals.save_config.connect(self.save_config)
        self.signals.translate.connect(self.translate)
        self.update()

    def on_reload(self):
        """On app profile reload"""
        self.setup()

    def update(self):
        """Update menu"""
        self.update_menu()

    def update_menu(self):
        """Update menu"""
        pass

    def append_content(self, id: str, content: str):
        """
        Append content to the specified ID

        :param id: ID to append to
        :param content: Content to append
        """
        self.signals.append.emit(id, content)

    def replace_content(self, id: str, content: str):
        """
        Replace content in the specified ID

        :param id: ID to replace in
        :param content: Content to replace with
        """
        self.signals.replace.emit(id, content)

    @Slot(str, str, str, str, str)
    def translate(
            self,
            id: str,
            model: str,
            text: str,
            source_lang: str,
            target_lang: str
    ):
        """
        Translate text

        :param id: ID of the content to translate
        :param model: Translation model (e.g., 'google', 'deepl')
        :param text: Text to translate
        :param source_lang: Source language code
        :param target_lang: Target language code
        """
        from_lang = self.window.core.text.get_language_name(source_lang)
        to_lang = self.window.core.text.get_language_name(target_lang)
        self.set_status(trans("status.sending"))

        # quick call
        model_data = self.window.core.models.get(model)
        if not model_data:
            self.set_status("Translation model '{}' not found.".format(model))
            return

        if id == "left":
            self.clear_right(force=True)
        elif id == "right":
            self.clear_left(force=True)

        worker = Worker(self.translate_execute)
        worker.signals = WorkerSignals()
        worker.signals.updated.connect(self.handle_update)
        worker.kwargs['id'] = id
        worker.kwargs['model'] = model_data
        worker.kwargs['text'] = text
        worker.kwargs['from_lang'] = from_lang
        worker.kwargs['to_lang'] = to_lang
        worker.kwargs['window'] = self.window
        worker.kwargs['updated_signal'] = worker.signals.updated
        self.window.threadpool.start(worker)

    def set_status(self, status: str):
        """
        Set status message

        :param status: Status message
        """
        event = KernelEvent(KernelEvent.STATUS, {'status': status})
        self.window.dispatch(event)
        self.signals.set_status.emit(status)
        QApplication.processEvents()

    def translate_execute(
            self,
            window,
            id: str,
            model: ModelItem,
            from_lang: str,
            to_lang: str,
            text: str,
            updated_signal: Signal,
    ):
        """
        Execute translation

        :param window: Main window instance
        :param id: ID of the column
        :param model: Translation model
        :param from_lang: Source language code
        :param to_lang: Target language code
        :param text: Text to translate
        :param updated_signal: Signal to emit on update
        """
        if from_lang == '--- AUTO DETECT ---':
            sys_prompt = """
            Translate provided text to {to_lang}. 
            In your response, return only the raw, translated text, without any comments or other insertions. 
            """.format(to_lang=to_lang)
        else:
            sys_prompt = """
            Translate provided text from {from_lang} to {to_lang}. 
            In your response, return only the raw, translated text, without any comments or other insertions. 
            """.format(from_lang=from_lang, to_lang=to_lang)

        ctx = CtxItem()
        ctx.input = text
        bridge_context = BridgeContext(
            ctx=CtxItem(),
            prompt=text,
            system_prompt=sys_prompt,
            model=model,
            force=True,  # even if kernel stopped
        )
        event = KernelEvent(KernelEvent.FORCE_CALL, {
            'context': bridge_context,
            'extra': {"disable_tools": True},
            'response': None,
        })
        window.dispatch(event)
        response = event.data.get('response')
        updated_signal.emit(id, response)

    @Slot(str, str)
    def handle_update(
            self,
            id: str,
            text: str,
    ):
        """
        Handle update signal (make update)

        :param id: ID of the content to update
        :param text: Text to update with
        """
        if text:
            self.set_status("Translation completed successfully.")
        else:
            self.set_status("Translation failed, no response received.")
            return

        if id == "left":
            self.replace_content("right", text)
        elif id == "right":
            self.replace_content("left", text)

    def get_current_path(self) -> str:
        """
        Get current output path

        :return: Output path
        """
        return os.path.join(self.window.core.config.get_user_dir("data"), self.config_file)

    def get_dialog_id(self) -> str:
        """
        Get dialog ID

        :return: Dialog ID
        """
        return self.dialog_id

    def open_file(self):
        """Open file dialog"""
        last_dir = self.window.core.config.get_last_used_dir()
        dialog = QFileDialog(self.window)
        dialog.setDirectory(last_dir)
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        if dialog.exec():
            path = dialog.selectedFiles()[0]
            try:
                content, _ = self.window.core.idx.indexing.read_text_content(path)
                self.replace_content("left", content)
            except Exception as e:
                self.window.core.logger.error(f"Error reading file {path}: {e}")

    def set_output(self, output: str):
        """
        Set output HTML

        :param output: Output HTML code
        """
        path = self.get_current_path()
        with open(path, "w", encoding="utf-8") as f:
            f.write(output)
        if os.path.exists(path):
            self.signals.reload.emit(path)
        self.signals.update.emit(output)

    def reload_output(self):
        """Reload output data"""
        self.load_config()
        self.update()

    def get_output(self) -> str:
        """
        Get current HTML output

        :return: Output data
        """
        path = self.get_current_path()
        data = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        return data

    def load_config(self):
        """Load config data from file"""
        path = self.get_current_path()
        data = ""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        if data:
            decoded = json.loads(data)
            if isinstance(decoded, dict):
                self.signals.load_config.emit(decoded)

    @Slot(dict)
    def save_config(self, config: Dict):
        """
        Save config data to file

        :param config: Configuration dictionary
        """
        path = self.get_current_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    def clear_output(self):
        """Clear output"""
        self.clear_left(force=True)
        self.clear_right(force=True)

    def clear_left(self, force: bool = False):
        """
        Clear left column

        :param force: Force clear
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='translator.clear.left',
                id=0,
                msg=trans("translator.clear.left.confirm"),
            )
            return
        self.replace_content("left", "")

    def clear_right(self, force: bool = False):
        """
        Clear right column

        :param force: Force clear
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='translator.clear.right',
                id=0,
                msg=trans("translator.clear.right.confirm"),
            )
            return
        self.replace_content("right", "")

    def clear(self, force: bool = False):
        """
        Clear current window

        :param force: Force clear
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='translator.clear',
                id=0,
                msg=trans("translator.clear.confirm"),
            )
            return
        self.clear_output()

    def clear_all(self):
        """Clear input and output"""
        self.clear_output()

    def open(self):
        """Open HTML canvas dialog"""
        if not self.opened:
            self.opened = True
            self.auto_opened = False
            self.load_config()
            self.window.ui.dialogs.open(self.dialog_id, width=800, height=600)
            self.update()

    def close(self):
        """Close HTML canvas dialog"""
        self.opened = False
        self.window.ui.dialogs.close(self.dialog_id)
        self.update()

    def toggle(self):
        """Toggle HTML canvas dialog open/close"""
        if self.opened:
            self.close()
        else:
            self.open()

    def show_hide(self, show: bool = True):
        """
        Show/hide HTML canvas window

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
        return self.window.ui.nodes['icon.translator']

    def toggle_icon(self, state: bool):
        """
        Toggle canvas icon

        :param state: State
        """
        self.get_toolbar_icon().setVisible(state)

    def get_current_output(self) -> str:
        """
        Get current output from canvas

        :return: Output data
        """
        return self.get_output()

    @Slot(str, str)
    def handle_save_as(self, text: str, type: str = 'txt'):
        """
        Handle save as signal

        :param text: Data to save
        :param type: File type
        """
        if type == 'html':
            text = output_clean_html(text)
        else:
            text = output_html2text(text)
        # fix: QTimer required here to prevent crash if signal emitted from WebEngine window
        QTimer.singleShot(0, lambda: self.window.controller.chat.common.save_text(text, type))

    def setup_menu(self) -> Dict[str, QAction]:
        """
        Setup main menu

        :return dict with menu actions
        """
        id = "translator"
        actions = {}
        actions[id] = QAction(
            QIcon(":/icons/text.svg"),
            trans("menu.tools.translator"),
            self.window,
            checkable=False,
        )
        actions[id].triggered.connect(
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
        tool_widget = tool.as_tab()  # ToolWidget
        widget = TabWidget()
        widget.from_tool(tool_widget)
        widget.setup()
        self.load_config()
        tool.set_tab(tab)
        return widget

    def setup_dialogs(self):
        """Setup dialogs (static)"""
        self.dialog = Tool(window=self.window, tool=self)
        self.dialog.setup()

    def setup_theme(self):
        """Setup theme"""
        pass

    def get_lang_mappings(self) -> Dict[str, Dict]:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {
            'menu.text': {
                'tools.translator': 'menu.tools.translator',
            }
        }