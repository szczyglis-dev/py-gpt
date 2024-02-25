#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.25 01:00:00                  #
# ================================================== #

import os
import requests

from .base import BaseProvider


class ElevenLabsTextToSpeech(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        Eleven Labs Text to Speech provider

        :param args: args
        :param kwargs: kwargs
        """
        super(ElevenLabsTextToSpeech, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "eleven_labs"
        self.name = "Eleven Labs"

    def init_options(self):
        """Initialize options"""
        url_api = {
            "API Key": "https://elevenlabs.io/speech-synthesis",
        }
        self.plugin.add_option(
            "eleven_labs_api_key",
            type="text",
            value="",
            label="Eleven Labs API Key",
            tab="eleven_labs",
            description="You can obtain your own API key at: "
                        "https://elevenlabs.io/speech-synthesis",
            tooltip="Eleven Labs API Key",
            secret=True,
            persist=True,
            urls=url_api,
        )
        self.plugin.add_option(
            "eleven_labs_voice",
            type="text",
            value="kigFud3tYib8QFaSSi9D",
            label="Voice ID",
            tab="eleven_labs",
            description="Specify Voice ID",
            tooltip="Voice ID",
            urls={
                "Voices": "https://elevenlabs.io/voice-library"
            },
        )
        self.plugin.add_option(
            "eleven_labs_model",
            type="text",
            value="eleven_multilingual_v2",
            label="Model",
            tab="eleven_labs",
            description="Specify model",
            tooltip="Model name",
            urls={
                "Models": "https://elevenlabs.io/docs/speech-synthesis/models"
            },
        )

    def speech(self, text: str) -> str:
        """
        Speech text to audio

        :param text: text to speech
        :return: path to generated audio file or None if audio playback is handled here
        """
        api_key = self.plugin.get_option_value("eleven_labs_api_key")
        model = self.plugin.get_option_value("eleven_labs_model")
        voice = self.plugin.get_option_value("eleven_labs_voice")
        output_file = self.plugin.output_file
        path = os.path.join(
            self.plugin.window.core.config.path,
            output_file,
        )
        CHUNK_SIZE = 1024
        url = "https://api.elevenlabs.io/v1/text-to-speech/" + voice

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        }
        data = {
            "text": text,
            "model_id": model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5,
            }
        }
        response = requests.post(url, json=data, headers=headers)
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
        return path

    def is_configured(self) -> bool:
        """
        Check if provider is configured

        :return: True if configured, False otherwise
        """
        api_key = self.plugin.get_option_value("eleven_labs_api_key")
        return api_key is not None and api_key != ""

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        api_key = self.plugin.get_option_value("eleven_labs_api_key")
        if api_key is None or api_key == "":
            return "Eleven Labs API KEY is not set. Please set it in plugin settings."

