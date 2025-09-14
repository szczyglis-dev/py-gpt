#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.14 20:00:00                  #
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
        debug = self.window.core.debug
        kernel_controller = self.window.controller.kernel

        debug.begin(self.id)
        debug.add(self.id, 'Busy:', str(kernel_controller.busy))
        debug.add(self.id, 'Halt:', str(kernel_controller.halt))
        debug.add(self.id, 'Status:', str(kernel_controller.status))
        debug.add(self.id, 'State:', str(kernel_controller.state))
        debug.add(self.id, 'Stack:', str(kernel_controller.last_stack))
        debug.end(self.id)