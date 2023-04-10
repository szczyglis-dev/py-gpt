#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

from core.updater import Updater


class Launcher:
    def __init__(self, window=None):
        """
        Launcher controller

        :param window: main window object
        """
        self.window = window
        self.updater = Updater(window)

    def show_api_monit(self):
        """Shows empty API KEY monit"""
        self.window.ui.dialogs.open('info.start')

    def setup(self):
        """Setups launcher"""
        self.updater.check()

        # show welcome API KEY dialog
        if self.window.config.data['api_key'] is None or self.window.config.data['api_key'] == '':
            self.show_api_monit()

        self.window.gpt.init()
        self.window.images.init()
        self.window.controller.settings.update_font_size()
