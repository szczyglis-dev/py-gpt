#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from pygpt_net.core.auto_updater import AUTO_UPDATER_ENABLED
from pygpt_net.ui.widget.dialog.update import UpdateDialog


class Update:
    def __init__(self, window=None):
        """
        Updater dialog

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup updater dialog"""
        self.window.ui.dialog['update'] = UpdateDialog(self.window)
        if AUTO_UPDATER_ENABLED:
            from pygpt_net.ui.widget.dialog.update_progress import UpdateProgressDialog
            self.window.ui.dialog['update.progress'] = UpdateProgressDialog(self.window)
