#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 03:00:00                  #
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
            model = self.window.config.get_model_by_idx(value, mode)
            self.window.config.set('model', model)
            self.window.config.data['current_model'][mode] = model
        elif id == 'preset.presets':
            # check if preset change is not locked
            if self.preset_change_locked():
                return

            mode = self.window.config.get('mode')
            preset = self.window.config.get_preset_by_idx(value, mode)
            self.window.config.data['preset'] = preset
            self.window.config.data['current_preset'][mode] = preset

        self.update()

    def mode_change_locked(self):
        """
        Checks if mode change is locked

        :return: bool
        """
        if self.window.controller.input.generating:
            return True
        return False

    def model_change_locked(self):
        """
        Checks if model change is locked

        :return: bool
        """
        if self.window.controller.input.generating:
            return True
        return False

    def preset_change_locked(self):
        """
        Checks if preset change is locked

        :return: bool
        """
        # if self.window.controller.input.generating:
            # return True
        return False

    def set_mode(self, mode):
        """
        Sets mode

        :param mode: mode name
        """

        # if ctx loaded with assistant then switch to this assistant
        if mode == "assistant":
            if self.window.gpt.context.current_ctx is not None \
                    and self.window.gpt.context.current_assistant is not None:
                self.window.controller.assistant.select_by_id(self.window.gpt.context.current_assistant)

        self.window.config.set('mode', mode)
        self.window.config.set('model', "")
        self.window.config.set('preset', "")
        self.window.controller.attachment.update()
        self.window.controller.context.update_ctx()
        self.update()

        self.window.set_status(trans('status.started'))

        # vision camera
        if mode == 'vision':
            self.window.controller.camera.setup()
            self.window.controller.camera.show_camera()
        else:
            self.window.controller.camera.hide_camera()

    def reset_preset_data(self):
        """Resets preset data"""
        self.window.data['preset.prompt'].setPlainText("")
        self.window.data['preset.ai_name'].setText("")
        self.window.data['preset.user_name'].setText("")

    def reset_current_data(self):
        """Resets current data"""
        self.window.config.set('prompt', None)
        self.window.config.set('ai_name', None)
        self.window.config.set('user_name', None)

    def update_preset_data(self):
        """Updates preset data"""
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
        self.window.data['preset.prompt'].setPlainText(preset_data['prompt'])
        self.window.data['preset.ai_name'].setText(preset_data['ai_name'])
        self.window.data['preset.user_name'].setText(preset_data['user_name'])

        # update current data
        self.window.config.set('prompt', preset_data['prompt'])
        self.window.config.set('ai_name', preset_data['ai_name'])
        self.window.config.set('user_name', preset_data['user_name'])

    def select_mode_by_current(self):
        """Selects mode by current"""
        mode = self.window.config.get('mode')
        items = self.window.config.get_modes()
        idx = list(items.keys()).index(mode)
        current = self.window.models['prompt.mode'].index(idx, 0)
        self.window.data['prompt.mode'].setCurrentIndex(current)

    def select_model_by_current(self):
        """Selects model by current"""
        mode = self.window.config.get('mode')
        model = self.window.config.get('model')
        items = self.window.config.get_models(mode)
        if model in items:
            idx = list(items.keys()).index(model)
            current = self.window.models['prompt.model'].index(idx, 0)
            self.window.data['prompt.model'].setCurrentIndex(current)

    def select_preset_by_current(self):
        """Selects preset by current"""
        mode = self.window.config.get('mode')
        preset = self.window.config.get('preset')
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
        mode = self.window.config.get('mode')
        items = self.window.config.get_models(mode)
        self.window.ui.toolbox.update_list('prompt.model', items)

    def update_list_presets(self):
        """Updates presets list"""
        # update model
        mode = self.window.config.get('mode')
        items = self.window.config.get_presets(mode)
        self.window.ui.toolbox.update_list('preset.presets', items)

    def update_chat_label(self):
        """Updates chat label"""
        mode = self.window.config.get('mode')
        model = self.window.config.get('model')
        if model is None or model == "":
            model_str = "{}".format(trans("mode." + mode))
        else:
            model_str = "{} ({})".format(trans("mode." + mode), model)
        self.window.data['chat.model'].setText(model_str)

    def select_default(self):
        """Sets default mode, model and preset"""
        # mode
        mode = self.window.config.get('mode')
        if mode is None or mode == "":
            self.window.config.set('mode', self.window.config.get_default_mode())

        # model
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

        # preset
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

        # assistant
        assistant = self.window.config.get('assistant')
        if assistant is None or assistant == "":
            mode = self.window.config.get('mode')
            if mode == 'assistant':
                self.window.config.set('assistant', self.window.controller.assistant.assistants.get_default_assistant())
                self.window.controller.assistant.update()

    def update_current_temperature(self, temperature=None):
        """
        Updates current temperature

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

    def update_current(self):
        """Updates current mode, model and preset"""
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

    def update_active(self):
        """Updates active mode, model and preset"""
        mode = self.window.config.data['mode']
        if mode == 'chat':
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)

            # presets
            self.window.data['preset.ai_name'].setDisabled(False)
            self.window.data['preset.user_name'].setDisabled(False)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['presets.widget'].setVisible(True)
            self.window.data['assistants.widget'].setVisible(False)

            self.window.data['dalle.options'].setVisible(False)

            self.window.data['temperature.label'].setVisible(True)
            self.window.config_option['current_temperature'].setVisible(True)

            # vision capture
            self.window.data['vision.capture.options'].setVisible(False)
            self.window.data['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.tabs['input'].setTabVisible(1, False)  # files
            self.window.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.data['input.stream'].setVisible(True)
        elif mode == 'img':
            self.window.config_option['current_temperature'].slider.setDisabled(True)
            self.window.config_option['current_temperature'].input.setDisabled(True)

            # presets
            self.window.data['preset.prompt'].setDisabled(False)
            self.window.data['preset.ai_name'].setDisabled(True)
            self.window.data['preset.user_name'].setDisabled(True)
            self.window.data['preset.clear'].setVisible(False)
            self.window.data['preset.use'].setVisible(True)

            self.window.data['presets.widget'].setVisible(True)
            self.window.data['assistants.widget'].setVisible(False)

            self.window.data['dalle.options'].setVisible(True)

            self.window.data['temperature.label'].setVisible(False)
            self.window.config_option['current_temperature'].setVisible(False)

            # vision capture
            self.window.data['vision.capture.options'].setVisible(False)
            self.window.data['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.tabs['input'].setTabVisible(1, False)  # files
            self.window.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.data['input.stream'].setVisible(False)
        elif mode == 'completion':
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)

            # presets
            self.window.data['preset.prompt'].setDisabled(False)
            self.window.data['preset.ai_name'].setDisabled(False)
            self.window.data['preset.user_name'].setDisabled(False)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['presets.widget'].setVisible(True)
            self.window.data['assistants.widget'].setVisible(False)

            self.window.data['dalle.options'].setVisible(False)

            self.window.data['temperature.label'].setVisible(True)
            self.window.config_option['current_temperature'].setVisible(True)

            # vision capture
            self.window.data['vision.capture.options'].setVisible(False)
            self.window.data['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.tabs['input'].setTabVisible(1, False)  # files
            self.window.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.data['input.stream'].setVisible(True)
        elif mode == 'vision':
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)

            # presets
            self.window.data['preset.ai_name'].setDisabled(True)
            self.window.data['preset.user_name'].setDisabled(True)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['presets.widget'].setVisible(True)
            self.window.data['assistants.widget'].setVisible(False)

            self.window.data['dalle.options'].setVisible(False)

            self.window.data['temperature.label'].setVisible(False)
            self.window.config_option['current_temperature'].setVisible(False)

            # vision capture
            self.window.data['vision.capture.options'].setVisible(True)
            self.window.data['attachments.capture_clear'].setVisible(True)

            # files tabs
            self.window.tabs['input'].setTabVisible(1, True)  # files
            self.window.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.data['input.stream'].setVisible(True)
        elif mode == 'langchain':
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)

            # presets
            self.window.data['preset.ai_name'].setDisabled(False)
            self.window.data['preset.user_name'].setDisabled(False)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['presets.widget'].setVisible(True)
            self.window.data['assistants.widget'].setVisible(False)

            self.window.data['dalle.options'].setVisible(False)

            self.window.data['temperature.label'].setVisible(True)
            self.window.config_option['current_temperature'].setVisible(True)

            # vision capture
            self.window.data['vision.capture.options'].setVisible(False)
            self.window.data['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.tabs['input'].setTabVisible(1, False)  # files
            self.window.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.data['input.stream'].setVisible(True)
        elif mode == 'assistant':
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)

            # presets
            self.window.data['preset.ai_name'].setDisabled(True)
            self.window.data['preset.user_name'].setDisabled(True)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['presets.widget'].setVisible(True)
            self.window.data['assistants.widget'].setVisible(True)

            self.window.data['dalle.options'].setVisible(False)

            self.window.data['temperature.label'].setVisible(True)
            self.window.config_option['current_temperature'].setVisible(True)

            # vision capture
            self.window.data['vision.capture.options'].setVisible(False)
            self.window.data['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.tabs['input'].setTabVisible(1, True)  # files
            self.window.tabs['input'].setTabVisible(2, True)  # uploaded files

            # stream checkbox
            self.window.data['input.stream'].setVisible(False)

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
