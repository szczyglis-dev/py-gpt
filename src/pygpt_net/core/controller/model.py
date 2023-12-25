#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #

from pygpt_net.core.utils import trans


class Model:
    def __init__(self, window=None):
        """
        Model and preset select controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup"""
        pass

    def select(self, id, value):
        """
        Select mode, model or preset

        :param id: id of the list
        :param value: value of the list (row index)
        """
        if id == 'prompt.mode':
            # check if mode change is not locked
            if self.mode_change_locked():
                return
            mode = self.window.app.modes.get_by_idx(value)
            self.set_mode(mode)
            return
        elif id == 'prompt.model':
            # check if model change is not locked
            if self.model_change_locked():
                return
            mode = self.window.app.config.get('mode')
            self.set_model_by_idx(mode, value)
        elif id == 'preset.presets':
            # check if preset change is not locked
            if self.preset_change_locked():
                return
            mode = self.window.app.config.get('mode')
            self.set_preset_by_idx(mode, value)

        # update all layout
        self.window.controller.ui.update()

    def set_mode(self, mode):
        """
        Set mode

        :param mode: mode name
        """
        # if ctx loaded with assistant then switch to this assistant
        if mode == "assistant":
            if self.window.app.ctx.current is not None \
                    and self.window.app.ctx.assistant is not None:
                self.window.controller.assistant.select_by_id(self.window.app.ctx.assistant)

        self.window.app.config.set('mode', mode)
        self.window.app.config.set('model', "")
        self.window.app.config.set('preset', "")
        self.window.controller.attachment.update()
        self.window.controller.ctx.update_ctx()

        # update all layout
        self.window.controller.ui.update()

        self.window.set_status(trans('status.started'))

        # vision camera
        if mode == 'vision':
            self.window.controller.camera.setup()
            self.window.controller.camera.show_camera()
        else:
            self.window.controller.camera.hide_camera()

        # assistant
        if mode == "assistant":
            # update ctx label
            self.window.controller.ctx.update_ctx_label_by_current()

    def set_model_by_idx(self, mode, idx):
        """
        Set model by index

        :param mode: mode name
        :param idx: model index
        """
        model = self.window.app.models.get_by_idx(idx, mode)
        self.window.app.config.set('model', model)
        self.window.app.config.data['current_model'][mode] = model

    def set_model(self, mode, model):
        """
        Set model

        :param mode: mode name
        :param model: model name
        """
        self.window.app.config.set('model', model)
        self.window.app.config.data['current_model'][mode] = model

    def set_preset_by_idx(self, mode, idx):
        """
        Set preset by index

        :param mode: mode name
        :param idx: preset index
        """
        preset = self.window.app.presets.get_by_idx(idx, mode)
        self.window.app.config.data['preset'] = preset
        self.window.app.config.data['current_preset'][mode] = preset

    def set_preset(self, mode, preset):
        """
        Set preset

        :param mode: mode name
        :param preset: preset name
        """
        if not self.window.app.presets.has(mode, preset):
            return False
        self.window.app.config.data['preset'] = preset
        self.window.app.config.data['current_preset'][mode] = preset

    def select_mode_by_current(self):
        """Select mode by current"""
        mode = self.window.app.config.get('mode')
        items = self.window.app.modes.get_all()
        idx = list(items.keys()).index(mode)
        current = self.window.ui.models['prompt.mode'].index(idx, 0)
        self.window.ui.nodes['prompt.mode'].setCurrentIndex(current)

    def select_model_by_current(self):
        """Select model by current"""
        mode = self.window.app.config.get('mode')
        model = self.window.app.config.get('model')
        items = self.window.app.models.get_by_mode(mode)
        if model in items:
            idx = list(items.keys()).index(model)
            current = self.window.ui.models['prompt.model'].index(idx, 0)
            self.window.ui.nodes['prompt.model'].setCurrentIndex(current)

    def select_preset_by_current(self):
        """Select preset by current"""
        mode = self.window.app.config.get('mode')
        preset = self.window.app.config.get('preset')
        items = self.window.app.presets.get_by_mode(mode)
        if preset in items:
            idx = list(items.keys()).index(preset)
            current = self.window.ui.models['preset.presets'].index(idx, 0)
            self.window.ui.nodes['preset.presets'].setCurrentIndex(current)

    def select_default(self):
        """Set default mode, model and preset"""
        self.select_default_mode()
        self.select_default_model()
        self.select_default_preset()
        self.window.controller.assistant.select_default_assistant()

    def select_default_mode(self):
        """Set default mode"""
        mode = self.window.app.config.get('mode')
        if mode is None or mode == "":
            self.window.app.config.set('mode', self.window.app.modes.get_default())

    def select_default_model(self):
        """Set default model"""
        model = self.window.app.config.get('model')
        if model is None or model == "":
            mode = self.window.app.config.get('mode')

            # set previous selected model
            current_models = self.window.app.config.get('current_model')
            if mode in current_models and \
                    current_models[mode] is not None and \
                    current_models[mode] != "" and \
                    current_models[mode] in self.window.app.models.get_by_mode(mode):
                self.window.app.config.set('model', current_models[mode])
            else:
                # or set default model
                self.window.app.config.set('model', self.window.app.models.get_default(mode))

    def select_default_preset(self):
        """Set default preset"""
        preset = self.window.app.config.get('preset')
        if preset is None or preset == "":
            mode = self.window.app.config.get('mode')

            # set previous selected preset
            current_presets = self.window.app.config.get('current_preset')
            if mode in current_presets and \
                    current_presets[mode] is not None and \
                    current_presets[mode] != "" and \
                    current_presets[mode] in self.window.app.presets.get_by_mode(mode):
                self.window.app.config.set('preset', current_presets[mode])
            else:
                # or set default preset
                self.window.app.config.set('preset', self.window.app.presets.get_default(mode))

    def update_preset_data(self):
        """Update preset data"""
        id = self.window.app.config.get('preset')
        if id is None or id == "":
            self.reset_preset_data()  # clear preset fields
            self.reset_current_data()
            return

        if id not in self.window.app.presets.items:
            self.window.app.config.set('preset', "")  # clear preset if not found
            self.reset_preset_data()  # clear preset fields
            self.reset_current_data()
            return

        # update preset fields
        data = self.window.app.presets.items[id]
        self.window.ui.nodes['preset.prompt'].setPlainText(data.prompt)
        self.window.ui.nodes['preset.ai_name'].setText(data.ai_name)
        self.window.ui.nodes['preset.user_name'].setText(data.user_name)

        # update current data
        self.window.app.config.set('prompt', data.prompt)
        self.window.app.config.set('ai_name', data.ai_name)
        self.window.app.config.set('user_name', data.user_name)

    def update_list_modes(self):
        """Update modes list"""
        items = self.window.app.modes.get_all()
        self.window.ui.toolbox.mode.update(items)

    def update_list_models(self):
        """Update models list"""
        mode = self.window.app.config.get('mode')
        items = self.window.app.models.get_by_mode(mode)
        self.window.ui.toolbox.model.update(items)

    def update_list_presets(self):
        """Update presets list"""
        mode = self.window.app.config.get('mode')
        items = self.window.app.presets.get_by_mode(mode)
        self.window.ui.toolbox.presets.update(items)

    def update_current_temperature(self, temperature=None):
        """
        Update current temperature

        :param temperature: temperature (float)
        """
        if temperature is None:
            if self.window.app.config.get('preset') is None or self.window.app.config.get('preset') == "":
                temperature = 1.0  # default temperature
            else:
                id = self.window.app.config.get('preset')
                if id in self.window.app.presets.items:
                    temperature = float(self.window.app.presets.items[id].temperature)
        self.window.controller.settings.apply("current_temperature", temperature)

    def update_current_preset(self):
        """Update current mode, model and preset"""
        mode = self.window.app.config.get('mode')
        id = self.window.app.config.get('preset')
        if id is not None and id != "":
            if id in self.window.app.presets.items:
                preset = self.window.app.presets.items[id]
                self.window.app.config.set('user_name', preset.user_name)
                self.window.app.config.set('ai_name', preset.ai_name)
                self.window.app.config.set('prompt', preset.prompt)
                self.window.app.config.set('temperature', preset.temperature)
                return

        self.window.app.config.set('user_name', None)
        self.window.app.config.set('ai_name', None)
        self.window.app.config.set('temperature', 1.0)

        # set default prompt if mode is chat
        if mode == 'chat':
            self.window.app.config.set('prompt', self.window.app.config.get('default_prompt'))
        else:
            self.window.app.config.set('prompt', None)

    def update_mode(self):
        """Update mode"""
        self.select_default_mode()
        self.update_list_modes()
        self.select_mode_by_current()

    def update_models(self):
        """Update models"""
        self.select_default_model()
        self.update_list_models()
        self.select_model_by_current()

    def update_presets(self):
        """Update presets"""
        self.select_default_preset()
        self.update_current_preset()
        self.update_preset_data()
        self.update_current_temperature()
        self.update_list_presets()
        self.select_preset_by_current()

    def reset_preset_data(self):
        """Reset preset data"""
        self.window.ui.nodes['preset.prompt'].setPlainText("")
        self.window.ui.nodes['preset.ai_name'].setText("")
        self.window.ui.nodes['preset.user_name'].setText("")

    def reset_current_data(self):
        """Reset current data"""
        self.window.app.config.set('prompt', None)
        self.window.app.config.set('ai_name', None)
        self.window.app.config.set('user_name', None)

    def mode_change_locked(self):
        """
        Check if mode change is locked

        :return: true if locked
        :rtype: bool
        """
        if self.window.controller.input.generating:
            return True
        return False

    def model_change_locked(self):
        """
        Check if model change is locked

        :return: true if locked
        :rtype: bool
        """
        if self.window.controller.input.generating:
            return True
        return False

    def preset_change_locked(self):
        """
        Check if preset change is locked

        :return: true if locked
        :rtype: bool
        """
        # if self.window.controller.input.generating:
        # return True
        return False
