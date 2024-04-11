#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.10 23:00:00                  #
# ================================================== #

import copy
import json
import os


class Editor:
    def __init__(self, window=None):
        """
        File editor core

        :param window: Window instance
        """
        self.window = window

    def restore(self, dialog_id: str):
        """
        Load defaults from file

        :param dialog_id: dialog id
        """
        file = self.window.ui.dialog[dialog_id].file
        self.load(dialog_id, file)
        self.window.ui.status("Reloaded file: {}".format(file))

    def clear(self, dialog_id: str):
        """
        Clear editor

        :param dialog_id: dialog id
        """
        self.window.ui.editor[dialog_id].clear()
        self.window.ui.dialog[dialog_id].file = None
        self.window.ui.dialog[dialog_id].base_content = ""
        self.window.ui.dialog[dialog_id].reset_file_title()
        self.window.ui.editor[dialog_id].on_update()
        self.window.ui.status("")

    def destroy(self, dialog_id: str):
        """
        On destroy editor

        :param dialog_id: dialog id
        """
        self.window.ui.editor[dialog_id].on_destroy()

    def is_changed(self, dialog_id: str) -> bool:
        """
        Check if content was changed

        :param dialog_id: dialog id
        :return: True if changed
        """
        return self.window.ui.dialog[dialog_id].is_changed()

    def load(self, dialog_id: str, file: str = None):
        """
        Load file to editor

        :param dialog_id: dialog id
        :param file: file name
        """
        # load file
        self.window.ui.paths[dialog_id].setText(file)
        self.window.ui.dialog[dialog_id].file = file
        if not os.path.exists(file):
            self.window.ui.status("File not found: {}".format(file))
            return
        try:
            with open(file, 'r', encoding="utf-8") as f:
                txt = f.read()
                self.window.ui.editor[dialog_id].setPlainText(txt)
                self.window.ui.dialog[dialog_id].base_content = copy.deepcopy(txt)
                self.window.ui.dialog[dialog_id].update_file_title()
                self.window.ui.editor[dialog_id].on_update()
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.status("Error loading file: {}".format(e))

    def save(self, dialog_id: str, path: str = None):
        """
        Save file to disk

        :param dialog_id: dialog id
        :param path: file path
        """
        file = self.window.ui.dialog[dialog_id].file
        if path is None:
            path = file
        else:
            self.window.ui.dialog[dialog_id].file = path  # update file path

        data = self.window.ui.editor[dialog_id].toPlainText()

        # check if this is a valid JSON
        if path.endswith('.json'):
            try:
                json.loads(data)
            except Exception as e:
                self.window.ui.status("WARNING: This is not a valid JSON: {}".format(e))
                self.window.ui.dialogs.alert("WARNING: This is not a valid JSON: {}".format(e))

        # save changes
        try:
            with open(path, 'w', encoding="utf-8") as f:
                f.write(data)
            self.window.ui.dialog[dialog_id].base_content = copy.deepcopy(data)
            self.window.ui.dialog[dialog_id].update_file_title(force=True)
            self.window.ui.status("Saved file: {}".format(os.path.basename(path)))
            self.window.controller.files.update_explorer()
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.status("Error saving file: {}".format(path))
