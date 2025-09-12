#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.11 00:00:00                  #
# ================================================== #

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_EXPERT,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
)
class Launcher:
    def __init__(self, window=None):
        """
        Launcher controller

        :param window: Window instance
        """
        self.window = window

    def post_setup(self):
        """Post setup launcher"""
        # check for updates
        if self.window.core.config.get('updater.check.launch'):
            self.window.core.updater.run_check(force=True)  # async

    def show_api_monit(self):
        """Show empty API KEY monit"""
        self.window.ui.dialogs.open('info.start')

    def check_updates(self):
        """Check for updates"""
        self.window.core.updater.check(True)

    def toggle_update_check(self, value):
        """Toggle update check on startup"""
        self.window.core.config.set('updater.check.launch', value)
        self.window.core.config.save()
