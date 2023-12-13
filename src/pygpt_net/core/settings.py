#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.13 14:00:00                  #
# ================================================== #

import os

from .utils import trans


class Settings:
    def __init__(self, window=None):
        """
        Settings handler

        :param window: main window
        """
        self.window = window

        # prepare cfg ids
        self.ids = ['settings', 'editor']
        self.active = {}

        # prepare active
        for id in self.ids:
            self.active[id] = False

    def load_user_settings(self):
        """Loads user config (from user home dir)"""
        # replace config with user base config
        self.window.config.load_config()

        # re-init settings
        self.window.controller.settings.init('settings')
        self.window.ui.dialogs.alert(trans('dialog.settings.defaults.user.result'))

    def load_app_settings(self):
        """Loads base app config (from app root dir)"""
        # persist important values
        persist_options = [
            'api_key',
            'organization_key',
        ]
        persist_values = {}
        for option in persist_options:
            if option in self.window.config.data:
                persist_values[option] = self.window.config.data[option]

        # save current config backup
        self.window.config.save('config.backup.json')

        # replace config with app base config
        self.window.config.load_base_config()

        # restore persisted values
        for option in persist_options:
            if option in persist_values:
                self.window.config.data[option] = persist_values[option]

        # re-init settings
        self.window.controller.settings.init('settings')
        self.window.ui.dialogs.alert(trans('dialog.settings.defaults.app.result'))

    def load_default_editor(self):
        """Loads defaults from file"""
        file = self.window.dialog['config.editor'].file
        self.load_editor(file)
        self.window.set_status("Loaded defaults from file: {}".format(file))

    def save_editor(self):
        """Saves file to disk"""
        file = self.window.dialog['config.editor'].file
        path = os.path.join(self.window.config.path, file)
        try:
            with open(path, 'w', encoding="utf-8") as f:
                f.write(self.window.editor['config'].toPlainText())
                f.close()
            self.window.set_status("Saved file: {}".format(path))
            self.window.ui.dialogs.alert("Saved file: {}".format(path))
        except Exception as e:
            self.window.set_status("Error saving file: {}".format(path))
            print(e)

    def load_editor(self, file=None):
        """
        Loads file to editor

        :param id: file id
        """
        # load file
        path = os.path.join(self.window.config.path, file)
        self.window.path_label['config'].setText(path)
        self.window.dialog['config.editor'].file = file
        try:
            with open(path, 'r', encoding="utf-8") as f:
                txt = f.read()
                f.close()
                self.window.editor['config'].setPlainText(txt)
        except Exception as e:
            print(e)
