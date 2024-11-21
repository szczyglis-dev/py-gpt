#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 03:00:00                  #
# ================================================== #

class KernelDebug:
    def __init__(self, window=None):
        """
        Kernel debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'kernel'

    def update(self):
        """Update debug window."""
        self.window.core.debug.begin(self.id)
        self.window.core.debug.add(self.id, 'Busy:', str(self.window.controller.kernel.busy))
        self.window.core.debug.add(self.id, 'Halt:', str(self.window.controller.kernel.halt))
        self.window.core.debug.add(self.id, 'Status:', str(self.window.controller.kernel.status))
        self.window.core.debug.add(self.id, 'State:', str(self.window.controller.kernel.state))
        self.window.core.debug.add(self.id, 'Stack:', str(self.window.controller.kernel.last_stack))
        self.window.core.debug.end(self.id)
