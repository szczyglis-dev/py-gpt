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
        debug = self.window.core.debug
        config = self.window.core.config
        profile = config.profile
        settings_editor = self.window.controller.settings.editor
        app_fonts = QFontDatabase.families()

        debug.begin(self.id)

        path = os.path.join(config.path, '', 'config.json')
        debug.add(self.id, 'Config File', str(path))
        debug.add(self.id, 'Current workdir', str(config.get_user_path()))
        debug.add(self.id, 'Base workdir', str(config.get_base_workdir()))
        debug.add(self.id, 'Workdir config', str(os.path.join(config.get_base_workdir(), "path.cfg")))
        debug.add(self.id, 'App dir', str(config.get_app_path()))
        debug.add(self.id, 'Profile [current]', str(profile.get_current()))
        debug.add(self.id, 'Profile [all]', str(profile.get_all()))
        debug.add(self.id, 'Registered fonts', str(app_fonts))
        debug.add(self.id, 'Sections', str(settings_editor.get_sections()))
        debug.add(self.id, 'Options', str(settings_editor.get_options()))

        # config data
        for key in config.all():
            debug.add(self.id, key, str(config.get(key)))

        debug.end(self.id)
