#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.29 18:00:00                  #
# ================================================== #

from .base import BaseProvider


class GoogleGenAIAudioInput(BaseProvider):

    PROMPT_TRANSCRIBE = (
        "You are a speech-to-text transcriber. "
        "Return only the verbatim transcript as plain text. "
        "Do not add any explanations, timestamps, labels or formatting."
    )

    def __init__(self, *args, **kwargs):
        """
        Google GenAI (Gemini) audio provider for transcription (via API).

        :param args: args
        :param kwargs: kwargs
        """
        super(GoogleGenAIAudioInput, self).__init__(*args, **kwargs)
        self.plugin = kwargs.get("plugin")
        self.id = "google_genai"
        self.name = "Google GenAI"

    def init_options(self):
        """Initialize options"""
        # Keep option shape consistent with Whisper provider
        self.plugin.add_option(
            "google_genai_audio_model",
            type="text",
            value="gemini-2.5-flash",
            label="Model",
            tab="google_genai",
            description="Specify Gemini model supporting audio, e.g., gemini-2.5-flash",
        )
        self.plugin.add_option(
            "google_genai_audio_prompt",
            type="textarea",
            value=self.PROMPT_TRANSCRIBE,
            label="System Prompt",
            tab="google_genai",
            description="System prompt to guide the transcription output",
            tooltip="System prompt for transcription",
            persist=True,
        )

    def transcribe(self, path: str) -> str:
        """
        Audio to text transcription using Google GenAI (Gemini).

        :param path: path to audio file to transcribe
        :return: transcribed text
        """
        # Get pre-configured GenAI client from the app core
        client = self.plugin.window.core.api.google.get_client()

        # Upload the audio file via the Files API
        uploaded_file = client.files.upload(file=path)

        # Ask the model to produce a plain text transcript only
        # Using system_instruction keeps the public API surface simple (no extra options needed)
        config = {
            "system_instruction": self.plugin.get_option_value("google_genai_audio_prompt") or self.PROMPT_TRANSCRIBE,
            "temperature": 0.0,
        }

        # Generate content (transcription) with the selected model
        model_name = self.plugin.get_option_value("google_genai_audio_model")
        response = client.models.generate_content(
            model=model_name,
            contents=[uploaded_file],
            config=config,
        )

        # The SDK exposes the unified .text property for convenience
        return response.text or ""

    def is_configured(self) -> bool:
        """
        Check if provider is configured

        :return: True if configured, False otherwise
        """
        api_key = self.plugin.window.core.config.get("api_key_google")
        return api_key is not None and api_key != ""

    def get_config_message(self) -> str:
        """
        Return message to display when provider is not configured

        :return: message
        """
        return "Google GenAI API key is not set yet. Please configure it in settings."