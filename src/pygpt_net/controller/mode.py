#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.30 21:00:00                  #
# ================================================== #

from pygpt_net.utils import trans


class Mode:
    def __init__(self, window=None):
        """
        Mode controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup"""
        pass

    def select(self, idx):
        """
        Select mode

        :param idx: value of the list (row idx)
        """
        # check if mode change is not locked
        if self.change_locked():
            return
        mode = self.window.core.modes.get_by_idx(idx)
        self.set(mode)

    def set(self, mode):
        """
        Set mode

        :param mode: mode name
        """
        # if ctx loaded with assistant then switch to this assistant
        if mode == "assistant":
            if self.window.core.ctx.current is not None \
                    and self.window.core.ctx.assistant is not None:
                self.window.controller.assistant.select_by_id(self.window.core.ctx.assistant)

        self.window.core.config.set('mode', mode)
        self.window.core.config.set('model', "")
        self.window.core.config.set('preset', "")
        self.window.controller.attachment.update()
        self.window.controller.ctx.update_ctx()

        # update all layout
        self.window.controller.ui.update()

        self.window.ui.status(trans('status.started'))

        # vision camera
        if mode == 'vision':
            self.window.controller.camera.setup()
            self.window.controller.camera.show_camera()
        else:
            self.window.controller.camera.hide_camera()

        # assistant
        if mode == "assistant":
            # update ctx label
            self.window.controller.ctx.update_label_by_current()

    def select_current(self):
        """Select mode by current"""
        mode = self.window.core.config.get('mode')
        items = self.window.core.modes.get_all()
        idx = list(items.keys()).index(mode)
        current = self.window.ui.models['prompt.mode'].index(idx, 0)
        self.window.ui.nodes['prompt.mode'].setCurrentIndex(current)

    def default_all(self):
        """Set default mode, model and preset"""
        self.select_default()
        self.window.controller.model.select_default()
        self.window.controller.presets.select_default()
        self.window.controller.assistant.select_default()

    def select_default(self):
        """Set default mode"""
        mode = self.window.core.config.get('mode')
        if mode is None or mode == "":
            self.window.core.config.set('mode', self.window.core.modes.get_default())

    def update_list(self):
        """Update modes list"""
        items = self.window.core.modes.get_all()
        self.window.ui.toolbox.mode.update(items)

    def update_temperature(self, temperature=None):
        """
        Update current temperature

        :param temperature: temperature (float)
        """
        if temperature is None:
            if self.window.core.config.get('preset') is None or self.window.core.config.get('preset') == "":
                temperature = 1.0  # default temperature
            else:
                id = self.window.core.config.get('preset')
                if id in self.window.core.presets.items:
                    temperature = float(self.window.core.presets.items[id].temperature)
        self.window.controller.settings.editor.apply("current_temperature", temperature)

    def update_mode(self):
        """Update mode"""
        self.select_default()
        self.update_list()
        self.select_current()

    def reset_current(self):
        """Reset current data"""
        self.window.core.config.set('prompt', None)
        self.window.core.config.set('ai_name', None)
        self.window.core.config.set('user_name', None)

    def change_locked(self):
        """
        Check if mode change is locked

        :return: true if locked
        :rtype: bool
        """
        if self.window.controller.chat.input.generating:
            return True
        return False
