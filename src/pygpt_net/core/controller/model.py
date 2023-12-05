#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 12:00:00                  #
# ================================================== #

from ..utils import trans


class Model:
    def __init__(self, window=None):
        """
        Model and preset select controller

        :param window: main window object
        """
        self.window = window

    def setup(self):
        """Setups all select lists"""
        self.update()

    def select(self, id, value):
        """
        Selects mode, model or preset

        :param id: ID of the list
        :param value: value of the list (row index)
        """
        if id == 'prompt.mode':
            mode = self.window.config.get_mode_by_idx(value)
            self.window.config.data['mode'] = mode
            self.window.config.data['model'] = ""
            self.window.config.data['preset'] = ""
            self.window.controller.attachment.update()  # reload attachments
        elif id == 'prompt.model':
            mode = self.window.config.data['mode']
            model = self.window.config.get_model_by_idx(value, mode)
            self.window.config.data['model'] = model
            self.window.config.data['current_model'][mode] = model
        elif id == 'preset.presets':
            mode = self.window.config.data['mode']
            preset = self.window.config.get_preset_by_idx(value, mode)
            self.window.config.data['preset'] = preset
            self.window.config.data['current_preset'][mode] = preset

        self.update()

    def reset_preset_data(self):
        """Resets preset data"""
        self.window.data['preset.prompt'].setPlainText("")
        self.window.data['preset.ai_name'].setText("")
        self.window.data['preset.user_name'].setText("")

    def reset_current_data(self):
        """Resets current data"""
        self.window.config.data['prompt'] = None
        self.window.config.data['ai_name'] = None
        self.window.config.data['user_name'] = None

    def update_preset_data(self):
        """Updates preset data"""
        preset = self.window.config.data['preset']
        if preset is None or preset == "":
            self.reset_preset_data()  # clear preset fields
            self.reset_current_data()
            return

        if preset not in self.window.config.presets:
            self.window.config.data['preset'] = ""  # clear preset if not found
            self.reset_preset_data()  # clear preset fields
            self.reset_current_data()
            return

        # update preset fields
        preset_data = self.window.config.presets[preset]
        self.window.data['preset.prompt'].setPlainText(preset_data['prompt'])
        self.window.data['preset.ai_name'].setText(preset_data['ai_name'])
        self.window.data['preset.user_name'].setText(preset_data['user_name'])

        # update current data
        self.window.config.data['prompt'] = preset_data['prompt']
        self.window.config.data['ai_name'] = preset_data['ai_name']
        self.window.config.data['user_name'] = preset_data['user_name']

    def select_mode_by_current(self):
        """Selects mode by current"""
        mode = self.window.config.data['mode']
        items = self.window.config.get_modes()
        idx = list(items.keys()).index(mode)
        current = self.window.models['prompt.mode'].index(idx, 0)
        self.window.data['prompt.mode'].setCurrentIndex(current)

    def select_model_by_current(self):
        """Selects model by current"""
        mode = self.window.config.data['mode']
        model = self.window.config.data['model']
        items = self.window.config.get_models(mode)
        if model in items:
            idx = list(items.keys()).index(model)
            current = self.window.models['prompt.model'].index(idx, 0)
            self.window.data['prompt.model'].setCurrentIndex(current)

    def select_preset_by_current(self):
        """Selects preset by current"""
        mode = self.window.config.data['mode']
        preset = self.window.config.data['preset']
        items = self.window.config.get_presets(mode)
        if preset in items:
            idx = list(items.keys()).index(preset)
            current = self.window.models['preset.presets'].index(idx, 0)
            self.window.data['preset.presets'].setCurrentIndex(current)

    def update_list_modes(self):
        """Updates modes list"""
        # update modes
        items = self.window.config.get_modes()
        self.window.ui.toolbox.update_list('prompt.mode', items)

    def update_list_models(self):
        """Updates models list"""
        # update modes
        mode = self.window.config.data['mode']
        items = self.window.config.get_models(mode)
        self.window.ui.toolbox.update_list('prompt.model', items)

    def update_list_presets(self):
        """Updates presets list"""
        # update model
        mode = self.window.config.data['mode']
        items = self.window.config.get_presets(mode)
        self.window.ui.toolbox.update_list('preset.presets', items)

    def update_chat_label(self):
        """Updates chat label"""
        mode = self.window.config.data['mode']
        model = self.window.config.data['model']
        if model is None or model == "":
            model_str = "{}".format(trans("mode." + mode))
        else:
            model_str = "{} ({})".format(trans("mode." + mode), model)
        self.window.data['chat.model'].setText(model_str)

    def select_default(self):
        """Sets default mode, model and preset"""
        if self.window.config.data['mode'] is None or self.window.config.data['mode'] == "":
            self.window.config.data['mode'] = self.window.config.get_default_mode()

        if self.window.config.data['model'] is None or self.window.config.data['model'] == "":
            mode = self.window.config.data['mode']

            # set previous selected model
            if mode in self.window.config.data['current_model'] and \
                    self.window.config.data['current_model'][mode] is not None and \
                    self.window.config.data['current_model'][mode] != "" and \
                    self.window.config.data['current_model'][mode] in self.window.config.get_models(mode):
                self.window.config.data['model'] = self.window.config.data['current_model'][mode]
            else:
                # or set default model
                self.window.config.data['model'] = self.window.config.get_default_model(self.window.config.data['mode'])

        if self.window.config.data['preset'] is None or self.window.config.data['preset'] == "":
            mode = self.window.config.data['mode']

            # set previous selected preset
            if mode in self.window.config.data['current_preset'] and \
                    self.window.config.data['current_preset'][mode] is not None and \
                    self.window.config.data['current_preset'][mode] != "" and \
                    self.window.config.data['current_preset'][mode] in self.window.config.get_presets(mode):
                self.window.config.data['preset'] = self.window.config.data['current_preset'][mode]
            else:
                # or set default preset
                self.window.config.data['preset'] = self.window.config.get_default_preset(
                    self.window.config.data['mode'])

    def update_current_temperature(self, temperature=None):
        """
        Updates current temperature

        :param temperature: temperature (float)
        """
        if temperature is None:
            if self.window.config.data['preset'] is None or self.window.config.data['preset'] == "":
                temperature = 1.0  # default temperature
            else:
                preset = self.window.config.data['preset']
                if preset in self.window.config.presets and 'temperature' in self.window.config.presets[preset]:
                    temperature = float(self.window.config.presets[preset]['temperature'])
        self.window.controller.settings.apply("current_temperature", temperature)

    def update_current(self):
        """Updates current mode, model and preset"""
        mode = self.window.config.data['mode']
        if self.window.config.data['preset'] is not None and self.window.config.data['preset'] != "":
            if self.window.config.data['preset'] in self.window.config.presets:
                preset = self.window.config.presets[self.window.config.data['preset']]
                self.window.config.data['user_name'] = preset['user_name']
                self.window.config.data['ai_name'] = preset['ai_name']
                self.window.config.data['prompt'] = preset['prompt']
                self.window.config.data['temperature'] = preset['temperature']
                return

        self.window.config.data['user_name'] = None
        self.window.config.data['ai_name'] = None
        self.window.config.data['temperature'] = 1.0

        # set default prompt if mode is chat
        if mode == 'chat':
            self.window.config.data['prompt'] = self.window.config.data['default_prompt']
        else:
            self.window.config.data['prompt'] = None

    def update_active(self):
        """Updates active mode, model and preset"""
        mode = self.window.config.data['mode']
        if mode == 'chat':
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)

            self.window.data['preset.ai_name'].setDisabled(True)
            self.window.data['preset.user_name'].setDisabled(True)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['presets.widget'].setVisible(True)
            self.window.data['assistants.widget'].setVisible(False)

            self.window.data['img_variants.label'].setVisible(False)
            self.window.config_option['img_variants'].setVisible(False)

            self.window.data['temperature.label'].setVisible(True)
            self.window.config_option['current_temperature'].setVisible(True)
        elif mode == 'img':
            self.window.config_option['current_temperature'].slider.setDisabled(True)
            self.window.config_option['current_temperature'].input.setDisabled(True)

            self.window.data['preset.prompt'].setDisabled(False)
            self.window.data['preset.ai_name'].setDisabled(True)
            self.window.data['preset.user_name'].setDisabled(True)
            self.window.data['preset.clear'].setVisible(False)
            self.window.data['preset.use'].setVisible(True)

            self.window.data['presets.widget'].setVisible(True)
            self.window.data['assistants.widget'].setVisible(False)

            self.window.data['img_variants.label'].setVisible(True)
            self.window.config_option['img_variants'].setVisible(True)

            self.window.data['temperature.label'].setVisible(False)
            self.window.config_option['current_temperature'].setVisible(False)
        elif mode == 'completion':
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)

            self.window.data['preset.prompt'].setDisabled(False)
            self.window.data['preset.ai_name'].setDisabled(False)
            self.window.data['preset.user_name'].setDisabled(False)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['presets.widget'].setVisible(True)
            self.window.data['assistants.widget'].setVisible(False)

            self.window.data['img_variants.label'].setVisible(False)
            self.window.config_option['img_variants'].setVisible(False)

            self.window.data['temperature.label'].setVisible(True)
            self.window.config_option['current_temperature'].setVisible(True)
        elif mode == 'vision':
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)

            self.window.data['preset.ai_name'].setDisabled(True)
            self.window.data['preset.user_name'].setDisabled(True)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['presets.widget'].setVisible(True)
            self.window.data['assistants.widget'].setVisible(False)

            self.window.data['img_variants.label'].setVisible(False)
            self.window.config_option['img_variants'].setVisible(False)

            self.window.data['temperature.label'].setVisible(True)
            self.window.config_option['current_temperature'].setVisible(True)
        elif mode == 'langchain':
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)

            self.window.data['preset.ai_name'].setDisabled(False)
            self.window.data['preset.user_name'].setDisabled(False)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['presets.widget'].setVisible(True)
            self.window.data['assistants.widget'].setVisible(False)

            self.window.data['img_variants.label'].setVisible(False)
            self.window.config_option['img_variants'].setVisible(False)

            self.window.data['temperature.label'].setVisible(True)
            self.window.config_option['current_temperature'].setVisible(True)
        elif mode == 'assistant':
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)

            self.window.data['preset.ai_name'].setDisabled(False)
            self.window.data['preset.user_name'].setDisabled(False)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['presets.widget'].setVisible(False)
            self.window.data['assistants.widget'].setVisible(True)

            self.window.data['img_variants.label'].setVisible(False)
            self.window.config_option['img_variants'].setVisible(False)

            self.window.data['temperature.label'].setVisible(True)
            self.window.config_option['current_temperature'].setVisible(True)

    def update(self):
        """Updates all lists"""
        self.select_default()  # set default mode, model and preset if not set
        self.update_current()  # update current mode, model and preset

        # update preset data and current temperature
        self.update_preset_data()
        self.update_current_temperature()

        # update lists
        self.update_list_modes()
        self.update_list_models()
        self.update_list_presets()

        # select current mode, model and preset
        self.select_mode_by_current()
        self.select_model_by_current()
        self.select_preset_by_current()

        # update chat label
        self.update_chat_label()

        # disable / enable widgets
        self.update_active()

        # update tokens counters, etc.
        self.window.controller.ui.update()
