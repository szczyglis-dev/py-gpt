#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #

from ..utils import trans


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
            mode = self.window.config.get_mode_by_idx(value)
            self.set_mode(mode)
            return
        elif id == 'prompt.model':
            # check if model change is not locked
            if self.model_change_locked():
                return
            mode = self.window.config.get('mode')
            self.set_model_by_idx(mode, value)
        elif id == 'preset.presets':
            # check if preset change is not locked
            if self.preset_change_locked():
                return
            mode = self.window.config.get('mode')
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
            if self.window.app.context.current_ctx is not None \
                    and self.window.app.context.current_assistant is not None:
                self.window.controller.assistant.select_by_id(self.window.app.context.current_assistant)

        self.window.config.set('mode', mode)
        self.window.config.set('model', "")
        self.window.config.set('preset', "")
        self.window.controller.attachment.update()
        self.window.controller.context.update_ctx()

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
            self.window.controller.context.update_ctx_label_by_current()

    def set_model_by_idx(self, mode, idx):
        """
        Set model by index

        :param mode: mode name
        :param idx: model index
        """
        model = self.window.config.get_model_by_idx(idx, mode)
        self.window.config.set('model', model)
        self.window.config.data['current_model'][mode] = model

    def set_model(self, mode, model):
        """
        Set model

        :param mode: mode name
        :param model: model name
        """
        self.window.config.set('model', model)
        self.window.config.data['current_model'][mode] = model

    def set_preset_by_idx(self, mode, idx):
        """
        Set preset by index

        :param mode: mode name
        :param idx: preset index
        """
        preset = self.window.config.get_preset_by_idx(idx, mode)
        self.window.config.data['preset'] = preset
        self.window.config.data['current_preset'][mode] = preset

    def set_preset(self, mode, preset):
        """
        Set preset

        :param mode: mode name
        :param preset: preset name
        """
        if not self.window.config.has_preset(mode, preset):
            return False
        self.window.config.data['preset'] = preset
        self.window.config.data['current_preset'][mode] = preset

    def select_mode_by_current(self):
        """Select mode by current"""
        mode = self.window.config.get('mode')
        items = self.window.config.get_modes()
        idx = list(items.keys()).index(mode)
        current = self.window.ui.models['prompt.mode'].index(idx, 0)
        self.window.ui.nodes['prompt.mode'].setCurrentIndex(current)

    def select_model_by_current(self):
        """Select model by current"""
        mode = self.window.config.get('mode')
        model = self.window.config.get('model')
        items = self.window.config.get_models(mode)
        if model in items:
            idx = list(items.keys()).index(model)
            current = self.window.ui.models['prompt.model'].index(idx, 0)
            self.window.ui.nodes['prompt.model'].setCurrentIndex(current)

    def select_preset_by_current(self):
        """Select preset by current"""
        mode = self.window.config.get('mode')
        preset = self.window.config.get('preset')
        items = self.window.config.get_presets(mode)
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
        mode = self.window.config.get('mode')
        if mode is None or mode == "":
            self.window.config.set('mode', self.window.config.get_default_mode())

    def select_default_model(self):
        """Set default model"""
        model = self.window.config.get('model')
        if model is None or model == "":
            mode = self.window.config.get('mode')

            # set previous selected model
            current_models = self.window.config.get('current_model')
            if mode in current_models and \
                    current_models[mode] is not None and \
                    current_models[mode] != "" and \
                    current_models[mode] in self.window.config.get_models(mode):
                self.window.config.set('model', current_models[mode])
            else:
                # or set default model
                self.window.config.set('model', self.window.config.get_default_model(mode))

    def select_default_preset(self):
        """Set default preset"""
        preset = self.window.config.get('preset')
        if preset is None or preset == "":
            mode = self.window.config.get('mode')

            # set previous selected preset
            current_presets = self.window.config.get('current_preset')
            if mode in current_presets and \
                    current_presets[mode] is not None and \
                    current_presets[mode] != "" and \
                    current_presets[mode] in self.window.config.get_presets(mode):
                self.window.config.set('preset', current_presets[mode])
            else:
                # or set default preset
                self.window.config.set('preset', self.window.config.get_default_preset(mode))

    def update_preset_data(self):
        """Update preset data"""
        preset = self.window.config.get('preset')
        if preset is None or preset == "":
            self.reset_preset_data()  # clear preset fields
            self.reset_current_data()
            return

        if preset not in self.window.config.presets:
            self.window.config.set('preset', "")  # clear preset if not found
            self.reset_preset_data()  # clear preset fields
            self.reset_current_data()
            return

        # update preset fields
        preset_data = self.window.config.presets[preset]
        self.window.ui.nodes['preset.prompt'].setPlainText(preset_data['prompt'])
        self.window.ui.nodes['preset.ai_name'].setText(preset_data['ai_name'])
        self.window.ui.nodes['preset.user_name'].setText(preset_data['user_name'])

        # update current data
        self.window.config.set('prompt', preset_data['prompt'])
        self.window.config.set('ai_name', preset_data['ai_name'])
        self.window.config.set('user_name', preset_data['user_name'])

    def update_list_modes(self):
        """Update modes list"""
        items = self.window.config.get_modes()
        self.window.ui.toolbox.update_list('prompt.mode', items)

    def update_list_models(self):
        """Update models list"""
        mode = self.window.config.get('mode')
        items = self.window.config.get_models(mode)
        self.window.ui.toolbox.update_list('prompt.model', items)

    def update_list_presets(self):
        """Update presets list"""
        mode = self.window.config.get('mode')
        items = self.window.config.get_presets(mode)
        self.window.ui.toolbox.update_list('preset.presets', items)

    def update_current_temperature(self, temperature=None):
        """
        Update current temperature

        :param temperature: temperature (float)
        """
        if temperature is None:
            if self.window.config.get('preset') is None or self.window.config.get('preset') == "":
                temperature = 1.0  # default temperature
            else:
                preset = self.window.config.get('preset')
                if preset in self.window.config.presets and 'temperature' in self.window.config.presets[preset]:
                    temperature = float(self.window.config.presets[preset]['temperature'])
        self.window.controller.settings.apply("current_temperature", temperature)

    def update_current_preset(self):
        """Update current mode, model and preset"""
        mode = self.window.config.get('mode')
        preset_id = self.window.config.get('preset')
        if preset_id is not None and preset_id != "":
            if preset_id in self.window.config.presets:
                preset = self.window.config.presets[preset_id]
                self.window.config.set('user_name', preset['user_name'])
                self.window.config.set('ai_name', preset['ai_name'])
                self.window.config.set('prompt', preset['prompt'])
                self.window.config.set('temperature', preset['temperature'])
                return

        self.window.config.set('user_name', None)
        self.window.config.set('ai_name', None)
        self.window.config.set('temperature', 1.0)

        # set default prompt if mode is chat
        if mode == 'chat':
            self.window.config.set('prompt', self.window.config.get('default_prompt'))
        else:
            self.window.config.set('prompt', None)

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
        self.window.config.set('prompt', None)
        self.window.config.set('ai_name', None)
        self.window.config.set('user_name', None)

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
