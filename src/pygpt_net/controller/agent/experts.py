#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.01 17:00:00                  #
# ================================================== #


class Experts:
    def __init__(self, window=None):
        """
        Experts controller

        :param window: Window instance
        """
        self.window = window
        self.is_stop = False

    def stop(self):
        """
        Stop experts
        """
        self.is_stop = True

    def stopped(self) -> bool:
        """
        Check if experts are stopped

        :return: True if experts are stopped
        """
        return self.is_stop

    def unlock(self):
        """
        Unlock experts
        """
        self.is_stop = False

    def enabled(self) -> bool:
        """
        Check if experts are enabled

        :return: True if experts are enabled
        """
        modes = ["agent", "expert"]
        mode = self.window.core.config.get('mode')
        if mode in modes or self.window.controller.plugins.is_type_enabled("experts"):
            return True
        return False