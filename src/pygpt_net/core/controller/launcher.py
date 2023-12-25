#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #

class Launcher:
    def __init__(self, window=None):
        """
        Launcher controller

        :param window: Window instance
        """
        self.window = window

    def show_api_monit(self):
        """Show empty API KEY monit"""
        self.window.ui.dialogs.open('info.start')

    def check_updates(self):
        """Check for updates"""
        self.window.app.updater.check(True)

    def setup(self):
        """Setup launcher"""
        # show welcome API KEY dialog (disable for langchain mode)
        if self.window.app.config.get('mode') != 'langchain' and \
                (self.window.app.config.get('api_key') is None or self.window.app.config.get('api_key') == ''):
            self.show_api_monit()

        self.window.app.gpt.init()
        self.window.app.image.init()
        self.window.controller.settings.update_font_size()

    def post_setup(self):
        """Post setup launcher"""
        # show welcome API KEY dialog (disable for langchain mode)
        if self.window.app.config.get('mode') != 'langchain' and \
                (self.window.app.config.get('api_key') is None or self.window.app.config.get('api_key') == ''):
            self.show_api_monit()

        # check for updates
        self.window.app.updater.check()
