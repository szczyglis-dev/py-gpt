# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 00:00:00                  #
# ================================================== #

class Vision:
    def __init__(self, window=None):
        """
        UI vision update controller

        :param window: Window instance
        """
        self.window = window

    def has_vision(self):
        """
        Check if vision is available

        :return: True if vision is available
        """
        mode = self.window.core.config.get("mode")
        if mode == 'img':
            return False
        if mode == 'vision':
            return True
        if self.window.controller.plugins.is_type_enabled('vision'):
            return True
        if self.is_vision_model() and mode in ["chat"]:
            return True
        return False

    def update(self):
        """Update vision options"""
        if self.window.controller.painter.is_active():
            self.window.controller.camera.setup()
            self.window.controller.camera.show_camera()
        else:
            if self.has_vision():
                self.window.controller.camera.setup()
                self.window.controller.camera.show_camera()
                self.window.controller.chat.vision.show_inline()
            else:
                self.window.controller.camera.hide_camera()
                self.window.controller.chat.vision.hide_inline()

    def is_vision_model(self) -> bool:
        """
        Check if current model has vision capabilities

        :return: True if vision model
        """
        model_id = self.window.core.config.get("model")
        if model_id is not None:
            if self.window.core.models.has(model_id):
                model = self.window.core.models.get(model_id)
                if "vision" in model.mode:
                    return True
        return False

