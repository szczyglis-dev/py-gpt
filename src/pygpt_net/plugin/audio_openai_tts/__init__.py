#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.30 13:00:00                  #
# ================================================== #

import os

from PySide6.QtCore import Slot

from pygpt_net.plugin.base import BasePlugin
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from .worker import Worker


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "audio_openai_tts"
        self.name = "Audio Output (OpenAI TTS)"
        self.type = ['audio.output']
        self.description = "Enables audio/voice output (speech synthesis) using OpenAI TTS (Text-To-Speech) API"
        self.allowed_voices = [
            'alloy',
            'echo',
            'fable',
            'onyx',
            'nova',
            'shimmer',
        ]
        self.allowed_models = [
            'tts-1',
            'tts-1-hd',
        ]
        self.input_text = None
        self.playback = None
        self.order = 1
        self.use_locale = True
        self.output_file = "output.mp3"
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.add_option(
            "model",
            type="text",
            value="tts-1",
            label="Model",
            description="Specify model, available models: "
                        "tts-1, tts-1-hd",
        )
        self.add_option(
            "voice",
            type="text",
            value="alloy",
            label="Voice",
            description="Specify voice, available voices: "
                        "alloy, echo, fable, onyx, nova, shimmer",
        )

    def setup(self) -> dict:
        """
        Return available config options

        :return: config options
        """
        return self.options

    def setup_ui(self):
        """
        Setup UI
        """
        pass

    def attach(self, window):
        """
        Attach window

        :param window: Window instance
        """
        self.window = window

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: args
        :param kwargs: kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.INPUT_BEFORE:
            self.on_input_before(data['value'])

        elif name == Event.CTX_AFTER:
            self.on_ctx_after(ctx)

        elif name == Event.AUDIO_READ_TEXT:
            self.on_ctx_after(ctx)

        elif name == Event.AUDIO_OUTPUT_STOP:
            self.stop_audio()

    def on_input_before(self, text: str):
        """
        Event: Before input

        :param text: text to read
        """
        self.input_text = text

    def on_ctx_after(self, ctx: CtxItem):
        """
        Event: After ctx

        :param ctx: CtxItem
        """
        text = ctx.output
        try:
            if text is not None and len(text) > 0:
                # get config
                voice = self.get_option_value('voice')
                model = self.get_option_value('model')
                if model not in self.allowed_models:
                    model = 'tts-1'
                if voice not in self.allowed_voices:
                    voice = 'alloy'

                # worker
                worker = Worker()
                worker.plugin = self
                worker.client = self.window.core.gpt.get_client()
                worker.model = model
                worker.path = os.path.join(
                    self.window.core.config.path,
                    self.output_file,
                )
                worker.voice = voice
                worker.text = self.window.core.audio.clean_text(text)

                # signals
                worker.signals.playback.connect(self.handle_playback)
                worker.signals.stop.connect(self.handle_stop)
                worker.signals.status.connect(self.handle_status)  # base handler
                worker.signals.error.connect(self.handle_error)  # base handler

                # start
                self.window.threadpool.start(worker)

        except Exception as e:
            self.error(e)

    def destroy(self):
        """Destroy thread"""
        pass

    def set_status(self, status: str):
        """
        Set status

        :param status: status text
        """
        self.window.ui.plugin_addon['audio.output'].set_status(status)

    def show_stop_button(self):
        """Show stop button"""
        self.window.ui.plugin_addon['audio.output'].stop.setVisible(True)

    def hide_stop_button(self):
        """Hide stop button"""
        self.window.ui.plugin_addon['audio.output'].stop.setVisible(False)

    def stop_speak(self):
        """Stop speaking"""
        self.window.ui.plugin_addon['audio.output'].stop.setVisible(False)
        self.window.ui.plugin_addon['audio.output'].set_status('Stopped')
        self.window.ui.plugin_addon['audio.output'].stop_audio()

    def stop_audio(self):
        """Stop playing the audio"""
        if self.playback is not None:
            self.playback.stop()
            self.playback = None

    @Slot(object)
    def handle_playback(self, playback):
        """
        Handle thread playback object

        :param playback: playback object
        """
        self.playback = playback

    @Slot()
    def handle_stop(self):
        """Handle thread playback stop"""
        self.stop_audio()
