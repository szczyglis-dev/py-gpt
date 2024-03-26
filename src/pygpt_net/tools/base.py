#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.25 10:00:00                  #
# ================================================== #

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