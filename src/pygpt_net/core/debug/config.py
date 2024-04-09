#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.09 23:00:00                  #
# ================================================== #

import os

from PySide6.QtGui import QFontDatabase


class ConfigDebug:
    def __init__(self, window=None):
        """
        Config debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'config'

    def update(self):
        """Update debug window."""
        self.window.core.debug.begin(self.id)

        app_fonts = QFontDatabase.families()
        path = os.path.join(self.window.core.config.path, '', 'config.json')
        self.window.core.debug.add(self.id, 'Config File', str(path))
        self.window.core.debug.add(self.id, 'Current workdir', str(self.window.core.config.get_user_path()))
        self.window.core.debug.add(self.id, 'Base workdir', str(self.window.core.config.get_base_workdir()))
        self.window.core.debug.add(self.id, 'Workdir config', str(os.path.join(self.window.core.config.get_base_workdir(), "path.cfg")))
        self.window.core.debug.add(self.id, 'App dir', str(self.window.core.config.get_app_path()))
        self.window.core.debug.add(self.id, 'Profile [current]', str(self.window.core.config.profile.get_current()))
        self.window.core.debug.add(self.id, 'Profile [all]', str(self.window.core.config.profile.get_all()))
        self.window.core.debug.add(self.id, 'Registered fonts', str(app_fonts))
        self.window.core.debug.add(
            self.id, 'Sections',
            str(self.window.controller.settings.editor.get_sections())
        )
        self.window.core.debug.add(
            self.id, 'Options',
            str(self.window.controller.settings.editor.get_options())
        )

        # config data
        for key in self.window.core.config.all():
            self.window.core.debug.add(self.id, key, str(self.window.core.config.get(key)))

        self.window.core.debug.end(self.id)
