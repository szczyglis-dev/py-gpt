#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 21:00:00                  #
# ================================================== #

class Model:
    def __init__(self, window=None):
        """
        Model controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup"""
        pass

    def select(self, idx):
        """
        Select model

        :param idx: value of the list (row idx)
        """
        # check if model change is not locked
        if self.change_locked():
            return
        mode = self.window.core.config.get('mode')
        self.set_by_idx(mode, idx)

        # update all layout
        self.window.controller.ui.update()

    def set_by_idx(self, mode, idx):
        """
        Set model by index

        :param mode: mode name
        :param idx: model index
        """
        model = self.window.core.models.get_by_idx(idx, mode)
        self.window.core.config.set('model', model)
        self.window.core.config.data['current_model'][mode] = model

    def set_model(self, mode, model):
        """
        Set model

        :param mode: mode name
        :param model: model name
        """
        self.window.core.config.set('model', model)
        self.window.core.config.data['current_model'][mode] = model

    def select_current(self):
        """Select model by current"""
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')
        items = self.window.core.models.get_by_mode(mode)
        if model in items:
            idx = list(items.keys()).index(model)
            current = self.window.ui.models['prompt.model'].index(idx, 0)
            self.window.ui.nodes['prompt.model'].setCurrentIndex(current)

    def select_default(self):
        """Set default model"""
        model = self.window.core.config.get('model')
        if model is None or model == "":
            mode = self.window.core.config.get('mode')

            # set previous selected model
            current_models = self.window.core.config.get('current_model')
            if mode in current_models and \
                    current_models[mode] is not None and \
                    current_models[mode] != "" and \
                    current_models[mode] in self.window.core.models.get_by_mode(mode):
                self.window.core.config.set('model', current_models[mode])
            else:
                # or set default model
                self.window.core.config.set('model', self.window.core.models.get_default(mode))

    def update_list(self):
        """Update models list"""
        mode = self.window.core.config.get('mode')
        items = self.window.core.models.get_by_mode(mode)
        self.window.ui.toolbox.model.update(items)

    def update(self):
        """Update models"""
        self.select_default()
        self.update_list()
        self.select_current()

    def change_locked(self):
        """
        Check if model change is locked

        :return: true if locked
        :rtype: bool
        """
        if self.window.controller.input.generating:
            return True
        return False
