#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 22:00:00                  #
# ================================================== #

class Audio:
    def __init__(self, window=None):
        """
        Audio/voice controller

        :param window: main window object
        """
        self.window = window

    def setup(self):
        """Setups controller"""
        self.update()

    def toggle_output(self):
        """Toggles audio/voice"""
        if self.window.controller.plugins.is_enabled('audio_azure'):
            self.disable_output()
        else:
            self.enable_output()

    def enable_output(self):
        """Enables audio/voice"""
        self.window.controller.plugins.enable('audio_azure')
        if self.window.controller.plugins.is_enabled('audio_azure') \
                and (self.window.controller.plugins.handler.plugins['audio_azure'].options['azure_api_key'] is None
                     or self.window.controller.plugins.handler.plugins['audio_azure'].options['azure_api_key'] == ''):
            self.window.ui.dialogs.alert("Azure API KEY is not set. Please set it in plugins settings.")
            self.window.controller.plugins.disable('audio_azure')
        self.window.config.save()
        self.update()

    def disable_output(self):
        """Disables audio/voice"""
        self.window.controller.plugins.disable('audio_azure')
        self.window.config.save()
        self.update()

    def update(self):
        """Updates UI"""
        self.update_menu()

    def update_menu(self):
        """Updates menu"""
        if self.window.controller.plugins.is_enabled('audio_azure'):
            self.window.menu['audio.output.azure'].setChecked(True)
        else:
            self.window.menu['audio.output.azure'].setChecked(False)

        if self.window.controller.plugins.is_enabled('audio_openai_tts'):
            self.window.menu['audio.output.tts'].setChecked(True)
        else:
            self.window.menu['audio.output.tts'].setChecked(False)

        if self.window.controller.plugins.is_enabled('audio_openai_whisper'):
            self.window.menu['audio.input.whisper'].setChecked(True)
        else:
            self.window.menu['audio.input.whisper'].setChecked(False)
