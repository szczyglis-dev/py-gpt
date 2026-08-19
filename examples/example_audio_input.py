#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# PyGPT audio-input provider tutorial                #
# Docs: https://pygpt.readthedocs.io/en/latest/      #
# Updated: 2026-08-19                                #
# ================================================== #

from pygpt_net.provider.audio_input.base import BaseProvider


class ExampleAudioInput(BaseProvider):
    """Minimal speech-to-text provider using OpenAI transcription as an example.

    PyGPT attaches the Audio Input plugin to this provider during registration.
    Provider-specific settings are then added by `init_options()`.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "example_audio_input"  # must be unique
        self.name = "Example audio input (OpenAI transcription)"

    def init_options(self):
        """Declare settings displayed under this provider's plugin tab."""
        self.plugin.add_option(
            "example_model",
            type="text",
            value="whisper-1",
            label="Transcription model",
            tab=self.id,
            description="Model sent to the transcription API, e.g. whisper-1.",
        )

    def transcribe(self, path: str) -> str:
        """Transcribe the audio file at `path` and return plain text.

        Do not hard-code the recording filename. PyGPT currently keeps its own
        audio-input file under the workdir `tmp` directory, but a provider should
        simply consume the path it receives.
        """
        client = self.plugin.window.core.api.openai.get_client()
        with open(path, "rb") as audio_file:
            return client.audio.transcriptions.create(
                model=self.plugin.get_option_value("example_model"),
                file=audio_file,
                response_format="text",
            )

    def is_configured(self) -> bool:
        """Return False when credentials required by this provider are missing."""
        api_key = self.plugin.window.core.config.get("api_key")
        return bool(api_key)

    def get_config_message(self) -> str:
        """Message shown when `is_configured()` returns False."""
        return "OpenAI API key is not configured. Set it in Config -> Settings -> API Keys."
