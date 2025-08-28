#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.23 19:00:00                  #
# ================================================== #

from pygpt_net.provider.audio_input.base import BaseProvider  # <--- provider must inherit from BaseProvider


class ExampleAudioInput(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        Example audio input (OpenAI Whisper provider is used here as an example)

        :param args: args
        :param kwargs: kwargs
        """
        super(ExampleAudioInput, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "example_audio_input"
        self.name = "Example input provider (Whisper)"

    def init_options(self):
        """Initialize options for plugin tab"""
        self.plugin.add_option(
            "whisper_model",
            type="text",
            value="whisper-1",
            label="Example model",
            tab="example_audio_input",  # tab ID == provider iID
            description="Example description",
        )

    def transcribe(self, path: str) -> str:
        """
        Audio to text transcription

        This method must return transcription of the audio file generated in `path`

        :param path: path to audio file to transcribe
        :return: transcribed text
        """
        client = self.plugin.window.core.api.openai.get_client()
        with open(path, "rb") as audio_file:
            return client.audio.transcriptions.create(
                model=self.plugin.get_option_value('whisper_model'),
                file=audio_file,
                response_format="text",
            )

    def is_configured(self) -> bool:
        """
        Check if provider is configured

        This method should check that all required config options are provided (API keys, etc.)

        :return: True if configured, False otherwise
        """
        return True

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured (no API keys, etc.)

        :return: message
        """
        return "You must define an API key in the plugin settings!"
