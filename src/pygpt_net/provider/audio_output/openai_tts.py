#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 18:00:00                  #
# ================================================== #

import os

from .base import BaseProvider


class OpenAITextToSpeech(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        OpenAI Text to Speech provider

        :param args: args
        :param kwargs: kwargs
        """
        super(OpenAITextToSpeech, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "openai_tts"
        self.name = "OpenAI TTS"
        self.allowed_models = [
            'tts-1',
            'tts-1-hd',
        ]

    def init_options(self):
        """Initialize options"""
        self.plugin.add_option(
            "openai_model",
            type="text",
            value="tts-1",
            label="Model",
            tab="openai_tts",
            description="Specify model, available models: "
                        "tts-1, tts-1-hd",
        )
        self.plugin.add_option(
            "openai_voice",
            type="combo",
            value="alloy",
            label="Voice",
            tab="openai_tts",
            use="audio_tts_whisper_voices",
            description="Specify voice, available voices: "
                        "alloy, echo, fable, onyx, nova, shimmer",
        )

    def speech(self, text: str) -> str:
        """
        Speech text to audio

        :param text: text to speech
        :return: path to generated audio file or None if audio playback is handled here
        """
        client = self.plugin.window.core.gpt.get_client()
        output_file = self.plugin.output_file
        voice = self.plugin.get_option_value('openai_voice')
        model = self.plugin.get_option_value('openai_model')
        allowed_voices = self.plugin.window.core.audio.whisper.get_voices()
        if model not in self.allowed_models:
            model = 'tts-1'
        if voice not in allowed_voices:
            voice = 'alloy'
        path = os.path.join(
            self.plugin.window.core.config.path,
            output_file,
        )
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
        )
        response.stream_to_file(path)
        return path

    def is_configured(self) -> bool:
        """
        Check if provider is configured

        :return: True if configured, False otherwise
        """
        return True

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        return ""
