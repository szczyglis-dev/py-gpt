#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.14 18:00:00                  #
# ================================================== #

import hashlib
import os

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QFileDialog

from pygpt_net.tools.base import BaseTool
from pygpt_net.tools.text_editor.ui.dialogs import DialogSpawner
from pygpt_net.utils import trans


class TextEditor(BaseTool):
    def __init__(self, *args, **kwargs):
        """
        Text editor

        :param window: Window instance
        """
        super(TextEditor, self).__init__(*args, **kwargs)
        self.id = "editor"
        self.width = 800
        self.height = 500
        self.instance_id = 0
        self.spawner = None

    def setup(self):
        """Setup tool"""
        self.spawner = DialogSpawner(self.window)

    def prepare_id(self, file: str):
        """
        Prepare unique id for file

        :param file: file name
        :return: unique id
        """
        return 'file_editor_' + hashlib.md5(file.encode('utf-8')).hexdigest()

    def open_file(self, id: str, auto_close: bool = True, force: bool = False, save: bool = False):
        """
        Open text file dialog

        :param id: editor id
        :param auto_close: auto close current editor
        :param force: force open new instance
        :param save: save current file
        """
        if not force and self.window.core.filesystem.editor.is_changed(id) and auto_close:
            self.window.ui.dialogs.confirm(
                type='editor.changed.open',
                id=id,
                msg=trans("changed.confirm"),
            )
            return

        if save:
            self.save(id)

        path, _ = QFileDialog.getOpenFileName(
            self.window,
            trans("action.open"))
        if path:
            self.open(path, id, auto_close)

    def clear(self, id: str = None, force: bool = False, save: bool = False):
        """
        Clear current instance

        :param id: editor id
        :param force: force open new instance
        :param save: save current file
        """
        if not force and self.window.core.filesystem.editor.is_changed(id):
            self.window.ui.dialogs.confirm(
                type='editor.changed.clear',
                id=id,
                msg=trans("changed.confirm"),
            )
            return

        if save:
            id = self.save(id)
            self.close(id)

        self.window.core.filesystem.editor.clear(id)

    def new(self):
        """Open new instance"""
        self.open()

    def open(
            self,
            file: str = None,
            current_id: str = None,
            auto_close: bool = True,
            force: bool = False):
        """
        Open/toggle file editor

        :param file: File to load
        :param current_id: editor id
        :param auto_close: auto close current editor
        :param force: force open new instance
        """
        # pre-check if file can be opened as text
        if file:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    f.read()
            except Exception as e:
                self.window.ui.dialogs.alert(e)
                self.window.ui.status("Error opening text file: {}".format(e))
                return

            # close current editor if different file
            id = self.prepare_id(file)
            if current_id and auto_close:
                if id != current_id:
                    self.close(current_id)
        else:
            # new instance id
            id = 'file_tmp_editor_' + str(self.instance_id)
            self.instance_id += 1

        self.window.ui.dialogs.open_instance(
            id,
            width=self.width,
            height=self.height,
        )

        # set file
        if file:
            title = os.path.basename(file)
            file_size = self.window.core.filesystem.sizeof_fmt(os.path.getsize(file))
            title += " - {}".format(file_size)
            self.window.ui.dialog[id].file = file
            self.window.core.filesystem.editor.load(id, file)  # load file to editor
            self.window.ui.dialog[id].setWindowTitle(title)  # set window title
            self.window.ui.editor[id].setFocus()  # set focus
            if not force:
                self.window.ui.status("Loaded file: {}".format(os.path.basename(file)))  # set status
        else:
            self.window.core.filesystem.editor.clear(id)  # clear editor if no file

    def close(self, id: str, save: bool = False):
        """
        Close file editor

        :param id: editor id
        :param save: save file before close
        """
        if save:
            id = self.save(id)
        self.window.ui.dialog[id].accept_close = True
        self.window.core.filesystem.editor.destroy(id)  # unregister from memory
        self.window.ui.dialogs.close(id)

    def save(self, id: str) -> str:
        """
        Save content to current file

        :param id: editor id
        :return: new editor id
        """
        file = self.window.ui.dialog[id].file
        if file:
            self.window.core.filesystem.editor.save(id)
        else:
            id = self.save_as_file(id)
        return id

    def restore(self, id: str, force: bool = False, save: bool = False):
        """
        Restore file content

        :param id: editor id
        :param force: force restore
        :param save: save file before restore
        """
        if not force and self.window.core.filesystem.editor.is_changed(id):
            self.window.ui.dialogs.confirm(
                type='editor.changed.restore',
                id=id,
                msg=trans("changed.confirm"),
            )
            return

        if save:
            self.save(id)

        file = self.window.ui.dialog[id].file
        if file:
            self.window.core.filesystem.editor.restore(id)
        else:
            self.window.ui.dialogs.alert("No file to restore")

    def save_as_file(self, id: str) -> str:
        """
        Save content to file

        :param id: editor id
        :return: new editor id
        """
        file_name = ""
        current = self.window.ui.dialog[id].file
        if current:
            file_name = os.path.basename(current)
        path, _ = QFileDialog.getSaveFileName(
            self.window,
            trans("action.save_as"),
            file_name,
        )
        if path:
            self.window.core.filesystem.editor.save(id, path)
        return id

    def setup_menu(self) -> dict:
        """
        Setup main menu

        :return dict with menu actions
        """
        actions = {}
        actions["text.editor"] = QAction(
            QIcon(":/icons/edit.svg"),
            trans("menu.tools.text.editor"),
            self.window,
            checkable=False,
        )
        actions["text.editor"].triggered.connect(
            lambda: self.open()
        )
        return actions

    def get_instance(self, type_id: str, dialog_id: str = None):
        """
        Spawn and return dialog instance

        :param type_id: dialog instance type ID
        :param dialog_id: dialog instance ID
        :return dialog instance
        """
        if type_id == "text_editor":
            return self.spawner.setup(dialog_id)

    def get_lang_mappings(self) -> dict:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {
            'menu.text': {
                'tools.text.editor': 'menu.tools.text.editor',
            }
        }
