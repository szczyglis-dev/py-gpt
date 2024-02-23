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

from .base import BaseProvider


class OpenAIWhisper(BaseProvider):
    def __init__(self, *args, **kwargs):
        """
        OpenAI Whisper provider

        :param args: args
        :param kwargs: kwargs
        """
        super(OpenAIWhisper, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "openai_whisper"
        self.name = "OpenAI Whisper"

    def init_options(self):
        """Initialize options"""
        self.plugin.add_option(
            "whisper_model",
            type="text",
            value="whisper-1",
            label="Model",
            tab="openai_whisper",
            description="Specify model, default: whisper-1",
        )

    def transcribe(self, path: str) -> str:
        """
        Audio to text transcription

        :param path: path to audio file to transcribe
        :return: transcribed text
        """
        client = self.plugin.window.core.gpt.get_client()
        with open(path, "rb") as audio_file:
            return client.audio.transcriptions.create(
                model=self.plugin.get_option_value('whisper_model'),
                file=audio_file,
                response_format="text",
            )

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
