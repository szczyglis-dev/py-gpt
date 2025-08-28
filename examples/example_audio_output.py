#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.24 02:00:00                  #
# ================================================== #

import os

from pygpt_net.provider.audio_output.base import BaseProvider  # <--- provider must inherit from BaseProvider


class ExampleAudioOutput(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        Example audio output (OpenAI Text to Speech used as example)

        :param args: args
        :param kwargs: kwargs
        """
        super(ExampleAudioOutput, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "example_audio_output"
        self.name = "Example audio output"
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

    def init_options(self):
        """Initialize options"""
        self.plugin.add_option(
            "openai_model",
            type="text",
            value="tts-1",
            label="Model",
            tab="example_audio_output",
            description="Example description #1",
        )
        self.plugin.add_option(
            "openai_voice",
            type="text",
            value="alloy",
            label="Voice",
            tab="example_audio_output",
            description="Example description #2",
        )

    def speech(self, text: str) -> str:
        """
        Speech text to audio

        Method must generate audio file with audio speech from provided text and return path to generated audio file

        :param text: text to speech
        :return: path to generated audio file or None if audio playback is handled here
        """
        client = self.plugin.window.core.api.openai.get_client()
        output_file = self.plugin.output_file
        voice = self.plugin.get_option_value('openai_voice')
        model = self.plugin.get_option_value('openai_model')
        if model not in self.allowed_models:
            model = 'tts-1'
        if voice not in self.allowed_voices:
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
        return path  # <--- return path to generated audio file

    def is_configured(self) -> bool:
        """
        Check if provider is configured

        This method should check that all required config options are provided (API keys, etc.)

        :return: True if configured, False otherwise
        """
        return True

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        return "You must define an API key in the plugin settings!"
