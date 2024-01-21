#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.21 10:00:00                  #
# ================================================== #


class Common:
    def __init__(self, window=None):
        """
        Idx common controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Set up UI"""
        # raw query
        if self.window.core.config.get('llama.idx.raw'):
            self.window.ui.config['global']['llama.idx.raw'].setChecked(True)
        else:
            self.window.ui.config['global']['llama.idx.raw'].setChecked(False)

    def enable_raw(self):
        """Enable raw query"""
        self.window.core.config.set('llama.idx.raw', True)
        self.window.core.config.save()

    def disable_raw(self):
        """Disable raw query"""
        self.window.core.config.set('llama.idx.raw', False)
        self.window.core.config.save()

    def toggle_raw(self, state: bool):
        """
        Toggle raw query

        :param state: state of checkbox
        """
        if not state:
            self.disable_raw()
        else:
            self.enable_raw()
