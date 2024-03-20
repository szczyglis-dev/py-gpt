#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.20 06:00:00                  #
# ================================================== #

from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Audio:
    def __init__(self, window=None):
        """
        Audio/voice controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup controller"""
        self.update()

    def toggle_input(self, state: bool, btn: bool = True):
        """
        Toggle audio input

        :param state: True to enable, False to disable
        :param btn: True if called from button
        """
        self.window.core.dispatcher.dispatch(
            Event(Event.AUDIO_INPUT_TOGGLE, {
                "value": state,
            })
        )

    def toggle_output(self):
        """Toggle audio output"""
        if self.window.controller.plugins.is_enabled('audio_output'):
            self.disable_output()
        else:
            self.enable_output()

    def enable_output(self):
        """Enable audio output"""
        self.toggle_output_icon(True)
        self.window.controller.plugins.enable('audio_output')
        self.window.core.config.save()
        self.update()

    def disable_output(self):
        """Disable audio output"""
        self.toggle_output_icon(False)
        self.window.controller.plugins.disable('audio_output')
        self.window.core.config.save()
        self.update()

    def disable_input(self, update: bool = True):
        """
        Disable audio input

        :param update: True to update menu and listeners
        """
        self.window.controller.plugins.disable('audio_input')
        self.window.core.config.save()
        if update:
            self.update()

    def stop_input(self):
        """Stop audio input"""
        self.window.core.dispatcher.dispatch(
            Event(Event.AUDIO_INPUT_STOP, {
                "value": True,
            }), all=True)

    def stop_output(self):
        """Stop audio output"""
        self.window.core.dispatcher.dispatch(
            Event(Event.AUDIO_OUTPUT_STOP, {
                "value": True,
            }), all=True)

    def update(self):
        """Update UI and listeners"""
        self.update_listeners()
        self.update_menu()

    def is_output_enabled(self) -> bool:
        """
        Check if any audio output is enabled

        :return: True if enabled
        """
        if self.window.controller.plugins.is_enabled('audio_output'):
            return True
        return False

    def update_listeners(self):
        """Update audio listeners"""
        is_output = False
        if self.window.controller.plugins.is_enabled('audio_output'):
            is_output = True
        if not is_output:
            self.stop_output()

        if not self.window.controller.plugins.is_enabled('audio_input'):
            self.toggle_input(False)
            self.stop_input()
            if self.window.ui.plugin_addon['audio.input'].btn_toggle.isChecked():
                self.window.ui.plugin_addon['audio.input'].btn_toggle.setChecked(False)

    def update_menu(self):
        """Update audio menu"""
        if self.window.controller.plugins.is_enabled('audio_output'):
            self.window.ui.menu['audio.output'].setChecked(True)
        else:
            self.window.ui.menu['audio.output'].setChecked(False)

        if self.window.controller.plugins.is_enabled('audio_input'):
            self.window.ui.menu['audio.input'].setChecked(True)
        else:
            self.window.ui.menu['audio.input'].setChecked(False)

    def read_text(self, text: str):
        """
        Read text using audio output plugins

        :param text: text to read
        """
        ctx = CtxItem()
        ctx.output = text
        all = True  # to all plugins (even if disabled)
        event = Event(Event.AUDIO_READ_TEXT)
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event, all=all)

    def toggle_output_icon(self, state: bool):
        """
        Toggle input icon

        :param state: True to enable, False to disable
        """
        if state:
            self.window.ui.nodes['icon.audio.output'].set_icon(":/icons/volume.svg")
        else:
            self.window.ui.nodes['icon.audio.output'].set_icon(":/icons/mute.svg")

    def toggle_input_icon(self, state: bool):
        """
        Toggle input icon

        :param state: True to enable, False to disable
        """
        if state:
            self.window.ui.nodes['icon.audio.input'].set_icon(":/icons/mic.svg")
        else:
            self.window.ui.nodes['icon.audio.input'].set_icon(":/icons/mic_off.svg")

    def on_begin(self, text: str):
        """
        On audio playback init

        :param text: text to play
        """
        self.window.ui.status(trans("status.audio.start"))

    def on_play(self, event: str):
        """
        On audio playback start

        :param event: event name
        """
        if event == Event.AUDIO_READ_TEXT:
            self.window.ui.status("")

    def on_stop(self):
        """
        On audio playback stopped (force)
        """
        self.window.ui.status(trans("status.audio.stopped"))

    def is_playing(self) -> bool:
        """
        Check if any audio is playing

        :return: True if playing
        """
        from pygame import mixer
        try:
            mixer.init()
            return mixer.get_busy()
        except Exception as e:
            pass
        return False
