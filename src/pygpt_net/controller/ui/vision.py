# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.23 19:00:00                  #
# ================================================== #

class Vision:
    def __init__(self, window=None):
        """
        UI vision update controller

        :param window: Window instance
        """
        self.window = window

    def update(self):
        """Update vision options"""
        mode = self.window.core.config.data['mode']
        if self.window.controller.painter.is_active():
            self.window.controller.camera.setup()
            self.window.controller.camera.show_camera()
        else:
            # plugin: vision
            if self.window.controller.plugins.is_type_enabled('vision'):
                if mode == 'vision' or mode in self.window.controller.chat.vision.allowed_modes:
                    self.window.controller.camera.setup()
                    self.window.controller.camera.show_camera()
                    if mode != 'vision':
                        self.window.controller.chat.vision.show_inline()
                else:
                    self.window.controller.camera.hide_camera()
                    self.window.controller.chat.vision.hide_inline()
            # no-plugin
            else:
                if mode != 'vision':
                    self.window.controller.camera.hide_camera()
                    self.window.controller.chat.vision.hide_inline()
                else:
                    self.window.controller.camera.setup()
                    self.window.controller.camera.show_camera()
