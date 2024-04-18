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

from pygpt_net.ui.widget.dialog.base import BaseDialog

class BaseTool:
    def __init__(self, *args, **kwargs):
        """
        Base Tool

        :param window: Window instance
        :param args: arguments
        :param kwargs: keyword arguments
        """
        self.window = None
        self.id = ""

    def setup(self):
        """Setup tool"""
        pass

    def post_setup(self):
        """Post-setup (window), after plugins are loaded"""
        pass

    def on_update(self):
        """On app main loop update"""
        pass

    def on_post_update(self):
        """On app main loop update"""
        pass

    def on_exit(self):
        """On app exit"""
        pass

    def on_reload(self):
        """On app profile reload"""
        pass

    def attach(self, window):
        """
        Attach window to plugin

        :param window: Window instance
        """
        self.window = window

    def setup_menu(self) -> list:
        """
        Setup main menu

        :return list with menu actions
        """
        return []

    def setup_dialogs(self):
        """Setup dialogs (static)"""
        pass

    def setup_theme(self):
        """Setup theme"""
        pass

    def get_instance(self, id: str, dialog_id: str = None) -> BaseDialog or None:
        """
        Spawn and return dialog instance

        :param id: dialog instance ID
        :param dialog_id: dialog instance ID
        """
        return None

    def get_lang_mappings(self) -> dict:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {}