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

import hashlib
import os

from PySide6.QtWidgets import QFileDialog

from pygpt_net.utils import trans


class TextEditor:
    def __init__(self, window=None):
        """
        Text editor controller

        :param window: Window instance
        """
        self.window = window
        self.width = 800
        self.height = 500

    def setup(self):
        """Set up editor"""
        pass

    def update(self):
        """Update"""
        pass

    def on_exit(self):
        """On exit"""
        pass

    def prepare_id(self, file: str):
        """
        Prepare unique id for file

        :param file: file name
        :return: unique id
        """
        return 'file_editor_' + hashlib.md5(file.encode('utf-8')).hexdigest()

    def open_file(self, id: str, auto_close: bool = True):
        """
        Open text file dialog

        :param id: editor id
        :param auto_close: auto close current editor
        """
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            trans("action.open"))
        if path:
            self.open(path, id, auto_close)

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
            # empty window (tmp)
            id = 'file_editor_'

        self.window.ui.dialogs.open_instance(
            id,
            width=self.width,
            height=self.height,
        )

        # set file
        if file:
            self.window.ui.dialog[id].file = file
            self.window.core.filesystem.editor.load(id, file)  # load file to editor
            self.window.ui.dialog[id].setWindowTitle(os.path.basename(file))  # set window title
            if not force:
                self.window.ui.status("Loaded file: {}".format(file))  # set status

        # update menu
        self.update()

    def close(self, id: str):
        """
        Close file editor

        :param id: editor id
        """
        self.window.ui.dialogs.close(id)

    def save(self, id: str):
        """
        Save content to current file

        :param id: editor id
        """
        file = self.window.ui.dialog[id].file
        if file:
            self.window.core.filesystem.editor.save(id)
        else:
            self.save_as_file(id)

    def restore(self, id: str):
        """
        Restore file content

        :param id: editor id
        """
        file = self.window.ui.dialog[id].file
        if file:
            self.window.core.filesystem.editor.restore(id)
        else:
            self.window.ui.dialogs.alert("No file to restore")

    def save_as_file(self, id: str):
        """
        Save content to file

        :param id: editor id
        """
        path, _ = QFileDialog.getSaveFileName(
            self.window,
            "Save as"
        )
        if path:
            self.window.core.filesystem.editor.save(id, path)
            # create new instance if file was changed
            new_id = self.prepare_id(path)
            if new_id != id:
                self.window.ui.dialogs.close(id)
                self.open(path, force=True)
