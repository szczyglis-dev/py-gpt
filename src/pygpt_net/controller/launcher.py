#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

class Launcher:
    def __init__(self, window=None):
        """
        Launcher controller

        :param window: Window instance
        """
        self.window = window

    def post_setup(self):
        """Post setup launcher"""
        # show welcome API KEY dialog (disable for langchain mode)
        if self.window.core.config.get('mode') != 'langchain' and \
                (self.window.core.config.get('api_key') is None or self.window.core.config.get('api_key') == ''):
            self.show_api_monit()

        # check for updates
        if self.window.core.config.get('updater.check.launch'):
            self.window.core.updater.check()

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
